import json
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text

from shared.auth.rbac import (
    AuthContext,
    EVENT_CREATORS,
    INTERNAL_READERS,
    require_actors,
    validate_event_permission,
)
from shared.db.session import get_database_health, get_session
from shared.messaging.health import get_rabbitmq_health
from shared.messaging.outbox import start_outbox_worker
from shared.messaging.consumer import start_consumer
from shared.models.event import CreateEventRequest, Event


def build_site_app(site_id: str):
    normalized_site_id = site_id.upper()
    app = FastAPI(title=f"{normalized_site_id} Service")

    def next_event_id() -> str:
        return f"{normalized_site_id.lower()}-{int(datetime.now(timezone.utc).timestamp() * 1000)}"

    @app.get("/")
    def root(auth: AuthContext = Depends(require_actors(*INTERNAL_READERS))):
        return {"status": f"{normalized_site_id} service running"}

    @app.get("/health")
    def health(auth: AuthContext = Depends(require_actors(*INTERNAL_READERS))):
        db = get_session(normalized_site_id)
        try:
            pending_outbox = db.execute(
                text("SELECT COUNT(*) FROM outbox_events WHERE status = 'PENDING'")
            ).scalar_one()
        except Exception as exc:
            pending_outbox = None
            outbox_error = str(exc)
        else:
            outbox_error = None
        finally:
            db.close()

        db_health = get_database_health(normalized_site_id)
        rabbitmq_health = get_rabbitmq_health()

        status = "ok" if db_health["ok"] and rabbitmq_health["ok"] else "degraded"
        return {
            "status": status,
            "service": normalized_site_id,
            "actor": auth.actor,
            "database": db_health,
            "rabbitmq": rabbitmq_health,
            "outbox": {
                "pending": pending_outbox,
                "error": outbox_error,
            },
        }

    @app.post("/events/")
    def create_event(
        request: CreateEventRequest,
        auth: AuthContext = Depends(require_actors(*EVENT_CREATORS)),
    ):
        db = get_session(normalized_site_id)
        normalized_event_type = validate_event_permission(auth.actor, request.event_type)

        event = Event(
            event_id=next_event_id(),
            container_id=request.container_id,
            site_id=normalized_site_id,
            event_type=normalized_event_type,
            timestamp=datetime.now(timezone.utc),
            payload=request.payload,
            sync_status="PENDING",
            sequence_number=1,
        )

        routing_key = f"{normalized_site_id.lower()}.{event.event_type.lower()}"

        try:
            db.execute(text("""
                INSERT INTO events (
                    event_id, container_id, site_id, event_type,
                    payload, timestamp, sync_status, sequence_number
                )
                VALUES (
                    :event_id, :container_id, :site_id, :event_type,
                    :payload, :timestamp, :sync_status, :sequence_number
                )
            """), {
                **event.model_dump(),
                "payload": json.dumps(event.payload),
            })

            db.execute(text("""
                INSERT INTO container_state (
                    container_id, current_location, last_event, last_updated
                )
                VALUES (
                    :container_id, :site_id, :event_type, :timestamp
                )
                ON CONFLICT (container_id)
                DO UPDATE SET
                    current_location = EXCLUDED.current_location,
                    last_event = EXCLUDED.last_event,
                    last_updated = EXCLUDED.last_updated
            """), {
                "container_id": str(event.container_id),
                "site_id": event.site_id,
                "event_type": event.event_type,
                "timestamp": event.timestamp,
            })

            db.execute(text("""
                INSERT INTO outbox_events (
                    event_id, source_site_id, routing_key, payload, status, created_at
                )
                VALUES (
                    :event_id, :source_site_id, :routing_key, :payload, 'PENDING', :created_at
                )
            """), {
                "event_id": str(event.event_id),
                "source_site_id": normalized_site_id,
                "routing_key": routing_key,
                "payload": json.dumps(event.model_dump(mode="json")),
                "created_at": event.timestamp,
            })

            db.commit()

            try:
                from shared.messaging.outbox import flush_outbox
                flush_outbox(normalized_site_id, limit=1)
                final_sync_status = "SENT"
            except Exception:
                final_sync_status = "PENDING"

            return {
                "message": "event created",
                "event": event,
                "sync_status": final_sync_status,
                "performed_by_actor": auth.actor,
            }

        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(exc))
        finally:
            db.close()

    @app.on_event("startup")
    def startup():
        start_outbox_worker(normalized_site_id)
        start_consumer(normalized_site_id)

    return app
