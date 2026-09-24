import pytest

from quiz_library.llm import LLMClient, LLMError
from quiz_library.model import LLMConfig, Paragraph

CONTENT = "Какой фактор размещения важнее для газовой промышленности?"


def _para(lines=("Газ.", "Текст параграфа.")):
    return Paragraph(number=6, title="Газовая промышленность", pages=(22, 25),
                     blocks=[{"type": "text", "lines": list(lines)}])


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def json(self):
        return self._payload


class FakeRequest:
    """Похож на real aiohttp: post() возвращает контекстный менеджер запроса."""

    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, *exc):
        return False


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.posts = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def post(self, url, headers=None, json=None, timeout=None):
        self.posts.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeRequest(self.response)


async def test_generate_question_returns_content():
    resp = FakeResponse({"choices": [{"message": {"content": CONTENT}}]})
    sess = FakeSession(resp)
    client = LLMClient(LLMConfig("https://api.dslab.tech/v1", "K", "m", 20.0), session=sess)
    text = await client.generate_question(_para())
    assert text == CONTENT


def test_client_constructed_without_running_loop_ok():
    # сессия aiohttp создаётся лениво (при первом async-вызове), поэтому
    # конструкция клиента вне event loop не должна падать
    client = LLMClient(LLMConfig("https://api.dslab.tech/v1", "K", "m", 20.0))
    assert client._session is None


async def test_request_shape_thinking_disabled():
    resp = FakeResponse({"choices": [{"message": {"content": CONTENT}}]})
    sess = FakeSession(resp)
    client = LLMClient(LLMConfig("https://api.dslab.tech/v1", "K", "m", 20.0), session=sess)
    await client.generate_question(_para())
    post = sess.posts[0]
    body = post["json"]
    assert body["model"] == "m"
    assert body["thinking"] == {"enabled": False}
    assert body["messages"][0]["role"] == "system"
    user = body["messages"][1]
    assert "параграф" in user["content"] or "Параграф" in user["content"]
    assert post["headers"]["Authorization"] == "Bearer K"
    assert post["url"].endswith("/chat/completions")


async def test_prompt_contains_title_and_pages():
    resp = FakeResponse({"choices": [{"message": {"content": CONTENT}}]})
    sess = FakeSession(resp)
    client = LLMClient(LLMConfig("https://api.dslab.tech/v1", "K", "m", 20.0), session=sess)
    await client.generate_question(_para())
    user = sess.posts[0]["json"]["messages"][1]["content"]
    assert "Газовая промышленность" in user
    assert "22-25" in user


async def test_latency_metrics_recorded():
    resp = FakeResponse({"choices": [{"message": {"content": CONTENT}}]})
    sess = FakeSession(resp)
    client = LLMClient(LLMConfig("https://api.dslab.tech/v1", "K", "m", 20.0), session=sess)
    await client.generate_question(_para())
    assert client.last_ttfb_ms >= 0
    assert client.last_total_ms >= client.last_ttfb_ms


async def test_http_error_raises_llm_error():
    resp = FakeResponse({"error": "boom"}, status=500)
    sess = FakeSession(resp)
    client = LLMClient(LLMConfig("https://api.dslab.tech/v1", "K", "m", 20.0), session=sess)
    with pytest.raises(LLMError):
        await client.generate_question(_para())


async def test_empty_content_raises_llm_error():
    resp = FakeResponse({"choices": [{"message": {"content": ""}}]})
    sess = FakeSession(resp)
    client = LLMClient(LLMConfig("https://api.dslab.tech/v1", "K", "m", 20.0), session=sess)
    with pytest.raises(LLMError):
        await client.generate_question(_para())


async def test_prompt_truncated_to_max_context():
    resp = FakeResponse({"choices": [{"message": {"content": CONTENT}}]})
    sess = FakeSession(resp)
    client = LLMClient(LLMConfig("https://api.dslab.tech/v1", "K", "m", 20.0), session=sess)
    long_lines = [f"строка {i} " + "-" * 50 for i in range(400)]
    await client.generate_question(_para(long_lines))
    user = sess.posts[0]["json"]["messages"][1]["content"]
    assert len(user) <= 12000 + 200