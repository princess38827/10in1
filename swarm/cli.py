"""Command-line interface for the research swarm.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python -m swarm.cli run "the future of humanoid robotics"
    python -m swarm.cli history
    python -m swarm.cli show <run_id>
"""
from __future__ import annotations

import asyncio
import sys

from .orchestrator import ResearchSwarm
from .storage import Storage


def _print_progress(stage: str, detail: str) -> None:
    icons = {
        "overseer": "🧭",
        "overseer_done": "✅",
        "worker_start": "🔎",
        "worker_done": "📥",
        "synthesizer": "🧩",
        "done": "🏁",
    }
    print(f"{icons.get(stage, '•')} [{stage}] {detail}")


async def cmd_run(topic: str) -> None:
    swarm = ResearchSwarm()
    try:
        run = await swarm.run(topic, on_progress=_print_progress)
    finally:
        await swarm.aclose()

    s = run.synthesis
    print("\n" + "=" * 70)
    print(f"RUN {run.run_id}  ({run.total_elapsed_s:.1f}s, {len(run.findings)} agents)")
    print("=" * 70)
    print(f"\nTOPIC: {run.topic}\n")
    print("EXECUTIVE SUMMARY\n" + "-" * 17)
    print(s.executive_summary)
    if s.themes:
        print("\nTHEMES\n" + "-" * 6)
        for t in s.themes:
            print(f"  - {t}")
    if s.contradictions:
        print("\nCONTRADICTIONS BETWEEN AGENTS\n" + "-" * 29)
        for c in s.contradictions:
            print(f"  - {c}")
    if s.gaps:
        print("\nCOVERAGE GAPS\n" + "-" * 13)
        for g in s.gaps:
            print(f"  - {g}")
    print("\nFULL REPORT\n" + "-" * 11)
    print(s.full_report)
    print(f"\nSaved. Retrieve later with: python -m swarm.cli show {run.run_id}")


def cmd_history() -> None:
    storage = Storage()
    runs = storage.list_runs()
    storage.close()
    if not runs:
        print("No runs yet.")
        return
    for r in runs:
        print(f"{r['run_id']}  {r['topic'][:60]:<60}  {r['total_elapsed_s']:.1f}s")


def cmd_show(run_id: str) -> None:
    storage = Storage()
    run = storage.get(run_id)
    storage.close()
    if not run:
        print(f"No run found with id {run_id}")
        return
    print(f"TOPIC: {run.topic}\n")
    print(run.synthesis.full_report if run.synthesis else "[no synthesis]")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd, *rest = sys.argv[1:]
    if cmd == "run":
        if not rest:
            print('Usage: python -m swarm.cli run "your topic here"')
            sys.exit(1)
        asyncio.run(cmd_run(" ".join(rest)))
    elif cmd == "history":
        cmd_history()
    elif cmd == "show":
        if not rest:
            print("Usage: python -m swarm.cli show <run_id>")
            sys.exit(1)
        cmd_show(rest[0])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
