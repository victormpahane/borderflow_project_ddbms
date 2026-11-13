import json
import os

import pika
from shared.models.event import Event

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@127.0.0.1:5672/")


def publish_raw_event(routing_key: str, body: str):
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    channel.exchange_declare(
        exchange="borderflow.events",
        exchange_type="topic",
        durable=True
    )

    channel.basic_publish(
        exchange="borderflow.events",
        routing_key=routing_key,
        body=body,
    )

    connection.close()


def publish_event(event: Event):
    routing_key = f"{event.site_id.lower()}.{event.event_type.lower()}"
    publish_raw_event(routing_key, event.model_dump_json())
