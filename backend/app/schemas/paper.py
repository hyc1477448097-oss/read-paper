from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


# ---------- Paper ----------

class PaperCreate(BaseModel):
    title: str
    domain: str | None = None


class PaperPatch(BaseModel):
    domain: str | None = None


class PaperOut(BaseModel):
    id: str
    title: str
    authors: str | None = None
    domain: str | None = None
    page_count: int = 0
    one_sentence_summary: str | None = None
    innovation_points: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaperBrief(BaseModel):
    id: str
    title: str
    domain: str | None = None
    page_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Section ----------

class SectionOut(BaseModel):
    id: str
    idx: int
    title: str | None = None
    content: str
    level: int = 1
    page_start: int | None = None
    page_end: int | None = None
    category: str | None = None
    summary: str | None = None

    model_config = {"from_attributes": True}


# ---------- Reference ----------

class ReferenceOut(BaseModel):
    id: str
    idx: int
    raw_text: str
    title: str | None = None
    authors: str | None = None
    year: int | None = None
    venue: str | None = None
    venue_type: str | None = None
    venue_level: str | None = None

    model_config = {"from_attributes": True}


class ReferenceAnalysis(BaseModel):
    total: int = 0
    recent_3yr_count: int = 0
    recent_3yr_ratio: float = 0.0
    recent_10yr_count: int = 0
    recent_10yr_ratio: float = 0.0
    venue_distribution: dict[str, int] = Field(default_factory=dict)
    level_distribution: dict[str, int] = Field(default_factory=dict)
    references: list[ReferenceOut] = Field(default_factory=list)


# ---------- AI ----------

class TranslateRequest(BaseModel):
    text: str
    page_number: int | None = None
    domain: str | None = None


class TranslateResponse(BaseModel):
    translated: str
    domain: str | None = None


class AskRequest(BaseModel):
    question: str
    context: dict | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)


class SummarizeResponse(BaseModel):
    sections: list[SectionOut]
    one_sentence: str | None = None
    innovation_points: str | None = None


class RecommendRequest(BaseModel):
    purpose: str = "innovation"


class RecommendResponse(BaseModel):
    sections: list[SectionOut] = Field(default_factory=list)
    reason: str | None = None


class RelevanceRequest(BaseModel):
    research_direction: str
    keywords: list[str] = Field(default_factory=list)


class RelevanceResponse(BaseModel):
    score: float = 0.0
    explanation: str = ""
    key_overlaps: list[str] = Field(default_factory=list)
