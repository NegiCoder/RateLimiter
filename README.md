# Rate Limiter v2 — Redis Token Bucket

A production-style **FastAPI rate limiting service** using Redis and the
**Token Bucket Algorithm**. It includes a small web dashboard for testing
requests, watching token state, and demonstrating `429 Too Many Requests`.

---

## Overview

Rate limiting controls how many requests a client can send in a period of time.
It protects APIs from abuse, accidental spikes, brute-force attempts, and noisy
clients that can overload backend resources.

This version stores each client's token bucket in **Redis** and updates it with
a **Lua script**, so refill + consume happens atomically even under concurrent
requests.

---

## Architecture

```mermaid
flowchart TD
    A[Client / Dashboard] --> B[FastAPI App]
    B --> C[RateLimiterMiddleware]
    C --> D{Excluded Path?}
    D -->|Yes| E[Forward Request]
    D -->|No| F[Identify Client by IP]
    F --> G[Redis Lua Token Bucket]
    G --> H{Token Available?}
    H -->|Yes| I[Consume Token]
    I --> J[Allow Request + Headers]
    H -->|No| K[Return 429 Too Many Requests]
```

---

## Features

- FastAPI middleware that intercepts requests before route handlers
- Redis-backed token bucket state per client IP
- Atomic Lua script for concurrency-safe refill and consume
- `X-RateLimit-Limit` and `X-RateLimit-Remaining` response headers
- Built-in dashboard for visual testing
- Debug endpoints for bucket state and reset
- Free deployment path: **Render + Upstash Redis**

---

## Token Bucket Algorithm

Each client has a bucket with a maximum capacity. A request consumes one token.
Tokens refill over time based on the configured refill rate.

Example:

- Capacity: `10`
- Refill rate: `1 token/second`

The client can send 10 requests immediately when the bucket is full. After that,
requests are allowed only as tokens refill. If the bucket has fewer than one
token, the API returns `429 Too Many Requests`.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI, Uvicorn |
| Middleware | Starlette `BaseHTTPMiddleware` |
| Store | Redis |
| Atomic logic | Redis Lua script |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Deployment | Render + Upstash Redis |

---

## Project Structure

```bash
RateLimiter/
├── app/
│   ├── core/
│   │   ├── config.py          # Environment variables
│   │   └── redis.py           # Redis client from REDIS_URL
│   ├── middleware/
│   │   └── rate_limiter_redis.py
│   ├── services/
│   │   └── token_bucket_redis.py
│   └── main.py                # FastAPI app + debug endpoints
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   └── js/app.js
├── .env.example
├── render.yaml
├── requirements.txt
└── README.md
```

---

## API Endpoints

| Method | Endpoint | Rate limited? | Purpose |
|--------|----------|---------------|---------|
| `GET` | `/` | No | Web dashboard |
| `GET` | `/health` | No | API + Redis health |
| `GET` | `/test` | Yes | Demo endpoint that consumes tokens |
| `GET` | `/debug/me` | No | Current client bucket |
| `POST` | `/debug/reset` | No | Reset current client bucket |
| `GET` | `/docs` | No | Swagger docs |

---

## Local Setup

You need **Redis** running locally, or use a free **Upstash** URL in `.env`.

### Option A — Upstash (easiest, no local Redis install)

1. Create a free database at [upstash.com](https://upstash.com)
2. Copy the Redis URL
3. Create `.env`:

```bash
cp .env.example .env
# paste your Upstash URL into REDIS_URL=
```

### Option B — Local Redis

```bash
# macOS
brew install redis
brew services start redis

# or Docker
docker run -d --name redis -p 6379:6379 redis:7
```

### Run the app

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

Open:

- Dashboard: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs

### Quick API test (terminal)

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/test
curl http://127.0.0.1:8000/debug/me
```

Run `/test` many times — after capacity is used you should see `429`.

### UI test checklist

1. Open http://127.0.0.1:8000
2. Confirm **Redis = Connected**
3. Click **Send 1 Request** → log shows `200`
4. Click **Run 12-Request Burst** → some `200`, then `429`
5. Watch **Tokens left** meter drop
6. Click **Reset Bucket** → tokens go back to full
7. Wait a few seconds → tokens refill slowly (1/sec)

### Self-check

```bash
python test_allowed_parse.py
```

---

## Free Deployment

Use **Upstash Redis** for the database and **Render** for the FastAPI service.

### Render settings

| Setting | Value |
|---------|-------|
| Branch | `v2-redis` |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

### Environment variables

| Key | Example |
|-----|---------|
| `REDIS_URL` | `rediss://default:password@host:6379` |
| `RATE_LIMIT_CAPACITY` | `10` |
| `RATE_LIMIT_REFILL_RATE` | `1` |

---

## Interview Summary

This project demonstrates how real backend systems protect APIs using a
middleware-based rate limiter. Every request passes through the middleware,
which identifies the client, runs an atomic Redis token bucket check, then
either allows the request or rejects it with HTTP `429`.