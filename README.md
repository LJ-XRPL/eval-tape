# Eval Tape

X bot for **@evaltape** — posts when a real LLM ships, then again when independent evals land.

**Bio:** Frontier + open-weight drops + independent evals. No vendor scorecards.

Two post types only: **SHIPPED** and **EVALS**.

## What it covers

| | |
|---|---|
| Closed labs | OpenAI, Anthropic, Google, xAI, Amazon, Microsoft/Azure |
| Open-weight families | Meta/Llama, DeepSeek, Mistral, Alibaba/Qwen, Kimi/Moonshot, MiniMax, Gemma, GLM, Cohere |

Skipped: fine-tunes, merges, GGUF re-uploads, app/CLI bumps, “now in the UI” of a model already posted, vendor self-benches, image/video models (v2).

Every post is tagged **Open** or **Closed**. Cap **3 posts/day**. If several evals land together → one ranked list.

## How it works

```
src/
  detect.py   # official lab RSS + allowlisted HF orgs → SHIPPED candidates
  evals.py    # Artificial Analysis poll, match to shipped models
  cards.py    # Pillow PNG cards (16:9) — no image-gen API
  post.py     # X API v2 + media; source URL as first reply
  state.py    # state.json load/save
  main.py     # one Actions run
  captions.py # caption formatter
  config.py   # allowlist + palettes
```

On each run:

1. Detect new allowlisted models since `state.json` → SHIPPED card + tweet (+ reply with canonical URL).
2. For shipped models missing evals, poll Artificial Analysis → EVALS card + tweet.
3. Commit updated `state.json`.

**First run seeds state and posts nothing** (no history dump).

**Dry-run** (`DRY_RUN=true`, default): logs tweet text, renders cards under `out/`, does **not** call X.

## Setup

### 1. X pay-per-use API

1. Create a project/app at [developer.x.com](https://developer.x.com/).
2. Enable **Read and Write** with **OAuth 1.0a** user context for the @evaltape account.
3. Buy **pay-per-use** credits for API v2 posting + media upload.
4. Copy: API Key, API Secret, Access Token, Access Token Secret.

Posts **with a URL in the status text cost more and are throttled** — Eval Tape never puts URLs in the tweet body. The source link goes in the **first reply**.

### 2. Artificial Analysis key

1. Create an account on the [Artificial Analysis Insights Platform](https://artificialanalysis.ai/).
2. Generate an API key (`x-api-key` header).
3. Free tier: **1000 req/day** — responses are cached in `state.json` (default 6h).

Endpoint used:

`GET https://artificialanalysis.ai/api/v2/data/llms/models`

Attribution is required — EVALS cards and captions name **Artificial Analysis**.

### 3. GitHub secrets

Repo → Settings → Secrets and variables → Actions:

| Secret | Required | Notes |
|---|---|---|
| `X_API_KEY` | for live | OAuth consumer key |
| `X_API_SECRET` | for live | |
| `X_ACCESS_TOKEN` | for live | |
| `X_ACCESS_SECRET` | for live | |
| `AA_API_KEY` | for evals | |
| `DRY_RUN` | optional | default `true` if unset. Set `false` only when ready to post. |

Local copy: `cp .env.example .env` (gitignored).

### 4. Dry-run vs live

| Mode | Behavior |
|---|---|
| `DRY_RUN=true` (default) | Render cards → `out/`, print captions, update state, **no X calls** |
| `DRY_RUN=false` | Same + post to X with media + source reply |

Workflow: every **30 minutes** + `workflow_dispatch` (`samples` / `run` / `seed`).

## Local commands

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Sample cards + captions (no secrets)
python -m src.main --samples

# Unit tests
pytest -q

# Seed current RSS/HF surface (post nothing)
python -m src.main --seed

# One cycle (respects DRY_RUN)
python -m src.main --run
```

## Post copy

Two lines. Model name in the **text**, not only on the image. No URLs. No hashtags.

**SHIPPED**

```
Claude Opus 5 just shipped.
Closed. Evals when the independent board has it.
```

**EVALS**

```
GPT-5.6 Sol: 61 on Artificial Analysis, rank 5.
Closed. One behind Opus 5 (max) at 63.
```

## Visuals

Pillow PNGs, 16:9. Same bones every time; **lab color** is the only theme change.

- **SHIPPED** — full-bleed lab color, giant model name, OPEN/CLOSED pill, black lower-third `SHIPPED · LAB · EVALTAPE`, sprocket-hole tape signature.
- **EVALS** — matte black jumbotron, enormous Intelligence Index number, RANK n, `EVALTAPE · ARTIFICIAL ANALYSIS` footer, sprocket holes.

Video: not in v1.
