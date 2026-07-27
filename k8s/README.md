# Kubernetes — referencia EcoNexo

Estos manifiestos son una base de arquitectura, no deben aplicarse sin reemplazar dominios, secretos, imágenes y servicios administrados.

## Archivos

- `00-namespace-config.yaml`: namespace, configuración y Secret de ejemplo.
- `10-api.yaml`: API con dos réplicas, probes, recursos y usuario no-root de imagen.
- `11-web.yaml`: web con dos réplicas.
- `20-services.yaml`: ingest, notify, anomaly y CronJob satelital.
- `30-availability.yaml`: PodDisruptionBudgets.
- `40-ingress.example.yaml`: ejemplo TLS/NGINX; adaptar al proveedor.

## Orden sugerido

```bash
kubectl apply -f k8s/00-namespace-config.yaml
kubectl apply -f k8s/10-api.yaml
kubectl apply -f k8s/11-web.yaml
kubectl apply -f k8s/20-services.yaml
kubectl apply -f k8s/30-availability.yaml
# Sólo después de adaptar DNS/TLS:
kubectl apply -f k8s/40-ingress.example.yaml
```

## Requisitos

- Reemplazar Secret por External Secrets/Secrets Manager.
- Usar imágenes por digest, no `latest`.
- Ejecutar migraciones en un job único antes del rollout.
- Usar RDS/PostGIS, IoT Core/broker TLS y S3 privado fuera del cluster.
- Construir la imagen web con sus `NEXT_PUBLIC_*`; no se cambian sólo con env runtime.
- Definir NetworkPolicies según el ingress/CNI real.
- Agregar autoscaling luego de medir CPU, memoria, latencia y colas.

## Puerta Misiones

Antes del rollout publico, aplicar migraciones 01-09, sincronizar GeoRef con `POST /territory/sync-georef`, confirmar `official: true` en `/territory/boundary-status` y dejar en cero la vista `misiones_external_data_audit`. Mantener `ALLOW_DEMO_SATELLITE_FIXTURES=false`.
