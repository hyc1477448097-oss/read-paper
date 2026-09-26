"""LLM & Embedding service using DeepSeek API via OpenAI-compatible client."""
from __future__ import annotations

import httpx
from openai import AsyncOpenAI

from app.core.config import settings

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            http_client=httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=10.0),
            ),
        )
    return _client


async def chat_completion(
    messages: list[dict[str, str]],
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> str:
    client = _get_client()
    resp = await client.chat.completions.create(
        model=settings.deepseek_llm_model,
        messages=messages,  # type: ignore[arg-type]
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    client = _get_client()
    resp = await client.embeddings.create(
        model=settings.deepseek_embed_model,
        input=texts,
    )
    return [item.embedding for item in resp.data]


async def get_embedding(text: str) -> list[float]:
    result = await get_embeddings([text])
    return result[0]


# ---------- Domain-aware translation (LLM, for intelligent / sidebar translate) ----------

async def translate_text_llm(text: str, domain: str | None = None) -> str:
    system_prompt = (
        "你是一个专业的学术论文翻译助手。请将以下英文学术文本翻译为中文，"
        "保留专业术语的准确性，必要时在中文翻译后用括号标注英文原文。"
    )
    if domain:
        system_prompt += f"\n本论文属于「{domain}」领域，请使用该领域的专业术语进行翻译。"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text},
    ]
    return await chat_completion(messages, temperature=0.1)


# ---------- Context-aware Q&A ----------
# 完整 RAG（Milvus 检索 + LangChain 生成）见 app.services.rag_qa.ask_with_langchain。
# 下列函数保留给「已拿到片段、只需生成」的场景，实现同样走 LangChain Prompt 链。

async def answer_question(question: str, context_chunks: list[str], domain: str | None = None) -> str:
    from app.services.rag_qa import answer_from_chunks

    return await answer_from_chunks(question, context_chunks, domain)


# ---------- Summarize ----------

async def summarize_section(content: str, domain: str | None = None) -> dict:
    system_prompt = (
        "你是学术论文分析助手。请对以下论文段落进行分析，返回JSON格式:\n"
        '{"summary": "一句话总结", "category": "科普|方法论|创新点|背景|实验|结论"}'
    )
    if domain:
        system_prompt += f"\n本论文属于「{domain}」领域。"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content[:3000]},
    ]
    import json
    raw = await chat_completion(messages, temperature=0.1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"summary": raw, "category": "未知"}


async def summarize_outline_chapter(
    outline_title: str,
    context_text: str,
    domain: str | None = None,
) -> str:
    """根据书签标题 + 解析正文摘录生成中文章节总结（非 JSON）。"""
    system_prompt = (
        "你是该领域的学术研究者，正在精读一篇论文中的某一章节摘录。"
        "用户给出 PDF 书签标题与解析器抽出的正文；页码与书签可能不完全对齐，请据实理解，勿编造摘录中没有的信息。"
        "请深刻把握：本章在讲什么、为何在全文中出现于此、对前后论证起什么作用；用研究者视角写出真正有区分度的理解，而不是可套用到任意章节的空话。"
        "输出结构（中文，不要 JSON 或 Markdown 代码块）：\n"
        "1）先用一小段（约 2～4 句）给出总判断：本章主旨 + 它在全文中的角色/作用；\n"
        "2）再分条列出本章重点，仅 1～3 条，每条一句、尽量具体（专有名词、机制、设定、结果等）；重点不足三条就少写，不要凑数。\n"
        "全文宜精炼，总长约 ≤220 个汉字。"
    )
    if domain:
        system_prompt += (
            f"\n论文所属领域为「{domain}」。请以该领域研究者的惯用概念与术语来理解与表述，"
            "抓住对本领域读者真正重要的信息。"
        )
    user_block = f"书签章节标题：{outline_title}\n\n--- 正文摘录 ---\n{context_text[:10000]}"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_block},
    ]
    return await chat_completion(messages, temperature=0.2, max_tokens=400)


async def one_sentence_summary(full_text: str) -> dict:
    messages = [
        {
            "role": "system",
            "content": (
                "你是学术论文分析助手。请对以下论文进行分析，返回JSON格式:\n"
                '{"one_sentence": "一句话总结全文", "innovation_points": "创新点1; 创新点2; ..."}'
            ),
        },
        {"role": "user", "content": full_text[:6000]},
    ]
    import json
    raw = await chat_completion(messages, temperature=0.1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"one_sentence": raw, "innovation_points": ""}


# ---------- Reading recommendation ----------

async def recommend_sections(sections_info: list[dict], purpose: str) -> dict:
    """Recommend which sections to read based on user purpose."""
    purpose_map = {
        "innovation": "寻找创新点灵感",
        "background": "了解研究背景",
        "writing": "学习写作方法",
        "preprocessing": "学习预处理方法",
        "visualization": "学习画图技巧",
        "conclusion": "了解总结展望",
    }
    purpose_text = purpose_map.get(purpose, purpose)
    sections_text = "\n".join(
        f"[{s['idx']}] {s['title']}: {s.get('summary', '')[:100]}" for s in sections_info
    )
    messages = [
        {
            "role": "system",
            "content": (
                f"用户的阅读目的是「{purpose_text}」。\n"
                "请从以下章节中推荐最相关的章节，返回JSON格式:\n"
                '{"recommended_indices": [0, 2, 5], "reason": "推荐理由"}'
            ),
        },
        {"role": "user", "content": sections_text},
    ]
    import json
    raw = await chat_completion(messages, temperature=0.2)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"recommended_indices": [], "reason": raw}


# ---------- Reference analysis ----------

async def analyze_references(refs_text: str) -> list[dict]:
    """Use LLM to parse structured reference info from raw text."""
    messages = [
        {
            "role": "system",
            "content": (
                "请解析以下参考文献列表，对每条返回JSON数组，每个元素包含:\n"
                '{"idx": 数字, "title": "标题", "authors": "作者", "year": 年份数字, '
                '"venue": "期刊/会议名", "venue_type": "journal|conference|preprint|book|other", '
                '"venue_level": "CCF-A|CCF-B|CCF-C|SCI-Q1|SCI-Q2|SCI-Q3|SCI-Q4|EI|other|unknown"}\n'
                "仅返回JSON数组，不要其他文字。"
            ),
        },
        {"role": "user", "content": refs_text[:8000]},
    ]
    import json
    raw = await chat_completion(messages, temperature=0.0, max_tokens=8192)
    try:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
    except json.JSONDecodeError:
        pass
    return []


# ---------- Relevance analysis ----------

async def analyze_relevance(paper_summary: str, direction: str, keywords: list[str]) -> dict:
    kw_text = "、".join(keywords) if keywords else "无"
    messages = [
        {
            "role": "system",
            "content": (
                "你是学术研究方向匹配分析助手。请分析论文与读者研究方向的契合度，返回JSON:\n"
                '{"score": 0-100数字, "explanation": "详细分析", '
                '"key_overlaps": ["重叠关键点1", "重叠关键点2"]}'
            ),
        },
        {
            "role": "user",
            "content": (
                f"论文摘要:\n{paper_summary[:3000]}\n\n"
                f"读者研究方向: {direction}\n"
                f"读者关键词: {kw_text}"
            ),
        },
    ]
    import json
    raw = await chat_completion(messages, temperature=0.1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"score": 0, "explanation": raw, "key_overlaps": []}
