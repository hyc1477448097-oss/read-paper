"""Paper management endpoints."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.postgres import get_db
from app.db.milvus import insert_chunks, delete_paper_chunks
from app.models.paper import Paper, PaperSection, Reference
from app.schemas.paper import PaperOut, PaperBrief, PaperPatch, SectionOut, ReferenceOut
from app.services.pdf_parser import parse_pdf, chunk_text
from app.services.llm_service import get_embeddings

router = APIRouter()


def _sanitize(text: str | None) -> str | None:
    """移除 PostgreSQL 不支持的 NULL 字节。"""
    if text is None:
        return None
    return text.replace('\x00', '')


def _normalize_title(title: str) -> str:
    """统一大小写与空白，用于重复标题比对。"""
    return " ".join((title or "").split()).lower()


@router.post("/upload", response_model=PaperOut)
async def upload_paper(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")

    paper_id = str(uuid.uuid4())
    save_dir = settings.upload_path / paper_id
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / file.filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        parsed = parse_pdf(save_path)
    except Exception:
        shutil.rmtree(save_dir, ignore_errors=True)
        raise

    normalized = _normalize_title(parsed.title)
    if normalized:
        existing = await db.execute(
            select(Paper).where(func.lower(func.trim(Paper.title)) == normalized)
        )
        dup: Paper | None = existing.scalars().first()
        if dup is not None:
            shutil.rmtree(save_dir, ignore_errors=True)
            raise HTTPException(
                status_code=409,
                detail={
                    "message": f"已存在同名论文：{dup.title}",
                    "existing_paper_id": dup.id,
                    "title": dup.title,
                },
            )

    paper = Paper(
        id=paper_id,
        title=_sanitize(parsed.title),
        authors=_sanitize(parsed.authors),
        domain=_sanitize(parsed.keywords),
        file_path=str(save_path),
        page_count=parsed.page_count,
    )
    db.add(paper)

    for sec in parsed.sections:
        db.add(PaperSection(
            paper_id=paper_id,
            idx=sec.idx,
            title=_sanitize(sec.title),
            content=_sanitize(sec.content),
            level=sec.level,
            page_start=sec.page_start,
            page_end=sec.page_end,
        ))

    for ref in parsed.references:
        db.add(Reference(
            paper_id=paper_id,
            idx=ref.idx,
            raw_text=_sanitize(ref.raw_text),
            title=_sanitize(ref.title),
            authors=_sanitize(ref.authors),
            year=ref.year,
            venue=_sanitize(ref.venue),
        ))

    await db.commit()
    await db.refresh(paper)

    # Build vector embeddings in background-ish (inline for now)
    try:
        all_chunks = []
        for sec in parsed.sections:
            text_chunks = chunk_text(sec.content)
            for chunk in text_chunks:
                all_chunks.append({"section_idx": sec.idx, "chunk_text": chunk})
        if all_chunks:
            texts = [c["chunk_text"] for c in all_chunks]
            embeddings = await get_embeddings(texts)
            for c, emb in zip(all_chunks, embeddings):
                c["embedding"] = emb
            insert_chunks(paper_id, all_chunks)
    except Exception:
        pass  # vector indexing failure should not block upload

    return paper


@router.get("/", response_model=list[PaperBrief])
async def list_papers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Paper).order_by(Paper.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{paper_id}", response_model=PaperOut)
async def get_paper(paper_id: str, db: AsyncSession = Depends(get_db)):
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    return paper


@router.get("/{paper_id}/file")
async def get_paper_file(paper_id: str, db: AsyncSession = Depends(get_db)):
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    file_path = Path(paper.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=file_path.name,
    )


@router.get("/{paper_id}/sections", response_model=list[SectionOut])
async def get_paper_sections(paper_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PaperSection)
        .where(PaperSection.paper_id == paper_id)
        .order_by(PaperSection.idx)
    )
    sections = result.scalars().all()
    if not sections:
        paper = await db.get(Paper, paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="论文不存在")
    return sections


@router.get("/{paper_id}/references", response_model=list[ReferenceOut])
async def get_paper_references(paper_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Reference)
        .where(Reference.paper_id == paper_id)
        .order_by(Reference.idx)
    )
    refs = result.scalars().all()
    if not refs:
        paper = await db.get(Paper, paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="论文不存在")
    return refs


@router.patch("/{paper_id}", response_model=PaperOut)
async def patch_paper(paper_id: str, body: PaperPatch, db: AsyncSession = Depends(get_db)):
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(paper, field, value)
    await db.commit()
    await db.refresh(paper)
    return paper


@router.delete("/{paper_id}")
async def delete_paper(paper_id: str, db: AsyncSession = Depends(get_db)):
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    try:
        delete_paper_chunks(paper_id)
    except Exception:
        pass
    file_path = Path(paper.file_path)
    if file_path.exists():
        shutil.rmtree(file_path.parent, ignore_errors=True)
    await db.delete(paper)
    await db.commit()
    return {"detail": "已删除"}
