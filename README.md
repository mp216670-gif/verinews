# 🛡️ VeriNews — Public News Authentication & Fact-Checking Platform

> **Verify any news in seconds. No login required. Fully explainable results.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%2B-red)](https://www.sqlalchemy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Tests](https://img.shields.io/badge/Tests-13%20passing-brightgreen)](./tests/)

VeriNews is a **free, open-source news authentication platform** built for the general public. Anyone can paste a news article link or headline and get an instant, explainable **Trust Score** (Grade A–D) with claim-by-claim verdicts — no account needed.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔍 **Instant Public Verifier** | Paste any URL or headline — no login required |
| 📊 **Explainable Trust Score** | 4-pillar scoring: Source, Claims, Corroboration, Recency |
| 🏷️ **Letter Grades (A–D)** | Clear, human-readable verdict on any story |
| ✅ **Claim-by-Claim Breakdown** | Each statement tagged `TRUE`, `MISLEADING`, or `FALSE` |
| 🔗 **URL Scraper** | Automatically extract content from live news links |
| 📰 **Magazine Editorial Feed** | Verified stories in a clean BloguLikes-inspired layout |
| 🚨 **Misinformation Alerts** | Flagged stories highlighted with red Grade D warnings |
| 🔐 **Role-Based API** | Reporter & Admin roles for institutional use via REST API |
| 📡 **REST API + OpenAPI Docs** | Full Swagger UI at `/docs` |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** (tested on Python 3.14)
- `pip` package manager

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/verinews.git
cd verinews
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On macOS/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
DATABASE_URL=sqlite:///./news_auth.db
JWT_SECRET=local-development-only-jwt-secret
FACT_CHECK_API_KEY=optional-google-api-key
```

> **Note:** The app works fully out of the box with SQLite. No external database server needed.

### 5. Run the Development Server

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000** in your browser. The database is auto-created and seeded with demo stories on first run.

---

## 🌐 How to Use (General Public)

No account needed. Just visit the homepage:

1. **Paste a URL** → Any live news link (BBC, Reuters, a blog, etc.)
2. **Or type a headline** → Paste the headline or any claim text
3. **Click "Check Truth"** → Results appear in under 2 seconds

### What the Results Mean

| Grade | Score | Meaning |
|---|---|---|
| 🟢 **A** | 85–100 | Highly credible — verified institutional source with supported claims |
| 🔵 **B** | 70–84 | Generally reliable — minor gaps in attribution or corroboration |
| 🟡 **C** | 50–69 | Questionable — unverified claims or weak sourcing, read with caution |
| 🔴 **D** | 0–49 | Disputed / Likely Fake — matches misinformation patterns or false claims |

### 4-Pillar Scoring System

```
Overall Trust Score = (Source Reliability × 30%)
                    + (Claim Accuracy × 40%)
                    + (Corroboration × 15%)
                    + (Recency × 15%)
```

| Pillar | Weight | What It Checks |
|---|---|---|
| **Source Reliability** | 30% | Publisher domain, HTTPS, named author |
| **Claim Accuracy** | 40% | Each statement checked against known fact patterns |
| **Corroboration** | 15% | Direct quotes, named witnesses, third-party citations |
| **Recency** | 15% | How fresh/recent the news is |

---

## 📁 Project Structure

```
verinews/
├── app/
│   ├── api/
│   │   ├── public.py          # 🌐 Public verify endpoint (no auth)
│   │   ├── auth.py            # JWT authentication
│   │   ├── articles.py        # Article CRUD
│   │   ├── verification.py    # Fact-check & trust score endpoints
│   │   ├── admin.py           # Admin governance endpoints
│   │   ├── deps.py            # Auth dependencies & role enforcement
│   │   └── routes.py          # Router registry
│   ├── core/
│   │   ├── config.py          # Pydantic Settings
│   │   ├── database.py        # SQLAlchemy engine & session
│   │   └── security.py        # Password hashing (bcrypt) & JWT
│   ├── models/
│   │   ├── user.py            # User model + UserRole enum
│   │   ├── article.py         # Article model (category, image_url)
│   │   ├── verification.py    # Claim & VerificationReport models
│   │   └── trust_score.py     # TrustScore model with JSON audit trail
│   ├── schemas/               # Pydantic V2 schemas (from_attributes)
│   ├── services/
│   │   ├── ingestion/         # URL scraper, RSS, text adapters
│   │   ├── fact_checking/     # Rule-based + Google Fact Check API
│   │   └── trust_scoring/     # 4-pillar explainable scorer
│   ├── static/
│   │   └── index.html         # BloguLikes editorial public UI
│   └── main.py                # App setup, lifespan seeding, CORS
├── tests/
│   ├── conftest.py            # pytest fixtures & test DB
│   ├── test_api.py            # End-to-end API tests (public verify)
│   ├── test_auth.py           # JWT & password hashing tests
│   ├── test_ingestion.py      # Scraper adapter tests
│   ├── test_fact_checking.py  # Fact-check engine tests
│   └── test_trust_scoring.py  # Trust score engine tests
├── docs/
│   └── screenshots/
├── .env.example               # Safe environment variable template
├── .gitignore
├── LICENSE
└── requirements.txt
```

---

## 🔌 API Reference

### Public Endpoint (No Auth Required)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/public/verify` | **Instant fact-check** — paste URL or text |
| `GET` | `/api/v1/articles` | Browse verified article feed |
| `GET` | `/api/v1/articles/{id}` | Get a single article with trust score |
| `GET` | `/api/v1/articles/{id}/trust-score` | Get the full explainable score |
| `GET` | `/api/v1/articles/{id}/report` | Get the full fact-check report |

### Example: Instant Public Fact-Check

```bash
# Check a suspicious headline
curl -X POST http://localhost:8000/api/v1/public/verify \
  -H "Content-Type: application/json" \
  -d '{"title": "Secret mineral cures all diseases guaranteed 100%"}'

# Check a live news URL
curl -X POST http://localhost:8000/api/v1/public/verify \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/news-article"}'
```

**Response:**
```json
{
  "article_id": 12,
  "title": "Secret mineral cures all diseases guaranteed 100%",
  "overall_score": 33.5,
  "grade": "D",
  "provider_verdict": "Disputed / Likely False",
  "explanation": {
    "summary": "Critical flag: 3 claims determined to be FALSE...",
    "positive_signals": [],
    "risk_factors": ["Medical misinformation pattern detected", "No institutional source"]
  },
  "claims": [
    {
      "claim_text": "Secret mineral cures all diseases guaranteed 100%",
      "verdict": "false",
      "confidence": 0.95,
      "explanation": "Known medical misinformation pattern"
    }
  ]
}
```

### Reporter / Admin Endpoints (JWT Required)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Public | Register account |
| `POST` | `/api/v1/auth/login` | Public | Get JWT token |
| `POST` | `/api/v1/articles` | Reporter+ | Submit article for review |
| `POST` | `/api/v1/articles/{id}/verify` | Reporter+ | Run fact-check on article |
| `POST` | `/api/v1/articles/{id}/review` | Reporter+ | Human calibration of score |
| `GET` | `/api/v1/admin/metrics` | Admin | Platform-wide statistics |

Full interactive docs: **http://localhost:8000/docs**

---

## 🧪 Running Tests

```bash
python -m pytest tests/ -v
```

```
tests/test_api.py::test_health_endpoint                         PASSED
tests/test_api.py::test_end_to_end_article_verification_lifecycle PASSED
tests/test_api.py::test_instant_verification_public_no_auth     PASSED
tests/test_auth.py::test_password_hashing                       PASSED
tests/test_auth.py::test_jwt_token_generation_and_decoding      PASSED
tests/test_auth.py::test_user_registration_and_login            PASSED
tests/test_fact_checking.py::test_fact_check_credible_article   PASSED
tests/test_fact_checking.py::test_fact_check_disinformation     PASSED
tests/test_ingestion.py::test_text_ingestion_adapter            PASSED
tests/test_ingestion.py::test_url_scraper_html_parsing          PASSED
tests/test_trust_scoring.py::test_trust_scoring_high_credibility PASSED
tests/test_trust_scoring.py::test_trust_scoring_low_credibility PASSED
tests/test_trust_scoring.py::test_reviewer_calibration          PASSED

13 passed in 4.12s
```

---

## ⚙️ Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./news_auth.db` | SQLite (local) or PostgreSQL URL |
| `JWT_SECRET` | Local-only fallback | JWT signing secret — **required on Vercel** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | JWT token lifetime (24 hours) |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `FACT_CHECK_API_KEY` | *(empty)* | Optional: Google Fact Check Tools API key |

### Using PostgreSQL (Production)

```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/verinews
```

Install the PostgreSQL driver:
```bash
pip install "psycopg[binary]"
```

### Deploying to Vercel

Vercel requires a persistent PostgreSQL database; SQLite is intentionally rejected in this environment. Configure these production environment variables before deploying:

```env
DATABASE_URL=postgresql+psycopg://...
JWT_SECRET=a-long-random-secret
SEED_DEMO_DATA=false
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_PASSWORD=a-unique-strong-password
```

The initial administrator is provisioned only when that username does not already exist. Public registration creates reader accounts in production; an administrator promotes institutional users through the admin API.

---

## 🤝 Contributing

Contributions are welcome. Please open an issue or pull request with a clear description and tests for behavior changes.

Quick contribution steps:
1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Commit changes: `git commit -m "feat: add my feature"`
4. Push and open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](./LICENSE) for details.

---

## 🙏 Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/) — Modern Python web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) — Python SQL toolkit
- [BloguLikes Theme by SteelThemes](https://ecosystem.hubspot.com/marketplace/website/blogulikes-theme-by-steelthemes) — UI design inspiration
- [Google Fact Check Tools API](https://developers.google.com/fact-check/tools/api) — External fact-check data source
