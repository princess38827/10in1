"""The three agent roles in the swarm.

Overseer   -- decomposes a topic into 9 non-overlapping subtopics
Worker     -- researches one subtopic (there are 9 of these, run in parallel)
Synthesizer-- the 10th agent; merges all 9 findings into one report
"""
from __future__ import annotations

import time

from .llm_client import LLMClient
from .models import Finding, SubTopic, SynthesisResult

NUM_WORKERS = 9


class Overseer:
    """Agent 1 of 10: plans the investigation."""

    SYSTEM = (
        "You are the overseer of a research swarm. Given a broad topic, break it "
        "into exactly {n} distinct, non-overlapping subtopics that together give "
        "thorough coverage of the topic from different angles (e.g. history, "
        "mechanisms, current state, controversies, stakeholders, future outlook, "
        "comparisons, risks, practical implications -- adapt angles to fit the "
        "actual topic). Respond ONLY with a JSON array of exactly {n} objects, "
        'each shaped like: {{"title": "short title", "question": "the specific '
        'research question this subtopic should answer", "rationale": "why this '
        'angle matters"}}. No prose, no markdown fences, just the JSON array.'
    )

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def decompose(self, topic: str) -> list[SubTopic]:
        system = self.SYSTEM.format(n=NUM_WORKERS)
        raw = await self.llm.complete_json(
            system=system,
            user=f"Topic: {topic}",
            max_tokens=1200,
            temperature=0.5,
        )
        if not isinstance(raw, list):
            raise ValueError("Overseer did not return a JSON array")
        subtopics = []
        for i, item in enumerate(raw[:NUM_WORKERS]):
            subtopics.append(
                SubTopic(
                    index=i,
                    title=item.get("title", f"Subtopic {i+1}"),
                    question=item.get("question", topic),
                    rationale=item.get("rationale", ""),
                )
            )
        return subtopics


class Worker:
    """Agents 2-10 of 10: nine parallel researchers, one per subtopic."""

    SYSTEM = (
        "You are a focused research agent. You have been assigned exactly one "
        "subtopic within a larger investigation. Research it thoroughly using "
        "your own knowledge -- be specific, concrete, and honest about uncertainty. "
        'Respond ONLY with JSON shaped like: {"summary": "2-4 sentence summary", '
        '"key_points": ["point 1", "point 2", ...], "confidence": 0.0-1.0, '
        '"open_questions": ["unresolved question 1", ...]}. No prose outside the JSON.'
    )

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def research(self, topic: str, subtopic: SubTopic) -> Finding:
        start = time.monotonic()
        user = (
            f"Overall investigation topic: {topic}\n\n"
            f"Your assigned subtopic: {subtopic.title}\n"
            f"Your research question: {subtopic.question}\n"
            f"Why this angle matters: {subtopic.rationale}"
        )
        try:
            raw = await self.llm.complete_json(
                system=self.SYSTEM, user=user, max_tokens=900, temperature=0.4
            )
            return Finding(
                subtopic_id=subtopic.id,
                subtopic_title=subtopic.title,
                summary=raw.get("summary", ""),
                key_points=raw.get("key_points", []),
                confidence=float(raw.get("confidence", 0.6)),
                open_questions=raw.get("open_questions", []),
                elapsed_s=time.monotonic() - start,
            )
        except Exception as e:  # noqa: BLE001
            return Finding(
                subtopic_id=subtopic.id,
                subtopic_title=subtopic.title,
                summary="",
                error=str(e),
                elapsed_s=time.monotonic() - start,
            )


class Synthesizer:
    """Agent 10 of 10: merges all findings into one coherent report."""

    SYSTEM = (
        "You are the synthesis agent for a research swarm. You will receive the "
        "findings from 9 parallel research agents, each covering one subtopic of "
        "a broader investigation. Merge them into one coherent report: resolve "
        "overlaps, surface contradictions between agents, note real gaps in "
        "coverage, and write a genuinely useful executive summary -- not just a "
        "restatement of each finding in order. Respond ONLY with JSON shaped like: "
        '{"executive_summary": "3-5 sentences", "themes": ["theme 1", ...], '
        '"contradictions": ["contradiction 1", ...], "gaps": ["gap 1", ...], '
        '"full_report": "a well-organized multi-paragraph report in markdown"}.'
    )

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def synthesize(self, run_id: str, topic: str, findings: list[Finding]) -> SynthesisResult:
        findings_blob = "\n\n".join(
            f"### {f.subtopic_title}\n"
            f"Summary: {f.summary or '[ERROR: ' + (f.error or 'no data') + ']'}\n"
            f"Key points: {'; '.join(f.key_points)}\n"
            f"Confidence: {f.confidence}\n"
            f"Open questions: {'; '.join(f.open_questions)}"
            for f in findings
        )
        user = f"Investigation topic: {topic}\n\nFindings from 9 agents:\n\n{findings_blob}"
        raw = await self.llm.complete_json(
            system=self.SYSTEM, user=user, max_tokens=2500, temperature=0.4
        )
        return SynthesisResult(
            run_id=run_id,
            topic=topic,
            executive_summary=raw.get("executive_summary", ""),
            themes=raw.get("themes", []),
            contradictions=raw.get("contradictions", []),
            gaps=raw.get("gaps", []),
            full_report=raw.get("full_report", ""),
        )
