# Bulk Certificate Generator API

A Django 5 + Django REST Framework backend for generating bulk certificates asynchronously with Celery and Redis, while tracking job progress and allowing download of individual or grouped certificate artifacts.

## Architecture Overview

This project uses:

- Django 5.x for the web API and ORM
- Django REST Framework for request validation and API responses
- Celery + Redis for asynchronous bulk generation
- SQLite as the default local development database and PostgreSQL as the production/Docker database option
- Pillow for certificate rendering from a predefined template

Celery and Redis were chosen because bulk certificate generation is naturally asynchronous and can take longer than a synchronous HTTP request. Offloading generation to a worker keeps the API responsive, allows progress tracking, and isolates one recipient failure from the rest of the batch.

## Repository Layout

```text
.
├── assets/
│   └── template.png
├── certificates_api/
│   ├── migrations/
│   ├── services/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── tasks.py
│   ├── urls.py
│   └── views.py
├── certificates_project/
│   ├── __init__.py
│   ├── asgi.py
│   ├── celery.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── tests/
│   ├── __init__.py
│   └── test_api.py
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── manage.py
├── pyproject.toml
├── README.md
├── requirements.txt
└── db.sqlite3
```

## Local Setup (Virtualenv)

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install project dependencies:

```bash
pip install -r requirements.txt
```

3. Copy environment variables:

```bash
cp .env.example .env
```

4. Run database migrations:

```bash
python manage.py migrate
```

5. Start Redis locally if needed:

```bash
redis-server
```

6. Start the Django development server:

```bash
python manage.py runserver 0.0.0.0:8000
```

7. Start the Celery worker in a second terminal:

```bash
celery -A certificates_project worker -l info
```

## Docker Setup

From the project root:

```bash
docker compose up --build
```

This starts:

- Django app on http://localhost:8000
- PostgreSQL on port 5432
- Redis on port 6379
- Celery worker process

If you want to rebuild the database after changing models:

```bash
docker compose exec web python manage.py migrate
```

## API Contract

### 1) Create a bulk generation job

Endpoint:

```http
POST /api/certificates/generate/
```

Example request:

```bash
curl -X POST http://localhost:8000/api/certificates/generate/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python Bootcamp",
    "recipients": [
      {"name": "Alice Johnson", "email": "alice@example.com", "course": "Python Foundations"},
      {"name": "Bob Smith", "email": "bob@example.com", "course": "Python Foundations"}
    ]
  }'
```

Response:

```json
{
  "job_id": "<uuid>",
  "status": "PENDING"
}
```

### 2) Fetch overall job status

```bash
curl http://localhost:8000/api/certificates/jobs/<job_id>/
```

### 3) Download a single certificate

```bash
curl -L http://localhost:8000/api/certificates/<certificate_id>/download/ -o certificate.png
```

### 4) Download all successful certificates in a job as a ZIP archive

```bash
curl -L http://localhost:8000/api/certificates/jobs/<job_id>/download-all/ -o certificates.zip
```

## Test Suite

Run the included tests with:

```bash
python manage.py test
```

The suite covers:

- valid job creation
- malformed payload validation
- certificate generation workflow
- partial failure handling
- single certificate download
- bulk zip download

## Notes on Fault Tolerance

Each recipient is processed independently inside the Celery task. If any one recipient fails validation or rendering, the job continues to process the remaining recipients. The overall job is marked as completed only after all recipients have been evaluated.

## Production Notes

- For production, set an actual secret key and enable PostgreSQL via environment variables.
- Use a real Redis service rather than local-process Redis in production.
- Set proper media storage and file permissions for generated certificate artifacts.
- Configure Celery workers with process supervision (for example, Supervisor, systemd, or Kubernetes).
