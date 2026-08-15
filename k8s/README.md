# Manifiestos Kubernetes — EcoNexo

Deploy a EKS (o cualquier cluster):

```bash
kubectl apply -f k8s/00-namespace-config.yaml
kubectl apply -f k8s/10-api.yaml
kubectl apply -f k8s/11-web.yaml
kubectl apply -f k8s/20-services.yaml
```

- **Datos gestionados en prod:** PostGIS → RDS, MQTT → AWS IoT Core, S3 → S3 (no se despliegan como pods).
- **Secretos** via `econexo-secrets` (mapear a Secrets Manager / External Secrets Operator).
- **satellite** corre como `CronJob` (equivalente a Lambda + EventBridge).
- Cada servicio tiene deployment (+ service donde expone puerto) y toma config del ConfigMap compartido.
