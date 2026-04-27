"""Baidu general translation API (HTTPS, form-urlencoded)."""
from __future__ import annotations

import asyncio
import hashlib
import random
import time
from typing import Any

import httpx

from app.core.config import settings

# Process-wide spacing: free-tier Baidu often allows ~1 QPS (error 54003 otherwise).
_baidu_request_lock = asyncio.Lock()
_last_baidu_request_end: float = 0.0

# Baidu recommends keeping single request under ~2000 chars for quality/latency.
_CHUNK_CHAR_LIMIT = 2000


class BaiduTranslateError(Exception):
    """Raised when Baidu translate API returns an error or an unusable response."""

    def __init__(self, message: str, error_code: str | int | None = None) -> None:
        super().__init__(message)
        self.error_code = error_code


def _sign(appid: str, q: str, salt: int, appkey: str) -> str:
    # Sign uses raw q (UTF-8); do not URL-encode before MD5.
    raw = appid + q + str(salt) + appkey
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _parse_translated(body: dict[str, Any]) -> str:
    trans = body.get("trans_result")
    if not trans or not isinstance(trans, list):
        raise BaiduTranslateError("百度翻译响应缺少 trans_result")
    parts: list[str] = []
    for item in trans:
        if isinstance(item, dict) and "dst" in item:
            parts.append(str(item["dst"]))
    if not parts:
        raise BaiduTranslateError("百度翻译 trans_result 为空")
    return "".join(parts)


async def _translate_single_chunk(
    client: httpx.AsyncClient,
    q: str,
    *,
    appid: str,
    appkey: str,
    url: str,
    from_lang: str,
    to_lang: str,
) -> str:
    global _last_baidu_request_end
    interval = max(0.0, float(settings.baidu_translate_min_interval_sec))
    async with _baidu_request_lock:
        if interval > 0:
            wait = interval - (time.monotonic() - _last_baidu_request_end)
            if wait > 0:
                await asyncio.sleep(wait)
        try:
            return await _translate_single_chunk_unlocked(
                client,
                q,
                appid=appid,
                appkey=appkey,
                url=url,
                from_lang=from_lang,
                to_lang=to_lang,
            )
        finally:
            _last_baidu_request_end = time.monotonic()


async def _translate_single_chunk_unlocked(
    client: httpx.AsyncClient,
    q: str,
    *,
    appid: str,
    appkey: str,
    url: str,
    from_lang: str,
    to_lang: str,
) -> str:
    salt = random.randint(32768, 65536)
    sign = _sign(appid, q, salt, appkey)
    data = {
        "q": q,
        "from": from_lang,
        "to": to_lang,
        "appid": appid,
        "salt": str(salt),
        "sign": sign,
    }
    try:
        resp = await client.post(
            url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        body = resp.json()
    except httpx.HTTPError as e:
        raise BaiduTranslateError(f"百度翻译请求失败: {e}") from e
    if not isinstance(body, dict):
        raise BaiduTranslateError("百度翻译响应格式无效")
    body_typed: dict[str, Any] = body
    if "error_code" in body_typed and body_typed["error_code"] not in (None, "", 0, "0"):
        code = body_typed.get("error_code")
        msg = body_typed.get("error_msg", "unknown")
        raise BaiduTranslateError(f"百度翻译错误 {code}: {msg}", error_code=code)
    return _parse_translated(body_typed)


def _chunk_unicode(text: str, max_len: int) -> list[str]:
    if not text:
        return []
    return [text[i : i + max_len] for i in range(0, len(text), max_len)]


async def translate_with_baidu(text: str) -> str:
    """Translate full text, splitting into chunks when longer than the API recommendation."""
    if not text:
        return ""
    appid = settings.baidu_translate_appid.strip()
    appkey = settings.baidu_translate_appkey.strip()
    if not appid or not appkey:
        raise BaiduTranslateError(
            "未配置百度翻译：请在环境变量中设置 BAIDU_TRANSLATE_APPID 与 BAIDU_TRANSLATE_APPKEY",
        )

    url = settings.baidu_translate_url.strip()
    from_lang = settings.baidu_translate_from.strip() or "auto"
    to_lang = settings.baidu_translate_to.strip() or "zh"

    chunks = _chunk_unicode(text, _CHUNK_CHAR_LIMIT)
    timeout = httpx.Timeout(60.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        translated_parts: list[str] = []
        for chunk in chunks:
            translated_parts.append(
                await _translate_single_chunk(
                    client,
                    chunk,
                    appid=appid,
                    appkey=appkey,
                    url=url,
                    from_lang=from_lang,
                    to_lang=to_lang,
                )
            )
    return "".join(translated_parts)
