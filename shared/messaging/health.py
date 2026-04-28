import pika


RABBITMQ_URL = "amqp://guest:guest@127.0.0.1:5672/"


def get_rabbitmq_health():
    try:
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        connection.close()
        return {"ok": True, "error": None}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
