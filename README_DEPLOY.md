# StockAI v2.0 — Deployment Guide

## Architecture Overview

StockAI uses a **split deployment** (Option A):

| Component | Platform | Purpose |
|-----------|----------|---------|
| **Frontend** (HTML/CSS/JS) | Vercel | Static file hosting + API proxy rewrites |
| **Backend** (FastAPI/Python) | Render / Railway / Fly.io | Long-running simulation engine, WebSocket, SQLite |

> **Why split?** Vercel serverless functions have a 10-second execution limit, no persistent filesystem, and no WebSocket support on the free tier. The simulation engine requires all three.

---

## What Works Where

| Feature | Vercel (Frontend) | Backend (Render) |
|---------|:-:|:-:|
| Landing page | ✅ | — |
| Live Market Monitor | ✅ (proxied to backend) | ✅ |
| Simulation Console | ✅ (proxied to backend) | ✅ |
| Workspace | ✅ (proxied to backend) | ✅ |
| WebSocket (live ticks) | ❌ (free tier) | ✅ |
| Chatbot (LLM) | ✅ (proxied) | ✅ |
| SQLite persistence | — | ✅ |

---

## Deploy Frontend to Vercel

### Prerequisites
- [Vercel CLI](https://vercel.com/docs/cli) installed (`npm i -g vercel`)
- A Vercel account (free tier works)

### Steps

1. **Update `vercel.json`** — Replace `your-backend-url.onrender.com` with your actual Render backend URL:
   ```json
   { "source": "/api/(.*)", "destination": "https://YOUR-BACKEND.onrender.com/api/$1" }
   ```

2. **Deploy**:
   ```bash
   cd StockAI
   vercel --prod
   ```

3. Vercel will detect the `vercel.json` config and:
   - Serve HTML files from `frontend/`
   - Proxy all API calls (`/api/*`, `/chat`, `/simulation/*`, etc.) to your Render backend

---

## Deploy Backend to Render

### Prerequisites
- A [Render](https://render.com) account (free tier works)
- The repository pushed to GitHub

### Steps

1. **Create a new Web Service** on Render:
   - **Repository**: Connect your GitHub repo
   - **Root Directory**: `StockAI`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python backend/run.py`
   - **Python Version**: 3.11+

2. **Set Environment Variables** in Render dashboard:
   | Variable | Required | Description |
   |----------|:--------:|-------------|
   | `GROQ_API_KEY` | Optional | Groq API key for LLM agents (free at console.groq.com) |
   | `GOOGLE_API_KEY` | Optional | Gemini API key (free at aistudio.google.com) |
   | `INDIA_MARKET_API_KEY` | Optional | Twelve Data key for Indian market data |

   > The app runs in **mock mode** without LLM keys — all features work, but agent decisions use hardcoded logic instead of live LLM calls.

3. **Health Check**: After deploy, verify at `https://YOUR-BACKEND.onrender.com/health`

---

## Deploy Backend to Railway (Alternative)

1. **Create a new project** on [Railway](https://railway.app)
2. **Connect GitHub** and select the repo
3. **Set root**: `StockAI`
4. **Start command**: `python backend/run.py`
5. **Add environment variables** (same as Render table above)
6. Railway auto-detects Python and installs from `requirements.txt`

---

## Environment Variables Reference

See `.env.example` for the full list. Copy it to `.env` for local development:

```bash
cp .env.example .env
# Edit .env with your API keys
```

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | Groq LLM provider (free, recommended) |
| `GOOGLE_API_KEY` | — | Google Gemini provider (free tier) |
| `OLLAMA_HOST` | `http://localhost:11434` | Local Ollama for offline LLM |
| `OPENAI_API_KEY` | — | OpenAI (paid, optional) |
| `INDIA_MARKET_API_KEY` | — | Twelve Data for NSE/BSE data |

---

## Local Development

```bash
cd StockAI
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python backend/run.py
# Open http://127.0.0.1:8000
```

## Running Tests

```bash
python -m pytest tests/ -v --tb=short
```
