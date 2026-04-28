# BorderFlow Demo Guide

This guide gives you a clean demonstration path for:

- normal distributed event flow
- health/status visibility
- offline simulation / partition tolerance
- final submission verification

## 1. Start the stack

### Local process mode

Start one terminal per service:

```bash
cd /home/victor/borderflow
./bin/run-depot.sh
./bin/run-border.sh
./bin/run-port.sh
./bin/run-destination.sh
./bin/run-control-tower.sh
```

### Docker Compose mode

```bash
cd /home/victor/borderflow
docker compose up --build
```

Open the control tower:

```text
http://127.0.0.1:8010
```

## 2. Baseline health demo

Show that every site is alive:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8002/health
curl http://127.0.0.1:8003/health
curl http://127.0.0.1:8010/health
```

What to point out:

- database connectivity is visible
- RabbitMQ connectivity is visible
- pending outbox count is visible
- control tower shows total healthy sites

## 3. Normal event propagation demo

Create an event at Depot:

```bash
curl -i -X POST http://127.0.0.1:8000/events/ \
  -H "Content-Type: application/json" \
  -d '{"container_id":"CONT-001","event_type":"ARRIVED","payload":{"operator":"demo"}}'
```

Then verify:

### Depot local write

```bash
psql "postgresql://bf_user:bf_password@127.0.0.1:5432/borderflow_depot" \
  -c "select event_id, container_id, site_id, event_type, sync_status from events order by timestamp desc limit 5;"
```

### Destination replicated receive

```bash
psql "postgresql://bf_user:bf_password@127.0.0.1:5432/borderflow_destination" \
  -c "select event_id, source_site_id, received_at from inbox_events order by received_at desc limit 5;"
```

What to point out:

- the event is stored locally first
- the event is added to the outbox
- RabbitMQ carries it to other sites
- another site records the message in `inbox_events`
- the final state appears in the destination site database

## 4. Offline simulation demo

This is the most important distributed-systems demonstration.

### Goal

Show that a site can continue to work locally even when another site or the messaging layer is unavailable, then recover later.

### Option A: Simulate one site being offline

If using Docker Compose, stop one site:

```bash
docker compose stop destination
```

If using local processes, stop the destination terminal with `Ctrl+C`.

Now create an event at Depot:

```bash
curl -i -X POST http://127.0.0.1:8000/events/ \
  -H "Content-Type: application/json" \
  -d '{"container_id":"CONT-OFFLINE-1","event_type":"HELD","payload":{"reason":"destination offline demo"}}'
```

Verify:

```bash
psql "postgresql://bf_user:bf_password@127.0.0.1:5432/borderflow_depot" \
  -c "select event_id, container_id, site_id, event_type, sync_status from events order by timestamp desc limit 5;"
```

Then bring the destination back:

```bash
docker compose start destination
```

or restart the local destination process:

```bash
cd /home/victor/borderflow
./bin/run-destination.sh
```

Then verify destination catches up:

```bash
psql "postgresql://bf_user:bf_password@127.0.0.1:5432/borderflow_destination" \
  -c "select event_id, source_site_id, received_at from inbox_events order by received_at desc limit 5;"
```

What to say:

- Depot stayed available
- the source site still accepted the event
- once the offline site returned, event synchronization resumed

### Option B: Simulate RabbitMQ outage

Stop RabbitMQ:

```bash
docker compose stop rabbitmq
```

Create an event at Depot:

```bash
curl -i -X POST http://127.0.0.1:8000/events/ \
  -H "Content-Type: application/json" \
  -d '{"container_id":"CONT-OFFLINE-2","event_type":"DELAYED","payload":{"reason":"mq offline demo"}}'
```

Now inspect Depot outbox:

```bash
psql "postgresql://bf_user:bf_password@127.0.0.1:5432/borderflow_depot" \
  -c "select event_id, status, routing_key, created_at, sent_at from outbox_events order by created_at desc limit 5;"
```

Expected:

- the event exists locally
- outbox row remains `PENDING`

Bring RabbitMQ back:

```bash
docker compose start rabbitmq
```

Wait a few seconds, then inspect again:

```bash
psql "postgresql://bf_user:bf_password@127.0.0.1:5432/borderflow_depot" \
  -c "select event_id, status, routing_key, created_at, sent_at from outbox_events order by created_at desc limit 5;"
```

Expected:

- `PENDING` becomes `SENT`
- downstream sites receive the event

What to say:

- the system tolerated a messaging outage
- no event was lost
- synchronization resumed automatically through the outbox worker

## 5. Control tower demo

Open:

```text
http://127.0.0.1:8010
```

Point out:

- per-site health cards
- total events
- pending outbox pressure
- live recent event feed

Useful API views:

```bash
curl http://127.0.0.1:8010/api/overview
curl http://127.0.0.1:8010/api/events
```

## 6. Smoke test demo

Run:

```bash
cd /home/victor/borderflow
./venv/bin/python -m tests.smoke_test
```

What to say:

- the stack has automated checks
- health endpoints are verified
- event propagation is verified automatically
- control tower aggregation is verified too

## 7. Kubernetes / k3s demo

Build the image:

```bash
docker build -t borderflow:latest .
```

Apply manifests:

```bash
kubectl apply -f infrastructure/k8s/namespace.yaml
kubectl apply -f infrastructure/k8s/configmap.yaml
kubectl apply -f infrastructure/k8s/postgres-config.yaml
kubectl apply -f infrastructure/k8s/postgres.yaml
kubectl apply -f infrastructure/k8s/rabbitmq.yaml
kubectl apply -f infrastructure/k8s/apps.yaml
```

Verify:

```bash
kubectl get pods -n borderflow
kubectl get svc -n borderflow
```

Control tower is exposed on NodePort `30010`.

## 8. Final submission checklist

- all services start
- control tower loads
- normal event propagation works
- offline simulation works
- smoke tests pass
- Docker Compose works
- Kubernetes manifests exist
- Git repo is committed
- GitHub remote is connected and pushed

## 9. What to mention to the lecturer

- each site has its own local database
- the source site writes locally before synchronization
- outbox protects events during outages
- inbox prevents duplicate reprocessing
- RabbitMQ provides asynchronous distribution
- the control tower aggregates operational state across the system
