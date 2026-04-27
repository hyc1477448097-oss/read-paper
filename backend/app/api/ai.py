"""AI feature endpoints: translate, ask, summarize, one-sentence, recommend.

All mounted under /api/papers prefix in main.py.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_db
from app.db.milvus import search_chunks
from app.db.redis import cache_get, cache_set
from app.models.paper import Paper, PaperSection
from app.schemas.paper import (
    TranslateRequest,
    TranslateResponse,
    AskRequest,
    AskResponse,
    SummarizeResponse,
    SectionOut,
    RecommendRequest,
    RecommendResponse,
)
from app.services.baidu_translate import BaiduTranslateError, translate_with_baidu
from app.services.llm_service import (
    translate_text_llm,
    answer_question,
    summarize_section,
    one_sentence_summary,
    recommend_sections,
    get_embedding,
)

router = APIRouter()


@router.post("/{paper_id}/translate", response_model=TranslateResponse)
async def translate(paper_id: str, req: TranslateRequest, db: AsyncSession = Depends(get_db)):
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    domain = req.domain or paper.domain
    engine = req.engine

    cache_key = f"translate:{paper_id}:{engine}:{hash(req.text + (domain or ''))}"
    cached = await cache_get(cache_key)
    if cached:
        return TranslateResponse(translated=cached["translated"], domain=domain)

    if engine == "llm":
        translated = await translate_text_llm(req.text, domain)
    else:
        try:
            translated = await translate_with_baidu(req.text)
        except BaiduTranslateError as e:
            raise HTTPException(status_code=502, detail=str(e)) from e
    await cache_set(cache_key, {"translated": translated}, ttl=7200)
    return TranslateResponse(translated=translated, domain=domain)


@router.post("/{paper_id}/ask", response_model=AskResponse)
async def ask(paper_id: str, req: AskRequest, db: AsyncSession = Depends(get_db)):
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")

    context_chunks: list[str] = []
    try:
        q_emb = await get_embedding(req.question)
        hits = search_chunks(q_emb, paper_id=paper_id, top_k=5)
        context_chunks = [h["chunk_text"] for h in hits]
    except Exception:
        pass

    if req.context and isinstance(req.context, dict):
        selected = req.context.get("selectedText") or req.context.get("selected_text")
        if selected:
            context_chunks.insert(0, str(selected))

    if not context_chunks:
        result = await db.execute(
            select(PaperSection)
            .where(PaperSection.paper_id == paper_id)
            .order_by(PaperSection.idx)
            .limit(3)
        )
        for sec in result.scalars().all():
            context_chunks.append(sec.content[:2000])

    answer = await answer_question(req.question, context_chunks, paper.domain)
    sources = [c[:200] + "..." for c in context_chunks[:3]]
    return AskResponse(answer=answer, sources=sources)


@router.post("/{paper_id}/summarize", response_model=SummarizeResponse)
async def summarize(paper_id: str, db: AsyncSession = Depends(get_db)):
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")

    cache_key = f"summarize:{paper_id}"
    cached = await cache_get(cache_key)
    if cached:
        return SummarizeResponse(**cached)

    result = await db.execute(
        select(PaperSection)
        .where(PaperSection.paper_id == paper_id)
        .order_by(PaperSection.idx)
    )
    sections = result.scalars().all()

    for sec in sections:
        if not sec.summary:
            analysis = await summarize_section(sec.content, paper.domain)
            sec.summary = analysis.get("summary", "")
            sec.category = analysis.get("category", "")
    await db.commit()

    full_text = "\n".join(sec.content[:500] for sec in sections)
    overall = await one_sentence_summary(full_text)
    paper.one_sentence_summary = overall.get("one_sentence", "")
    paper.innovation_points = overall.get("innovation_points", "")
    await db.commit()

    section_outs = [SectionOut.model_validate(s) for s in sections]
    resp_data = {
        "sections": [s.model_dump() for s in section_outs],
        "one_sentence": paper.one_sentence_summary,
        "innovation_points": paper.innovation_points,
    }
    await cache_set(cache_key, resp_data, ttl=3600)

    return SummarizeResponse(
        sections=section_outs,
        one_sentence=paper.one_sentence_summary,
        innovation_points=paper.innovation_points,
    )


@router.get("/{paper_id}/one-sentence")
async def get_one_sentence(paper_id: str, db: AsyncSession = Depends(get_db)):
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")

    if paper.one_sentence_summary:
        return {
            "one_sentence": paper.one_sentence_summary,
            "innovation_points": paper.innovation_points or "",
        }

    result = await db.execute(
        select(PaperSection)
        .where(PaperSection.paper_id == paper_id)
        .order_by(PaperSection.idx)
    )
    sections = result.scalars().all()
    full_text = "\n".join(sec.content[:500] for sec in sections)
    overall = await one_sentence_summary(full_text)
    paper.one_sentence_summary = overall.get("one_sentence", "")
    paper.innovation_points = overall.get("innovation_points", "")
    await db.commit()

    return {
        "one_sentence": paper.one_sentence_summary,
        "innovation_points": paper.innovation_points,
    }


@router.post("/{paper_id}/recommend", response_model=RecommendResponse)
async def recommend(paper_id: str, req: RecommendRequest, db: AsyncSession = Depends(get_db)):
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")

    result = await db.execute(
        select(PaperSection)
        .where(PaperSection.paper_id == paper_id)
        .order_by(PaperSection.idx)
    )
    sections = result.scalars().all()
    sections_info = [
        {"idx": s.idx, "title": s.title or "", "summary": s.summary or s.content[:200]}
        for s in sections
    ]

    rec = await recommend_sections(sections_info, req.purpose)
    indices = rec.get("recommended_indices", [])
    recommended = [
        SectionOut.model_validate(s) for s in sections if s.idx in indices
    ]
    return RecommendResponse(sections=recommended, reason=rec.get("reason", ""))
