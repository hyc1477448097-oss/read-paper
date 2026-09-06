"""上下文答疑：LangChain LCEL + 现有 Milvus / Embedding。

检索仍走项目内 ``get_embedding`` + ``search_chunks``（章程约定的 Milvus 入口），
生成侧用 LangChain ``ChatOpenAI``（DeepSeek 兼容）与 Prompt 链，保持
``AskResponse`` 契约不变。
"""
from __future__ import annotations

from typing import Any

from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_openai import ChatOpenAI
from pydantic import Field

from app.core.config import settings
from app.db.milvus import search_chunks
from app.services.llm_service import get_embedding

_QA_SYSTEM = (
    "你是一个学术论文阅读助手。根据以下论文片段回答用户的问题。"
    "如果片段中没有足够信息，请如实告知，不要编造。"
    "回答时引用相关段落。"
    "论文所属领域：{domain}。"
)

_QA_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _QA_SYSTEM),
        ("human", "论文片段:\n{context}\n\n问题: {question}"),
    ]
)


def _chat_model() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.deepseek_llm_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.2,
        timeout=120.0,
        max_retries=1,
    )


def _format_docs(docs: list[Document]) -> str:
    if not docs:
        return "（未检索到相关片段）"
    return "\n---\n".join(d.page_content for d in docs)


def _source_previews(docs: list[Document], limit: int = 3, preview_len: int = 200) -> list[str]:
    previews: list[str] = []
    for d in docs[:limit]:
        text = (d.page_content or "").strip()
        if not text:
            continue
        previews.append(text if len(text) <= preview_len else text[:preview_len] + "...")
    return previews


class PaperMilvusRetriever(BaseRetriever):
    """按 paper_id 在 Milvus 中检索；可选插入用户选中文本；无命中时用段落降级。"""

    paper_id: str
    top_k: int = 5
    selected_text: str | None = None
    fallback_texts: list[str] = Field(default_factory=list)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        raise NotImplementedError("请使用异步接口 ainvoke / _aget_relevant_documents")

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: AsyncCallbackManagerForRetrieverRun,
    ) -> list[Document]:
        docs: list[Document] = []

        selected = (self.selected_text or "").strip()
        if selected:
            docs.append(
                Document(
                    page_content=selected,
                    metadata={"source": "selection", "paper_id": self.paper_id},
                )
            )

        try:
            q_emb = await get_embedding(query)
            hits = search_chunks(q_emb, paper_id=self.paper_id, top_k=self.top_k)
            for h in hits:
                text = (h.get("chunk_text") or "").strip()
                if not text:
                    continue
                docs.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": "milvus",
                            "paper_id": h.get("paper_id") or self.paper_id,
                            "section_idx": h.get("section_idx"),
                            "score": h.get("score"),
                        },
                    )
                )
        except Exception:
            # 向量检索失败时保留选中文本 / 走段落降级
            pass

        if not docs:
            for text in self.fallback_texts:
                t = (text or "").strip()
                if not t:
                    continue
                docs.append(
                    Document(
                        page_content=t,
                        metadata={"source": "fallback", "paper_id": self.paper_id},
                    )
                )

        return docs


async def ask_with_langchain(
    *,
    question: str,
    paper_id: str,
    domain: str | None = None,
    selected_text: str | None = None,
    fallback_texts: list[str] | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """执行上下文答疑，返回 ``{"answer": str, "sources": list[str]}``。"""
    q = (question or "").strip()
    if not q:
        return {"answer": "请输入有效问题。", "sources": []}

    retriever = PaperMilvusRetriever(
        paper_id=paper_id,
        top_k=top_k,
        selected_text=selected_text,
        fallback_texts=list(fallback_texts or []),
    )
    docs = await retriever.ainvoke(q)
    answer = await answer_from_chunks(q, [d.page_content for d in docs], domain)
    return {
        "answer": answer,
        "sources": _source_previews(docs),
    }


async def answer_from_chunks(
    question: str,
    context_chunks: list[str],
    domain: str | None = None,
) -> str:
    """仅生成：已有上下文片段时走同一套 LangChain Prompt + ChatOpenAI。"""
    docs = [
        Document(page_content=c)
        for c in context_chunks
        if (c or "").strip()
    ]
    chain = _QA_PROMPT | _chat_model() | StrOutputParser()
    answer = await chain.ainvoke(
        {
            "context": _format_docs(docs),
            "question": (question or "").strip(),
            "domain": domain or "通用",
        }
    )
    return (answer or "").strip()
