# SupportFlow AI

SupportFlow AI is a local support-operations copilot that turns incoming customer tickets into structured triage decisions, routing metadata, escalation signals, safe draft replies, and integration-ready automation payloads.

## What it demonstrates

- Structured LLM classification validated with Pydantic
- Category, priority, sentiment, confidence, and routing decisions
- Policy-aware reply drafting without unsupported promises
- Human escalation for security, fraud, chargeback, legal, and outage risks
- JSON automation payloads for helpdesk or CRM integrations
- Local inference through Ollama with no paid API dependency
- Streamlit operator interface and FastAPI webhook
- Automated tests for analysis validation, routing, and export

## Architecture

```text
Customer ticket + account context + support policy
                      ↓
          Ollama / Qwen3 structured analysis
                      ↓
              Pydantic validation
                      ↓
Triage decision + draft reply + automation payload
                      ↓
          Human review / helpdesk integration
```

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
ollama pull qwen3:8b
streamlit run streamlit_app.py
```

The interface opens at `http://127.0.0.1:8501`. Ollama must be running locally on port `11434`.

## Webhook API

```powershell
uvicorn app.api:app --reload
```

- `GET /health` — provider and model status
- `POST /webhooks/tickets` — analyze, route, and draft a response

## Docker

```powershell
docker compose up --build
```

The container connects to Ollama on the Windows host through `host.docker.internal` and exposes the UI on `http://127.0.0.1:8503`.

## Safety safeguards

- Draft replies require human approval before sending.
- The model cannot promise refunds, credits, deadlines, or security outcomes without policy context.
- High-risk ticket patterns explicitly require escalation.
- Missing information results in clarification steps instead of invented facts.
- Invalid structured responses are rejected rather than silently displayed.

## Portfolio status

Personal demonstration project. It does not represent work completed for a client.

