"""Orchestrates the full 10-agent run: 1 overseer -> 9 parallel workers -> 1 synthesizer."""
from __future__ import annotations

import asyncio
import time

from .agents import Overseer, Synthesizer, Worker
from .llm_client import LLMClient
from .models import SwarmRun
from .storage import Storage


class ResearchSwarm:
    def __init__(self, llm: LLMClient | None = None, storage: Storage | None = None):
        self.llm = llm or LLMClient()
        self.storage = storage or Storage()
        self.overseer = Overseer(self.llm)
        self.synthesizer = Synthesizer(self.llm)

    async def run(self, topic: str, on_progress=None) -> SwarmRun:
        """on_progress(stage: str, detail: str) is called for lightweight status updates."""
        start = time.monotonic()

        def emit(stage: str, detail: str = ""):
            if on_progress:
                on_progress(stage, detail)

        emit("overseer", f"Decomposing: {topic}")
        subtopics = await self.overseer.decompose(topic)
        emit("overseer_done", f"{len(subtopics)} subtopics assigned")

        workers = [Worker(self.llm) for _ in subtopics]

        async def run_worker(worker: Worker, subtopic):
            emit("worker_start", subtopic.title)
            finding = await worker.research(topic, subtopic)
            status = "ok" if not finding.error else f"error: {finding.error}"
            emit("worker_done", f"{subtopic.title} ({status})")
            return finding

        findings = await asyncio.gather(
            *(run_worker(w, s) for w, s in zip(workers, subtopics))
        )

        emit("synthesizer", "Merging findings into final report")
        run = SwarmRun(topic=topic, subtopics=subtopics, findings=list(findings))
        synthesis = await self.synthesizer.synthesize(run.run_id, topic, run.findings)
        run.synthesis = synthesis
        run.total_elapsed_s = time.monotonic() - start
        emit("done", f"Completed in {run.total_elapsed_s:.1f}s")

        self.storage.save(run)
        return run

    async def aclose(self) -> None:
        await self.llm.aclose()
        self.storage.close()
