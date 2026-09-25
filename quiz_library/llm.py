"""LLM-клиент: DS Lab (OpenAI-совместимый /chat/completions) через aiohttp."""
from __future__ import annotations

import asyncio
import logging
import time
import uuid

import aiohttp

from quiz_library.model import LLMConfig, Paragraph
from quiz_library.text import paragraph_plain_text

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 12000

SYSTEM_PROMPT = (
    "Ты - учитель. По тексту учебника придумай ОДИН короткий вопрос по параграфу. "
    "Вопрос должен звучать естественно в голосовом разговоре и занимать не более "
    "двух предложений. НЕ используй дословно вопросы, помещённые в учебнике в "
    "конце параграфа."
)

CHOOSE_PROMPT = (
    "Ты - учитель. Дано домашнее задание и список тем учебника. "
    "Определи, к какой теме относится задание. "
    "Ответь ТОЛЬКО ключом темы из списка (строкой без лишнего текста).\n\n"
    "Домашнее задание: {query}\n\nТемы:\n{candidates}"
)


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(self, config: LLMConfig, session: aiohttp.ClientSession | None = None):
        self.config = config
        self._session = session
        self._owns_session = session is None
        self.last_ttfb_ms = 0.0
        self.last_total_ms = 0.0

    @property
    def session(self) -> aiohttp.ClientSession:
        # лениво: aiohttp.ClientSession можно создавать только внутри event loop
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._owns_session and self._session is not None:
            await self._session.close()

    def _build_prompt(self, paragraph: Paragraph) -> str:
        start, end = paragraph.pages
        body = paragraph_plain_text(paragraph)
        if len(body) > MAX_CONTEXT_CHARS:
            body = body[:MAX_CONTEXT_CHARS].rsplit("\n", 1)[0]   # граница строки, не слова
        return (
            f"Параграф {paragraph.key}. {paragraph.title}\n"
            f"Страницы: {start}-{end}\n\n{body}"
        )

    async def _chat(self, system: str, user: str) -> str:
        payload = {
            "model": self.config.model,
            "thinking": {"enabled": False},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        req_id = uuid.uuid4().hex[:8]
        t0 = time.monotonic()
        try:
            async with self.session.post(
                url, json=payload, headers={"Authorization": f"Bearer {self.config.api_key}"},
                timeout=self.config.timeout,
            ) as resp:
                self.last_ttfb_ms = (time.monotonic() - t0) * 1000.0
                data = await resp.json()
                if resp.status != 200:
                    raise LLMError(f"HTTP {resp.status}: {data.get('error') or data}")
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
            raise LLMError(str(exc)) from exc
        except LLMError:
            self.last_total_ms = (time.monotonic() - t0) * 1000.0
            raise
        self.last_total_ms = (time.monotonic() - t0) * 1000.0
        try:
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise LLMError(f"unexpected content type: {type(content).__name__}")
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"unexpected response shape: {data}") from exc
        if not content or not content.strip():
            raise LLMError("empty content from model")
        logger.info("llm qid=%s total_ms=%.0f ttfb_ms=%.0f", req_id, self.last_total_ms, self.last_ttfb_ms)
        return content.strip()

    async def generate_question(self, paragraph: Paragraph) -> str:
        prompt = self._build_prompt(paragraph)
        return await self._chat(SYSTEM_PROMPT, prompt)

    async def complete(self, system: str, user: str) -> str:
        return await self._chat(system, user)

    async def choose_paragraph(self, candidates: list[tuple[str, str, float]], query: str) -> str | None:
        options = "\n".join(f"{key}. {title} (сходство {score})" for key, title, score in candidates)
        prompt = CHOOSE_PROMPT.format(query=query, candidates=options)
        payload = {
            "model": self.config.model,
            "thinking": {"enabled": False},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        req_id = uuid.uuid4().hex[:8]
        t0 = time.monotonic()
        try:
            async with self.session.post(
                url, json=payload, headers={"Authorization": f"Bearer {self.config.api_key}"},
                timeout=self.config.timeout,
            ) as resp:
                self.last_ttfb_ms = (time.monotonic() - t0) * 1000.0
                data = await resp.json()
                if resp.status != 200:
                    raise LLMError(f"HTTP {resp.status}")
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
            raise LLMError(str(exc)) from exc
        self.last_total_ms = (time.monotonic() - t0) * 1000.0
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        clean = content.strip().strip(".,;: ")
        keys = {k for k, _, _ in candidates}
        if clean in keys:
            logger.info("llm arbiter qid=%s total_ms=%.0f ttfb_ms=%.0f chose=%r",
                        req_id, self.last_total_ms, self.last_ttfb_ms, clean)
            return clean
        # 6.1 vs «6.1.» и «ключ 6.1»
        import re
        m = re.search(r"\b(" + "|".join(re.escape(k) for k in keys) + r")\b", clean)
        chosen = m.group(1) if m else None
        logger.info("llm arbiter qid=%s total_ms=%.0f ttfb_ms=%.0f chose=%r raw=%r",
                    req_id, self.last_total_ms, self.last_ttfb_ms, chosen, clean[:80])
        return chosen