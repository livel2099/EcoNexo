# Aplicar EcoNexo Misiones 1.0.0-rc.2

## 1. Migrar la base existente

Desde la raíz del proyecto:

```powershell
docker compose exec -T postgis psql -U econexo -d econexo -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/10_copernicus_forestry_pests.sql
```

## 2. Reconstruir servicios

```powershell
docker compose up -d --build --force-recreate api web
```

## 3. Configurar Copernicus

1. Crear una configuración Sentinel Hub en Copernicus Data Space.
2. Copiar la URL `https://sh.dataspace.copernicus.eu/ogc/wms/INSTANCE_ID`.
3. Abrir `Admin Core > Fuentes SpaceAI`.
4. Pegar la URL y pulsar `Probar GetCapabilities`.
5. Copiar los nombres reales de las capas en color natural, NDVI, humedad y área quemada.
6. Activar Copernicus y guardar.

## 4. Probar

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/ready
```

Abrir `http://localhost:3000`, entrar a Centro de Comando y seleccionar NDVI. La capa se carga a partir de zoom 9.

## 5. Sanidad forestal

Abrir `Plagas forestales`. El módulo está centrado en San Antonio e incluye como contexto regional el radar meteorológico de Bernardo de Irigoyen. El radar no diagnostica ni identifica especies de plagas.
