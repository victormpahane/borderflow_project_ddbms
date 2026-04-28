import json
import os
import time
import unittest
import urllib.request

import psycopg2


BASE_URLS = {
    "DEPOT": os.getenv("DEPOT_URL", "http://127.0.0.1:8000"),
    "BORDER": os.getenv("BORDER_URL", "http://127.0.0.1:8001"),
    "PORT": os.getenv("PORT_URL", "http://127.0.0.1:8002"),
    "DESTINATION": os.getenv("DESTINATION_URL", "http://127.0.0.1:8003"),
}
CONTROL_TOWER_URL = os.getenv("CONTROL_TOWER_URL", "http://127.0.0.1:8010")

DATABASES = {
    "DEPOT": os.getenv("DEPOT_DATABASE_URL", "postgresql://bf_user:bf_password@127.0.0.1:5432/borderflow_depot"),
    "BORDER": os.getenv("BORDER_DATABASE_URL", "postgresql://bf_user:bf_password@127.0.0.1:5432/borderflow_border"),
    "PORT": os.getenv("PORT_DATABASE_URL", "postgresql://bf_user:bf_password@127.0.0.1:5432/borderflow_port"),
    "DESTINATION": os.getenv("DESTINATION_DATABASE_URL", "postgresql://bf_user:bf_password@127.0.0.1:5432/borderflow_destination"),
}


def fetch_json(url: str, method: str = "GET", body: dict | None = None):
    data = None
    headers = {}
    if body is not None:
      data = json.dumps(body).encode("utf-8")
      headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def query_value(database_url: str, sql: str, params: tuple = ()):
    with psycopg2.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()


class BorderFlowSmokeTest(unittest.TestCase):
    def test_health_endpoints(self):
        for site_id, base_url in BASE_URLS.items():
            with self.subTest(site_id=site_id):
                payload = fetch_json(f"{base_url}/health")
                self.assertIn(payload["status"], {"ok", "degraded"})

        overview = fetch_json(f"{CONTROL_TOWER_URL}/api/overview")
        self.assertEqual(overview["total_sites"], 4)

    def test_event_propagation(self):
        container_id = f"SMOKE-{int(time.time())}"

        response = fetch_json(
            f"{BASE_URLS['DEPOT']}/events/",
            method="POST",
            body={
                "container_id": container_id,
                "event_type": "ARRIVED",
                "payload": {"source": "smoke-test"},
            },
        )
        self.assertEqual(response["message"], "event created")

        deadline = time.time() + 15
        while time.time() < deadline:
            result = query_value(
                DATABASES["DESTINATION"],
                """
                SELECT container_id
                FROM events
                WHERE container_id = %s
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (container_id,),
            )
            if result:
                break
            time.sleep(1)
        else:
            self.fail("Event did not propagate to destination within 15 seconds")


if __name__ == "__main__":
    unittest.main()
