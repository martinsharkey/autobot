# LLM Gateway Load Balancer

This example builds a simple API gateway that load-balances chat completion requests across multiple public LLM providers.

## What it does

- exposes an OpenAI-compatible endpoint: `POST /v1/chat/completions`
- selects from active providers in `providers.yaml`
- retries/falls back on error
- optionally requires a gateway API key

## Setup

1. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

2. Copy the environment template:

```bash
copy .env.example .env
```

3. Fill your API keys in `.env`

4. Run the app:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Alternatively, use the helper script on Windows:

```powershell
./run-gateway.ps1
```

## Using the gateway

Send a normal OpenAI chat completion request to your gateway.

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer changeme" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Hello from the gateway"}]}'
```

## Sample Continue.dev setup

If Continue.dev supports custom OpenAI-compatible endpoints, set:

- `OPENAI_API_BASE=http://127.0.0.1:8000/v1`
- `OPENAI_API_KEY=changeme`
- `OPENAI_API_TYPE=openai`

If it uses a YAML config file, use this sample:

```yaml
provider: openai
base_url: http://127.0.0.1:8000/v1
api_key: changeme
```

## Adding providers

Open `providers.yaml` and add new entries. Each provider entry includes:

- `name`
- `base_url`
- `api_key_env`
- `api_key_prefix`
- `completions_path`
- `active`
- `weight`

The gateway is intentionally generic and can work with any OpenAI-compatible provider.

## Notes

- Free or credit-based providers may have unreliable quotas.
- Keep tokens low when testing.
- Use the `/v1/providers` endpoint to inspect active provider configs.
- If the gateway returns `503`, verify your provider API keys in `.env` and then restart the gateway. The gateway needs at least one valid upstream provider key.
