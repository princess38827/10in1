
# Research Swarm — 10-Agent Parallel Research System

A 10-agent swarm for deep, multi-angle research on any topic:

1. **Overseer** (1 agent) — breaks your topic into 9 distinct subtopics
2. **Workers** (9 agents) — research their assigned subtopic in parallel (async)
3. **Synthesizer** (1 agent) — merges all 9 findings into one report, surfacing
   themes, contradictions between agents, and real coverage gaps

Every run is persisted to a local SQLite database (`~/.research_swarm/runs.db`)
so you can pull up past investigations later.

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

```bash
python -m swarm.cli run "the future of humanoid robotics"
python -m swarm.cli history
python -m swarm.cli show <run_id>
```

## Architecture notes

- All 9 worker agents run concurrently via `asyncio.gather`, capped at 6
  simultaneous in-flight API calls (semaphore in `llm_client.py`) to stay
  well under rate limits.
- Each agent's system prompt forces strict JSON output so results compose
  cleanly without brittle text parsing.
- Retries with exponential backoff on 429/5xx responses.
- Swap `SWARM_MODEL` env var to change the model (defaults to `claude-sonnet-5`).

## Extending

- Point `Worker.research()` at a real web-search tool instead of relying on
  the model's own knowledge, for up-to-date findings.
- Add a `critic` agent between workers and synthesizer that scores each
  finding's confidence independently.
- Swap `Storage` for Postgres if you want multi-user history.

