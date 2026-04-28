Build the application image first:

```bash
docker build -t borderflow:latest .
```

Apply the stack:

```bash
kubectl apply -f infrastructure/k8s/namespace.yaml
kubectl apply -f infrastructure/k8s/configmap.yaml
kubectl apply -f infrastructure/k8s/postgres-config.yaml
kubectl apply -f infrastructure/k8s/postgres.yaml
kubectl apply -f infrastructure/k8s/rabbitmq.yaml
kubectl apply -f infrastructure/k8s/apps.yaml
```

Open the control tower through NodePort:

```bash
kubectl get svc -n borderflow control-tower
```

The service listens on port `30010`.
