# api-marketplace — Marketplace Events API (F4) MercadAndes

## Architecture: Clean Architecture

This API follows **Clean Architecture**, with a clear separation of concerns:

```
src/marketplace/
├── domain/           # ⚫ Entities and ports (interfaces) — no external dependencies
├── application/      # ⚫ Use cases and DTOs — business logic
├── infrastructure/   # ⚫ Concrete implementations: JSONL, configuration
└── presentation/     # ⚫ FastAPI, routes, dependencies — entry point
```

## What it contains

This API corresponds to source **F4** from the data sources table: **Marketplace Orders Events**.

It generates marketplace order lifecycle events:

- `created → paid → shipped → delivered/cancelled/returned`
- Configurable fault injection (duplicates and out-of-order)
- Deterministic IDs with uuid5 for reproducibility

It is fully self-contained: it does not depend on any other API.

## Function

- Generate marketplace order lifecycle events.
- Apply post-dispatch rule: canceling after `shipped` becomes `returned`.
- Inject duplicate events with the same `event_id` (configurable rate).
- Inject temporal disorder (out-of-order) with configurable maximum lag (default 6 hours).
- Write events to JSONL file (and ready for Kafka in the future).
- Executable as a Python module or Docker container independently.

## How to run

### Locally (without Docker)

```powershell
# 1. Copy the environment variables file
Copy-Item .env.example .env

# 2. Edit .env with your settings (optional)
# Notepad .env

# 3. Install dependencies
uv sync --locked

# 4. Run the API
uv run uvicorn marketplace.presentation.fastapi.main:app --host 0.0.0.0 --port 8000
```

Or directly as a module:

```powershell
uv run python -m marketplace.presentation.main
```

### With Docker

```bash
# Build the image
docker build -t api-marketplace:latest .

# Run the container
docker run --rm --env-file .env -p 8000:8000 api-marketplace:latest

# Run with volume to save JSONL file to your machine
docker run --rm --env-file .env -v "${PWD}/data/raw:/app/data/raw" -p 8000:8000 api-marketplace:latest
```

### Test the API

Once running at `http://localhost:8000`:

#### Generate 10 events (default mode)

```powershell
curl.exe -X POST "http://localhost:8000/api/v1/marketplace/events?orders=10&seed=42"
```

#### Generate 50 events with 10% duplicates

```powershell
curl.exe -X POST "http://localhost:8000/api/v1/marketplace/events?orders=50&duplicate_rate=0.1"
```

#### Generate 30 events with out-of-order enabled

```powershell
curl.exe -X POST "http://localhost:8000/api/v1/marketplace/events?orders=30&ooo_enabled=true"
```

#### Generate 100 events with custom seed

```powershell
curl -X POST "http://localhost:8000/api/v1/marketplace/events?orders=100&seed=12345"
```

#### View interactive documentation (Swagger UI)

Open in your browser:

```
http://localhost:8000/docs
```

Or the OpenAPI specification:

```
http://localhost:8000/openapi.json
```

#### Verify the API is alive

```powershell
curl.exe http://localhost:8000/
```

Expected response:

```json
{"status": "ok", "service": "api-marketplace", "version": "1.0.0"}
```

---

## Environment variables

Create an `.env` file based on `.env.example`. Available variables:

| Variable                    | Description                                      | Default                                                      |
| --------------------------- | ------------------------------------------------ | ------------------------------------------------------------ |
| `APP_ENV`                 | Execution environment                            | `development`                                              |
| `API_HOST`                | Server host                                      | `0.0.0.0`                                                  |
| `API_PORT`                | Server port                                      | `8000`                                                     |
| `MASTER_SEED`             | Seed for deterministic event generation          | `42`                                                       |
| `F4_DUPLICATE_RATE`       | Duplicate event rate (0.0 to 1.0)                | `0.0`                                                      |
| `F4_OOO_ENABLED`          | Enable out-of-order (temporal disorder)          | `false`                                                    |
| `F4_OOO_MAX_LAG_SEC`      | Maximum arrival lag in seconds (max 21600 = 6h)  | `21600`                                                    |
| `OUTPUT_FILE`             | Output JSONL file path                           | `data/raw/events.jsonl`                                    |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka servers (for future streaming)             | `localhost:9092`                                           |
| `KAFKA_TOPIC`             | Kafka topic name                                 | `marketplace.events`                                       |
| `KAFKA_ENABLED`           | Enable Kafka publishing                          | `false`                                                    |
| `VALID_TOKENS`            | Valid tokens separated by comma (authentication) | `token-seller-123,bearer-token-mercaandes-2026,test-token` |

---

## Endpoints

| Method   | Route                          | Description                            | Query parameters                                                       |
| -------- | ------------------------------ | -------------------------------------- | ---------------------------------------------------------------------- |
| `POST` | `/api/v1/marketplace/events` | Generate marketplace events (F4)       | `orders`, `seed`, `duplicate_rate`, `ooo_enabled`, `max_lag` |
| `GET`  | `/docs`                      | Interactive documentation (Swagger UI) | —                                                                     |
| `GET`  | `/openapi.json`              | OpenAPI specification                  | —                                                                     |
| `GET`  | `/`                          | Health check                           | —                                                                     |

### Parameters for `POST /api/v1/marketplace/events`

| Parameter          | Type        | Required | Description                         | Default   |
| ------------------ | ----------- | -------- | ----------------------------------- | --------- |
| `orders`         | `integer` | No       | Number of orders to generate        | `100`   |
| `seed`           | `integer` | No       | Seed for deterministic generation   | `42`    |
| `duplicate_rate` | `number`  | No       | Duplicate rate (0.0 to 1.0)         | `0.0`   |
| `ooo_enabled`    | `boolean` | No       | Enable out-of-order                 | `false` |
| `max_lag`        | `integer` | No       | Maximum lag in seconds (0 to 21600) | `21600` |

---

## Example responses

### Successful response (abbreviated):

```json
{
  "seed": 42,
  "n_orders": 10,
  "events_count": 36,
  "events": [
    {
      "event_id": "e8f3a2b1-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
      "order_id": "ORD-42-000001",
      "event_type": "created",
      "sku": "SKU-ELEC-CO-00001",
      "store_id": "STO-CO-FIS-001",
      "seller_id": "SEL-CO-PRV-001",
      "country": "CO",
      "quantity": 2,
      "unit_price": 450000.00,
      "event_ts": "2026-01-15T00:00:00+00:00",
      "arrival_ts": "2026-01-15T00:00:00+00:00"
    },
    {
      "event_id": "e8f3a2b1-1a2b-3c4d-5e6f-7a8b9c0d1e3g",
      "order_id": "ORD-42-000001",
      "event_type": "paid",
      "sku": "SKU-ELEC-CO-00001",
      "store_id": "STO-CO-FIS-001",
      "seller_id": "SEL-CO-PRV-001",
      "country": "CO",
      "quantity": 2,
      "unit_price": 450000.00,
      "event_ts": "2026-01-15T00:05:30+00:00",
      "arrival_ts": "2026-01-15T00:05:30+00:00"
    }
  ]
}
```

### Error response (invalid token or simulated fault):

```json
{
  "detail": "Forbidden: Invalid seller token"
}
```

Or with simulated fault (rate limit):

```json
{
  "detail": "Rate limit exceeded. Try again later."
}
```

---

## CI/CD

Each push to `main` or `develop` activates `.github/workflows/ci.yml`:

1. **test**: Install dependencies with `uv`, run `ruff check` and `pytest`.
2. **build-and-push**: Build Docker image and push to GitHub Container Registry (GHCR).

## Folder structure (Clean Architecture)

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
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── entities/
│       │   │   ├── __init__.py
│       │   │   ├── event.py          # Entity: marketplace event
│       │   │   └── order.py          # Entity: order and lifecycle
│       │   └── repositories/
│       │       ├── __init__.py
│       │       └── event_producer_repository.py  # Interface (port)
│       ├── application/
│       │   ├── __init__.py
│       │   ├── use_cases/
│       │   │   ├── __init__.py
│       │   │   ├── dto.py            # Data transfer objects
│       │   │   └── generate_marketplace_events.py  # Main use case
│       │   └── services/
│       ├── infrastructure/
│       │   ├── __init__.py
│       │   ├── config.py             # Environment variables
│       │   └── persistence/
│       │           ├── __init__.py
│       │           └── marketplace_producer_repository.py  # JSONL implementation
│       └── presentation/
│           ├── __init__.py
│           ├── fastapi/
│           │   ├── __init__.py
│           │   ├── deps.py           # Dependency injection
│           │   ├── main.py           # FastAPI app
│           │   └── routes/
│           │       ├── __init__.py
│           │       └── marketplace.py    # POST /api/v1/marketplace/events
│           └── main.py               # uvicorn entry point
├── tests/
│   └── unit/
│       ├── __init__.py
│       ├── test_marketplace.py
│       └── test_producer.py
└── .github/
    └── workflows/
        └── ci.yml
```
