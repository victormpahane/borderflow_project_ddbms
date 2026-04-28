import pika
import json
import threading
from sqlalchemy import text

from shared.db.session import get_session
from shared.models.event import Event

RABBITMQ_URL = "amqp://guest:guest@127.0.0.1:5672/"


def start_consumer(site_id: str):
    def consume():
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()

        channel.exchange_declare(
            exchange="borderflow.events",
            exchange_type="topic",
            durable=True
        )

        queue_name = f"{site_id.lower()}_queue"

        channel.queue_declare(queue=queue_name, durable=True)

        channel.queue_bind(
            exchange="borderflow.events",
            queue=queue_name,
            routing_key="#"
        )

        print(f"[{site_id}] Waiting for messages...")

        def callback(ch, method, properties, body):
            db = get_session(site_id)

            try:
                data = json.loads(body)
                event = Event(**data)

                if event.site_id.upper() == site_id.upper():
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return

                exists = db.execute(
                    text("SELECT 1 FROM inbox_events WHERE event_id = :id"),
                    {"id": str(event.event_id)}
                ).fetchone()

                if exists:
                    db.commit()
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    print(f"[{site_id}] Duplicate event ignored")
                    return

                db.execute(
                    text("""
                        INSERT INTO inbox_events (
                            event_id, source_site_id, payload, received_at
                        )
                        VALUES (
                            :event_id, :source_site_id, :payload, NOW()
                        )
                    """),
                    {
                        "event_id": str(event.event_id),
                        "source_site_id": event.site_id,
                        "payload": json.dumps(event.model_dump(mode="json")),
                    }
                )

                db.execute(
                    text("""
                    INSERT INTO events (
                        event_id, container_id, site_id, event_type,
                        payload, timestamp, sync_status, sequence_number
                    )
                    VALUES (
                        :event_id, :container_id, :site_id, :event_type,
                        :payload, :timestamp, 'RECEIVED', :sequence_number
                    )
                    """),
                    {
                        **event.model_dump(),
                        "payload": json.dumps(event.payload),
                    }
                )

                db.execute(
                    text("""
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
                    """),
                    {
                        "container_id": str(event.container_id),
                        "site_id": event.site_id,
                        "event_type": event.event_type,
                        "timestamp": event.timestamp
                    }
                )

                db.commit()
                ch.basic_ack(delivery_tag=method.delivery_tag)
                print(f"[{site_id}] Event stored & projection updated")

            except Exception as e:
                print(f"[{site_id}] Error: {e}")
                db.rollback()
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            finally:
                db.close()

        channel.basic_consume(
            queue=queue_name,
            on_message_callback=callback,
            auto_ack=False
        )

        channel.start_consuming()

    thread = threading.Thread(target=consume, daemon=True)
    thread.start()
    return thread
