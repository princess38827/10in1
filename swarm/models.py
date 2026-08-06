"""Pydantic data models shared across the swarm."""
from __future__ import annotations

import time
import uuid
from typing import List, Optional

from pydantic import BaseModel, Field


def _new_id() -> str:
    return str(uuid.uuid4())


class SubTopic(BaseModel):
    id: str = Field(default_factory=_new_id)
    index: int
    title: str
    question: str
    rationale: str = ""


class Finding(BaseModel):
    subtopic_id: str
    subtopic_title: str
    summary: str = ""
    key_points: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    open_questions: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    elapsed_s: float = 0.0


class SynthesisResult(BaseModel):
    executive_summary: str = ""
    themes: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    full_report: str = ""


class SwarmRun(BaseModel):
    run_id: str = Field(default_factory=_new_id)
    topic: str
    created_at: float = Field(default_factory=time.time)
    total_elapsed_s: float = 0.0
    subtopics: List[SubTopic] = Field(default_factory=list)
    findings: List[Finding] = Field(default_factory=list)
    synthesis: Optional[SynthesisResult] = None
