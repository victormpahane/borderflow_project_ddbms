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
  -H "Content-Type: application/json" \
  -d '{"container_id":"CONT-001","event_type":"ARRIVED","payload":{}}'
```

## Control tower

The control tower is a live dashboard and API surface that aggregates all sites:

- `GET /` for the dashboard UI
- `GET /api/overview` for the full summary payload
- `GET /api/events` for recent global events

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

## Kubernetes / k3s

Kubernetes manifests are in `infrastructure/k8s`.

Build the image:

```bash
docker build -t borderflow:latest .
```

Apply the manifests:

```bash
kubectl apply -f infrastructure/k8s/namespace.yaml
kubectl apply -f infrastructure/k8s/configmap.yaml
kubectl apply -f infrastructure/k8s/postgres-config.yaml
kubectl apply -f infrastructure/k8s/postgres.yaml
kubectl apply -f infrastructure/k8s/rabbitmq.yaml
kubectl apply -f infrastructure/k8s/apps.yaml
```

The control tower is exposed as a NodePort on `30010`.

You can also apply everything with:

```bash
kubectl apply -k infrastructure/k8s
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
