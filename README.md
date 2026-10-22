# Marketplace_Api — Productor de Eventos Marketplace (F4) MercadAndes

## Arquitectura

Servicio independiente para generación de eventos del ciclo de vida de órdenes de marketplace. Produce eventos deterministas con IDs basados en uuid5, soportando inyección de fallos configurables (duplicados y fuera de orden).

Es completamente autocontenido: no depende de ninguna otra carpeta ni librería externa aparte de sus dependencias de Python.

## Función

- Generar eventos de ciclo de vida: created → paid → shipped → delivered/cancelled/returned.
- Aplicar regla post-dispatch: cancelar después de shipped se convierte en returned.
- Inyectar duplicados con ID idéntico (configurable por tasa).
- Inyectar desorden temporal (out-of-order) con lag máximo de 6 horas.
- Generar IDs deterministas con uuid5 para reproducibilidad.
- Escribir eventos en formato JSONL.
- Ejecutable como módulo Python o contenedor Docker independiente.

## Modo de ejecución

### Localmente

```powershell
Copy-Item .env.example .env
# Editar .env si es necesario
uv sync --locked
uv run python -m marketplace.producer --orders 100
```

### Con Docker

```bash
Copy-Item .env.example .env
docker build -t api-marketplace:latest .
# --rm elimina el contenedor al terminar
# -v monta el volumen para que el archivo events.jsonl quede en tu PC
docker run --rm --env-file .env -v "${PWD}/data/raw:/app/data/raw" api-marketplace:latest --orders 100
```

## Variables de entorno

| Variable               | Descripción                             | Valor por defecto         |
| ---------------------- | ---------------------------------------- | ------------------------- |
| `MASTER_SEED`        | Seed para generación                    | `42`                    |
| `F4_DUPLICATE_RATE`  | Tasa de duplicados (0-1)                 | `0.0`                   |
| `F4_OOO_ENABLED`     | Habilitar out-of-order                   | `false`                 |
| `F4_OOO_MAX_LAG_SEC` | Lag máximo en segundos (max 21600 = 6h) | `21600`                 |
| `OUTPUT_FILE`        | Archivo de salida JSONL                  | `data/raw/events.jsonl` |

## Parámetros de línea de comandos

| Parámetro           | Descripción                  | Valor por defecto             |
| -------------------- | ----------------------------- | ----------------------------- |
| `--seed`           | Seed para generación         | `42`                        |
| `--orders`         | Número de órdenes a generar | `100`                       |
| `--duplicate-rate` | Tasa de duplicados inyectados | `0.0`                       |
| `--ooo`            | Habilitar out-of-order        | (flag)                        |
| `--max-lag`        | Lag máximo en segundos       | `21600`                     |
| `--start`          | Fecha de inicio ISO           | `2026-01-01T00:00:00+00:00` |
| `--out`            | Archivo de salida             | `data/raw/events.jsonl`     |

## CI/CD

Cada push a `main` o `develop` activa `.github/workflows/ci.yml`:

1. `uv sync --locked --dev`
2. `uv run ruff check`
3. `uv run pytest`
4. Build de imagen Docker y push a GHCR

## Estructura

```
api-marketplace/
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
├── Dockerfile
├── src/
│   └── marketplace/
│       ├── __init__.py
│       ├── config.py
│       ├── lifecycle.py
│       ├── faults.py
│       └── producer.py
└── tests/
    └── unit/
        ├── test_lifecycle.py
        └── test_faults.py
```
