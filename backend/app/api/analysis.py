"""Analysis endpoints: reference analysis, relevance analysis.

All mounted under /api/papers prefix in main.py.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_db
from app.db.redis import cache_get, cache_set
from app.models.paper import Paper, PaperSection, Reference
from app.schemas.paper import (
    ReferenceAnalysis,
    ReferenceOut,
    RelevanceRequest,
    RelevanceResponse,
)
from app.services.llm_service import analyze_references, analyze_relevance

router = APIRouter()

CURRENT_YEAR = datetime.now().year


@router.get("/{paper_id}/references", response_model=ReferenceAnalysis)
async def reference_analysis(paper_id: str, db: AsyncSession = Depends(get_db)):
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")

    cache_key = f"ref_analysis:{paper_id}"
    cached = await cache_get(cache_key)
    if cached:
        return ReferenceAnalysis(**cached)

    result = await db.execute(
        select(Reference)
        .where(Reference.paper_id == paper_id)
        .order_by(Reference.idx)
    )
    refs = result.scalars().all()

    needs_llm = any(r.venue_type is None for r in refs)
    if needs_llm and refs:
        raw_texts = "\n".join(f"[{r.idx}] {r.raw_text}" for r in refs)
        parsed_list = await analyze_references(raw_texts)
        ref_map = {p.get("idx"): p for p in parsed_list}
        for r in refs:
            info = ref_map.get(r.idx)
            if info:
                r.title = info.get("title") or r.title
                r.authors = info.get("authors") or r.authors
                r.year = info.get("year") or r.year
                r.venue = info.get("venue") or r.venue
                r.venue_type = info.get("venue_type") or r.venue_type
                r.venue_level = info.get("venue_level") or r.venue_level
        await db.commit()

    total = len(refs)
    recent_3 = sum(1 for r in refs if r.year and r.year >= CURRENT_YEAR - 3)
    recent_10 = sum(1 for r in refs if r.year and r.year >= CURRENT_YEAR - 10)

    venue_dist: dict[str, int] = {}
    level_dist: dict[str, int] = {}
    for r in refs:
        vt = r.venue_type or "unknown"
        venue_dist[vt] = venue_dist.get(vt, 0) + 1
        vl = r.venue_level or "unknown"
        level_dist[vl] = level_dist.get(vl, 0) + 1

    ref_outs = [ReferenceOut.model_validate(r) for r in refs]
    analysis = ReferenceAnalysis(
        total=total,
        recent_3yr_count=recent_3,
        recent_3yr_ratio=recent_3 / total if total else 0,
        recent_10yr_count=recent_10,
        recent_10yr_ratio=recent_10 / total if total else 0,
        venue_distribution=venue_dist,
        level_distribution=level_dist,
        references=ref_outs,
    )
    await cache_set(cache_key, analysis.model_dump(), ttl=3600)
    return analysis


@router.post("/{paper_id}/relevance", response_model=RelevanceResponse)
async def relevance_analysis(paper_id: str, req: RelevanceRequest, db: AsyncSession = Depends(get_db)):
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")

    cache_key = f"relevance:{paper_id}:{hash(req.research_direction + ''.join(req.keywords))}"
    cached = await cache_get(cache_key)
    if cached:
        return RelevanceResponse(**cached)

    summary_parts = [paper.one_sentence_summary or ""]
    result = await db.execute(
        select(PaperSection)
        .where(PaperSection.paper_id == paper_id)
        .order_by(PaperSection.idx)
        .limit(5)
    )
    for sec in result.scalars().all():
        summary_parts.append(sec.content[:500])
    paper_summary = "\n".join(summary_parts)

    analysis = await analyze_relevance(paper_summary, req.research_direction, req.keywords)
    resp = RelevanceResponse(
        score=float(analysis.get("score", 0)),
        explanation=analysis.get("explanation", ""),
        key_overlaps=analysis.get("key_overlaps", []),
    )
    await cache_set(cache_key, resp.model_dump(), ttl=1800)
    return resp
