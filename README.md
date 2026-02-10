# PDF Processor API

REST API that transforms veterinary diagnostic PDF reports into structured JSON data. Extracts patient metadata, diagnosis, recommendations, and medical images using Google Cloud Platform services.

**Stack:** Python 3.11 | FastAPI | Document AI | Cloud Storage | Firestore | Docker

**Live API:** https://pdf-processor-954383017603.us-central1.run.app

**Swagger Docs:** https://pdf-processor-954383017603.us-central1.run.app/docs

## Quick Start

```bash
# Install dependencies
poetry install

# Configure environment
cp .env.example .env
# Fill in your GCP credentials and JWT secret

# Run locally
poetry run uvicorn app.main:app --reload --port 8000

# Or with Docker
docker compose up --build
```

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/auth/register` | No | Register a new user (sends verification email) |
| `GET`  | `/auth/verify?token=` | No | Verify email address |
| `POST` | `/auth/token` | No | Login with username/password, returns JWT |
| `POST` | `/pdf/upload` | Bearer | Upload a PDF for processing |
| `GET`  | `/pdf/{document_id}` | Bearer | Retrieve a processed record |
| `GET`  | `/health` | No | Health check |

## Usage

```bash
# 1. Register a new user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"caio","email":"caio@example.com","password":"secret123"}'

# 2. Verify email (use the token from the verification email)
curl http://localhost:8000/auth/verify?token=TOKEN_FROM_EMAIL

# 3. Get a token (or use the pre-seeded admin/changeme123)
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -d "username=admin&password=changeme123" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 4. Upload a PDF
curl -X POST http://localhost:8000/pdf/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@report.pdf"

# 5. Retrieve by document_id
curl http://localhost:8000/pdf/{document_id} \
  -H "Authorization: Bearer $TOKEN"
```

## Response Example

```json
{
  "document_id": "80f730bc10a4",
  "filename": "Informe_radiologico_Chester.pdf",
  "gcs_uri": "gs://bucket/uploads/20260210_80f730bc10a4_Informe.pdf",
  "total_pages": 6,
  "images": [
    {
      "page_number": 3,
      "gcs_uri": "gs://bucket/extracted_images/80f730bc10a4/page3_img0.jpeg",
      "width": 1024,
      "height": 768,
      "mime_type": "image/jpeg"
    }
  ],
  "report_info": {
    "patient_name": "Chester",
    "species": "Canino",
    "breed": "Dobermann",
    "sex": "Macho",
    "age": null,
    "owner_name": "Naveda",
    "veterinarian": "Dra. Gerbeno",
    "date": "11/03/2022",
    "diagnosis": "Imágenes sugerentes de osteosarcoma en húmero derecho.",
    "recommendations": null
  },
  "processing_time_seconds": 7.294
}
```

## Architecture

```
Client
  |
  v
+--------------------------------------------------+
|  FastAPI  (Cloud Run)                            |
|                                                  |
|  /auth/*      /pdf/upload    /pdf/{id}           |
|       |              |              |            |
|  +----v--------------v--------------v---------+  |
|  |              Service Layer                 |  |
|  |  Auth · Email · DocumentAI · ReportParser  |  |
|  |  Storage  ·  Firestore                     |  |
|  +-----+------------+-------------+----------+  |
+---------+------------+-------------+-------------+
          |            |             |
          v            v             v
    +-----------+ +---------+ +----------+
    |Document AI| | Cloud   | |Firestore |
    |  (OCR)    | | Storage | | (NoSQL)  |
    +-----------+ +---------+ +----------+
```

### Processing Pipeline

1. **Validate** -- MIME type, magic bytes (`%PDF-`), file size, filename sanitization
2. **Upload PDF** to Cloud Storage
3. **Extract text** via Document AI (auto-chunks PDFs >15 pages)
4. **Extract images** via PyMuPDF with deduplication (filters logos, icons, headers)
5. **Upload images** to Cloud Storage
6. **Parse report fields** -- regex-based extraction of patient, owner, vet, diagnosis, recommendations
7. **Save record** to Firestore
8. **Return** structured JSON response

## GCP Services

| Service | Role |
|---------|------|
| **Document AI** | OCR text extraction from PDF pages. Handles scanned documents, mixed layouts, multi-language. Auto-chunking for large PDFs (>15 pages). |
| **Cloud Storage** | Persistent storage for original PDFs and extracted medical images. Organized by document ID. |
| **Firestore** | NoSQL database for structured metadata and user accounts. Document-oriented model maps naturally to the per-PDF record and user structures. Serverless, scales automatically. |

## Security

- **JWT authentication** (Bearer tokens) on all data endpoints
- **Email verification** required before login
- **bcrypt** password hashing
- **Rate limiting** (10 req/min per IP via SlowAPI)
- **Multi-layer file validation** (MIME type + magic bytes + size limit)
- **Filename sanitization** (path traversal prevention, unsafe character replacement)
- **Non-root Docker user**
- **No secrets in code** -- all config via environment variables
- **CORS** restricted by default

## Project Structure

```
app/
  config.py                # Settings from env vars (pydantic-settings)
  dependencies.py          # DI: auth guard, rate limiter
  exceptions.py            # Custom exception hierarchy
  main.py                  # App factory + GCP service initialization
  models/
    auth.py                # Token, User, Register models
    pdf.py                 # ReportInfo, PDFRecord, PageInfo, ImageInfo
  routers/
    auth.py                # POST /auth/token, /auth/register, GET /auth/verify
    health.py              # GET /health
    pdf.py                 # POST /pdf/upload, GET /pdf/{id}
  services/
    auth.py                # JWT creation + verification, bcrypt
    document_ai.py         # Document AI client + auto-chunking
    email.py               # Gmail SMTP verification emails
    firestore.py           # Firestore CRUD (PDF records + users)
    report_parser.py       # Veterinary report field extraction
    storage.py             # Cloud Storage uploads (PDF + images)
tests/
  conftest.py              # Fixtures with mocked GCP services
  test_auth.py             # Auth flow tests
  test_register.py         # Registration + verification tests
  test_firestore.py        # Firestore service tests
  test_health.py           # Health check test
  test_pdf.py              # Upload + GET endpoint tests
  test_report_parser.py    # Parser unit tests
```

## Tests

```bash
poetry run pytest tests/ -v       # 53 tests
poetry run ruff check app/ tests/ # Linter
```

All GCP services are mocked in tests -- no real credentials needed to run the suite.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `JWT_SECRET_KEY` | Yes | Secret for signing JWT tokens |
| `GCP_PROJECT_ID` | Yes | Google Cloud project ID |
| `GCP_PROCESSOR_ID` | Yes | Document AI processor ID |
| `GCS_BUCKET_NAME` | Yes | Cloud Storage bucket name |
| `GCP_LOCATION` | No | Document AI region (default: `us`) |
| `FIRESTORE_DATABASE` | No | Firestore database (default: `(default)`) |
| `JWT_ALGORITHM` | No | JWT algorithm (default: `HS256`) |
| `JWT_EXPIRE_MINUTES` | No | Token expiry (default: `30`) |
| `RATE_LIMIT` | No | Rate limit (default: `10/minute`) |
| `MAX_FILE_SIZE_MB` | No | Max upload size (default: `20`) |
| `DEBUG` | No | Enable Swagger docs (default: `false`) |
| `SMTP_HOST` | No | SMTP server hostname (default: `smtp.gmail.com`) |
| `SMTP_PORT` | No | SMTP server port (default: `587`) |
| `SMTP_USER` | No | SMTP username / email |
| `SMTP_PASSWORD` | No | SMTP password / app password |
| `SMTP_FROM_EMAIL` | No | Sender email address |

## Deploy to Cloud Run

```bash
# Build
gcloud builds submit --tag gcr.io/$PROJECT_ID/pdf-processor

# Deploy
gcloud run deploy pdf-processor \
  --image gcr.io/$PROJECT_ID/pdf-processor \
  --platform managed \
  --region us-central1 \
  --set-env-vars "JWT_SECRET_KEY=...,GCP_PROJECT_ID=...,GCP_PROCESSOR_ID=...,GCS_BUCKET_NAME=..."
```
