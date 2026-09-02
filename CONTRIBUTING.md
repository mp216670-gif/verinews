# Contributing to VeriNews

Thank you for your interest in contributing! This guide will help you get started.

## 🛠️ Development Setup

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/verinews.git
   cd verinews
   ```
3. Create and activate a **virtual environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   source .venv/bin/activate # macOS/Linux
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Copy `.env.example` to `.env` and set values:
   ```bash
   cp .env.example .env
   ```

## 🌿 Branch Naming

| Type | Pattern | Example |
|---|---|---|
| Feature | `feat/<short-description>` | `feat/rss-feed-ingestion` |
| Bug fix | `fix/<short-description>` | `fix/trust-score-rounding` |
| Documentation | `docs/<short-description>` | `docs/api-reference` |
| Tests | `test/<short-description>` | `test/ingestion-adapters` |

## ✅ Before Submitting a Pull Request

1. **Run tests** and ensure all pass:
   ```bash
   python -m pytest tests/ -v
   ```
2. **Keep commits focused** — one logical change per commit
3. **Write meaningful commit messages** using [Conventional Commits](https://www.conventionalcommits.org/):
   ```
   feat: add Google Fact Check API fallback provider
   fix: resolve trust score rounding issue for grade boundaries
   docs: update API reference for public verify endpoint
   ```
4. **Add tests** for any new behaviour
5. **Do not commit** `.env`, `*.db`, or any secrets

## 📐 Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) conventions
- Use type hints everywhere
- Add docstrings to all public functions and classes
- Keep functions small and single-purpose

## 📂 Key Files to Know

| File | Purpose |
|---|---|
| `app/api/public.py` | Public fact-check endpoint (no auth) |
| `app/services/fact_checking/rule_engine.py` | Pattern matching for misinformation |
| `app/services/trust_scoring/scorer.py` | 4-pillar score computation |
| `app/static/index.html` | Single-page public UI |
| `tests/` | All automated tests |

## 🐛 Reporting Bugs

Open an [Issue](../../issues/new) and include:
- Python version (`python --version`)
- Operating system
- Steps to reproduce
- Expected vs actual behaviour
- Any relevant error output

## 💡 Suggesting Features

Open an [Issue](../../issues/new) with the label `enhancement` and describe:
- The problem you're trying to solve
- Your proposed solution
- Any alternatives you considered

## 📄 License

By contributing, you agree your changes will be licensed under the [MIT License](./LICENSE).
