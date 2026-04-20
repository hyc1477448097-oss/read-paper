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


# ---------- Domain-aware translation ----------

async def translate_text(text: str, domain: str | None = None) -> str:
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

async def answer_question(question: str, context_chunks: list[str], domain: str | None = None) -> str:
    context = "\n---\n".join(context_chunks)
    system_prompt = (
        "你是一个学术论文阅读助手。根据以下论文片段回答用户的问题。"
        "如果片段中没有足够信息，请如实告知，不要编造。"
        "回答时引用相关段落。"
    )
    if domain:
        system_prompt += f"\n本论文属于「{domain}」领域。"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"论文片段:\n{context}\n\n问题: {question}"},
    ]
    return await chat_completion(messages, temperature=0.2)


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
