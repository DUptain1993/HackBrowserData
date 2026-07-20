# telegram-bot-builder

Point it at a GitHub repository. It clones the repo, analyzes the codebase to
understand what the project actually does, works out how to reproduce that logic,
and generates a runnable **Telegram bot** that exposes the project's functionality
as bot commands.

It is **repo-agnostic** — a general-purpose "codebase → Telegram bot" generator,
not tied to any particular project.

```
┌────────────┐   ┌──────────┐   ┌───────────┐   ┌────────┐   ┌───────────┐
│ GitHub URL │──▶│  digest  │──▶│  analyze  │──▶│ safety │──▶│ generate  │
│ / local    │   │ (files,  │   │ (Claude:  │   │ guard  │   │ bot.py +  │
│  path      │   │ README,  │   │ purpose,  │   │        │   │ project   │
│            │   │ entry-   │   │ strategy, │   │        │   │ files)    │
│            │   │ points)  │   │ commands) │   │        │   │           │
└────────────┘   └──────────┘   └───────────┘   └────────┘   └───────────┘
```

## How it works

1. **Digest** (`repo.py`) — shallow-clones the repo and builds a token-bounded
   snapshot: file tree, detected languages, README, manifests, and entry-point source.
2. **Analyze** (`analyzer.py`) — sends the digest to Claude, which returns a structured
   analysis: the project's purpose, its real capabilities, an *integration strategy*, and
   a set of proposed bot commands mapped onto actual functionality.
   - `cli_wrap` — the repo is a CLI; the bot invokes it as a subprocess.
   - `reimplement` — the core logic is small and pure; it's ported into the bot.
   - `api_wrap` — the repo is a library; the bot imports and calls it.
3. **Safety** (`safety.py`) — see below.
4. **Generate** (`generator.py`) — Claude writes `bot.py` (python-telegram-bot, async)
   implementing each command per the chosen strategy, plus `requirements.txt`,
   `.env.example`, `README.md`, and a `Dockerfile`.

## Usage

```bash
pip install -r requirements.txt          # for LLM mode; optional
export ANTHROPIC_API_KEY=sk-ant-...       # or run offline (see below)

# Inspect the analysis without generating anything:
python -m botbuilder analyze owner/repo

# Build a bot:
python -m botbuilder build https://github.com/owner/repo --out ./my-bot

# Then:
cd my-bot
cp .env.example .env        # set BOT_TOKEN from @BotFather
pip install -r requirements.txt
python bot.py
```

`source` accepts a full GitHub URL, the `owner/repo` shorthand, or a local path.

### Offline (heuristic) mode

Without the `anthropic` package or an API key, the tool automatically falls back to a
static-analysis mode. It still detects the language and entry point and generates a
working CLI-wrapper bot scaffold — just without the deep, logic-aware command design.
Force it with `--llm off`; require the LLM with `--llm on`.

## Safety guardrail

A Telegram bot is a remote channel that ships whatever it produces to a chat. Wrapping a
tool that **extracts local credentials or secrets** (browser passwords/cookies/cards,
wallet keys, etc.) in such a bot produces the exfiltration stage of an infostealer.

`safety.py` scans the repo and the analysis for that signature and **blocks generation**
when harvesting-and-exfiltrating secrets is the target repo's clear purpose. Repos that
merely *touch* secrets (a password manager, an auth library) generate with a warning. This
is a deliberate, documented limit on what the general tool will build — keep it in place.

## Development

```bash
pip install pytest
PYTHONPATH=. pytest tests -q
```

`tests/test_pipeline.py` runs the full offline pipeline against `examples/hello-cli`;
`tests/test_safety.py` covers the guardrail.

---

_Scaffolds are a starting point — review generated code before deploying it, and only run
bots against systems and accounts you are authorized to operate._
