"""AI feature endpoints: translate, ask, summarize, one-sentence, recommend.

All mounted under /api/papers prefix in main.py.
Ask/RAG is implemented via LangChain in ``app.services.rag_qa``.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_db
from app.db.redis import cache_get, cache_set
from app.core.config import settings
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
    ChapterSummaryRequest,
    ChapterSummaryResponse,
)
from app.services.baidu_translate import BaiduTranslateError, translate_with_baidu
from app.services.llm_service import (
    translate_text_llm,
    summarize_section,
    summarize_outline_chapter,
    one_sentence_summary,
    recommend_sections,
)
from app.services.rag_qa import ask_with_langchain

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

    selected: str | None = None
    if req.context and isinstance(req.context, dict):
        raw = req.context.get("selectedText") or req.context.get("selected_text")
        if raw:
            selected = str(raw)

    # 向量检索无命中或失败时，用前若干段落正文降级
    result = await db.execute(
        select(PaperSection)
        .where(PaperSection.paper_id == paper_id)
        .order_by(PaperSection.idx)
        .limit(3)
    )
    fallback_texts = [sec.content[:2000] for sec in result.scalars().all()]

    try:
        out = await ask_with_langchain(
            question=req.question,
            paper_id=paper_id,
            domain=paper.domain,
            selected_text=selected,
            fallback_texts=fallback_texts,
            top_k=settings.rag_top_k,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"答疑服务暂时不可用: {e}") from e

    return AskResponse(answer=out["answer"], sources=out.get("sources") or [])


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


def _section_page_span(sec: PaperSection) -> tuple[int, int] | None:
    """返回 1-based 闭区间页码；无页信息则 None。"""
    if sec.page_start is None:
        return None
    start = int(sec.page_start)
    end = int(sec.page_end) if sec.page_end is not None else start
    if end < start:
        end = start
    return start, end


def _overlaps(ps: int, pe: int, span: tuple[int, int]) -> bool:
    ss, ee = span
    return not (ee < ps or ss > pe)


@router.post("/{paper_id}/chapter-summary", response_model=ChapterSummaryResponse)
async def chapter_summary(
    paper_id: str,
    req: ChapterSummaryRequest,
    db: AsyncSession = Depends(get_db),
):
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    if req.page_end < req.page_start:
        raise HTTPException(status_code=422, detail="page_end 不能小于 page_start")

    domain = req.domain if req.domain is not None else paper.domain

    result = await db.execute(
        select(PaperSection)
        .where(PaperSection.paper_id == paper_id)
        .order_by(PaperSection.idx)
    )
    sections = result.scalars().all()

    ps, pe = req.page_start, req.page_end
    parts: list[str] = []
    for sec in sections:
        span = _section_page_span(sec)
        if span is None or not _overlaps(ps, pe, span):
            continue
        title = sec.title or "段落"
        parts.append(f"## {title}\n{sec.content}")

    context = "\n\n".join(parts)[:12000]
    if not context.strip():
        context = (
            "（当前页码范围内未匹配到解析器抽取的段落正文；可能正文未入库或与书签页码不对齐。"
            "请仅根据书签标题说明该章节通常可能包含的内容类型，并提醒用户补充解析或检查 PDF。）"
        )

    summary = await summarize_outline_chapter(req.outline_title.strip(), context, domain)
    return ChapterSummaryResponse(summary=summary, domain=domain)


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
