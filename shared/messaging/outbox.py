import json
import threading
import time
from datetime import datetime, timezone

from sqlalchemy import text

from shared.db.session import get_session
from shared.messaging.publisher import publish_raw_event


def flush_outbox(site_id: str, limit: int = 100):
    db = get_session(site_id)

    try:
        pending_rows = db.execute(
            text("""
                SELECT event_id, payload, routing_key
                FROM outbox_events
                WHERE status = 'PENDING'
                ORDER BY created_at
                LIMIT :limit
            """),
            {"limit": limit},
        ).mappings().all()

        sent_count = 0

        for row in pending_rows:
            publish_raw_event(row["routing_key"], json.dumps(row["payload"], default=str))
            db.execute(
                text("""
                    UPDATE outbox_events
                    SET status = 'SENT',
                        sent_at = :sent_at
                    WHERE event_id = :event_id
                """),
                {
                    "event_id": row["event_id"],
                    "sent_at": datetime.now(timezone.utc),
                },
            )
            db.execute(
                text("""
                    UPDATE events
                    SET sync_status = 'SENT'
                    WHERE event_id = :event_id
                """),
                {"event_id": row["event_id"]},
            )
            sent_count += 1

        db.commit()
        return sent_count

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def start_outbox_worker(site_id: str, poll_interval_seconds: int = 5):
    def worker():
        while True:
            try:
                flush_outbox(site_id)
            except Exception as exc:
                print(f"[{site_id}] Outbox worker error: {exc}")
            time.sleep(poll_interval_seconds)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread
