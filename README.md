# BorderFlow

This project expects local infrastructure that is not included in the codebase:

- PostgreSQL on `127.0.0.1:5432`
- RabbitMQ on `127.0.0.1:5672`
- Four PostgreSQL databases, one per site

## Rebuild the virtual environment

```bash
cd /home/victor/borderflow
rm -rf venv
python3 -m virtualenv venv
./venv/bin/pip install -r requirements.txt
```

## Create the databases

Run the bootstrap script once as a PostgreSQL superuser:

```bash
psql -U postgres -f scripts/bootstrap_postgres.sql
```

Then apply the schema to each database:

```bash
for db in borderflow_depot borderflow_border borderflow_port borderflow_destination; do
  psql -U postgres -d "$db" -f scripts/schema.sql
done
```

If `psql` is not available, apply the schema with the project environment:

```bash
cd /home/victor/borderflow
./venv/bin/python -m scripts.apply_schema
```

If you are switching from the old UUID-based schema to the new simple string ID schema, reset each database first:

```bash
psql "postgresql://bf_user:bf_password@127.0.0.1:5432/borderflow_depot" -f scripts/reset_schema.sql
psql "postgresql://bf_user:bf_password@127.0.0.1:5432/borderflow_border" -f scripts/reset_schema.sql
psql "postgresql://bf_user:bf_password@127.0.0.1:5432/borderflow_port" -f scripts/reset_schema.sql
psql "postgresql://bf_user:bf_password@127.0.0.1:5432/borderflow_destination" -f scripts/reset_schema.sql
```

Then apply `scripts/schema.sql` again.

If Docker Compose was already started before the privilege fix, reset the Compose Postgres volume once so the init scripts rerun:

```bash
docker compose down -v
docker compose up --build
```

## Optional environment overrides

The services now support per-site overrides:

- `DEPOT_DATABASE_URL`
- `BORDER_DATABASE_URL`
- `PORT_DATABASE_URL`
- `DESTINATION_DATABASE_URL`

Example:

```bash
export DEPOT_DATABASE_URL='postgresql://bf_user:bf_password@127.0.0.1:5432/borderflow_depot'
```

## Health checks

- `GET /health` on every site service

These endpoints report:

- DB connectivity
- RabbitMQ connectivity
- pending outbox count

Example:

```bash
curl -H "X-API-Key: management-demo-key" http://127.0.0.1:8000/health
```

## RBAC

The APIs use API-key-based RBAC based on the intended users from the handout:

- `depot_operations_controller`
- `truck_driver`
- `yard_depot_clerk`
- `border_liaison`
- `port_agent`
- `management_compliance`
- `customer_service_client`

Permission model:

- `management_compliance` can access health, audit, KPIs, and the control tower
- `customer_service_client` can use read-only global tracking
- `depot_operations_controller` can create any event type and read internal views
- `truck_driver` can create driver confirmation milestones only
- `yard_depot_clerk` can create depot gate and seal events
- `border_liaison` can create clearance and handover events
- `port_agent` can create port milestone events

Default demo keys:

- `depot-controller-demo-key`
- `truck-driver-demo-key`
- `yard-clerk-demo-key`
- `border-liaison-demo-key`
- `port-agent-demo-key`
- `management-demo-key`
- `client-demo-key`

Pass the key with:

```bash
-H "X-API-Key: management-demo-key"
```

Override keys and actors with the `BORDERFLOW_API_KEYS` environment variable using:

```text
api-key-1:depot_operations_controller,api-key-2:management_compliance,api-key-3:customer_service_client
```

## Start the services

Use the launcher scripts so the project always uses its own virtual environment:

```bash
./bin/run-depot.sh
./bin/run-border.sh
./bin/run-port.sh
./bin/run-destination.sh
./bin/run-control-tower.sh
```

Ports:

- Depot: `127.0.0.1:8000`
- Border: `127.0.0.1:8001`
- Port: `127.0.0.1:8002`
- Destination: `127.0.0.1:8003`
- Control Tower: `127.0.0.1:8010`

## Event creation

The API accepts simple string container IDs.

Example:

```bash
curl -X POST http://127.0.0.1:8000/events/ \
  -H "X-API-Key: depot-controller-demo-key" \
  -H "Content-Type: application/json" \
  -d '{"container_id":"CONT-001","event_type":"ARRIVED","payload":{}}'
```

## Control tower

The control tower is a live dashboard and API surface that aggregates all sites:

- `GET /` for the dashboard UI
- `GET /api/overview` for the full summary payload
- `GET /api/events` for recent global events
- `GET /api/tracking/{container_id}` for read-only tracking
- `GET /tracking` for the customer/client tracking page
- `GET /sites/DEPOT`, `GET /sites/BORDER`, `GET /sites/PORT`, `GET /sites/DESTINATION` for separate site dashboards

Open the dashboard with a viewer key:

```text
http://127.0.0.1:8010/?api_key=management-demo-key
```

Client tracking page:

```text
http://127.0.0.1:8010/tracking?api_key=client-demo-key
```

## Docker Compose

Bring up the full stack with:

```bash
docker compose up --build
```

That starts:

- PostgreSQL with all four site databases
- RabbitMQ with the management UI
- Depot, Border, Port, Destination
- Control Tower

Control Tower will be available at `http://127.0.0.1:8010`.

When running alongside local services, Docker Compose exposes:

- PostgreSQL on `127.0.0.1:55432`
- RabbitMQ on `127.0.0.1:55672`
- RabbitMQ management UI on `127.0.0.1:15673`

If you inspect the Docker Compose databases from your host with `psql`, use port `55432`.

## Kubernetes / k3s

Kubernetes manifests are in `infrastructure/k8s`.

Build the image:

```bash
docker build -t borderflow:latest .
```

Apply the manifests:

```bash
kubectl apply -k infrastructure/k8s
```

The control tower is exposed as a NodePort on `30010`.

If your k3s/container runtime does not already have the `borderflow:latest` image, import or rebuild it in the cluster runtime before applying the manifests.

Equivalent expanded apply path:

```bash
kubectl apply -f infrastructure/k8s/namespace.yaml
kubectl apply -f infrastructure/k8s/configmap.yaml
kubectl apply -f infrastructure/k8s/postgres-config.yaml
kubectl apply -f infrastructure/k8s/postgres.yaml
kubectl apply -f infrastructure/k8s/rabbitmq.yaml
kubectl apply -f infrastructure/k8s/apps.yaml
```

## Smoke tests

Run the smoke tests against the live stack with:

```bash
cd /home/victor/borderflow
./venv/bin/python -m tests.smoke_test
```

## Demo guide

A full demonstration guide, including offline simulation and lecturer talking points, is in `DEMO.md`.

## Architecture notes

The current implementation now aligns more closely with the handout:

- each site has its own API and database
- events are stored locally first
- pending messages are persisted in `outbox_events`
- received messages are deduplicated in `inbox_events`
- a background outbox worker retries pending publishes

## Git and GitHub

Git is required for submission. You still need to:

1. commit the project
2. create or connect a GitHub remote
3. push the branch to GitHub
