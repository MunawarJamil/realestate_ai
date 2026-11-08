import os
import time

from locust import HttpUser, between, events, task

API_KEY = os.environ.get("LOAD_TEST_API_KEY", "")  # rk_live_...
CONVERSATIONS_PATH = "/api/v1/chat/conversations"
STREAM_PATH = "/api/v1/chat/conversations/{conversation_id}/stream"

QUESTIONS = [
    "What 2 bedroom apartments do you have in Dubai Marina?",
    "What are your payment plans?",
    "Can I book a viewing this weekend?",
    "Do you have anything under 1.5M AED?",
]


def _short(line: bytes, limit: int = 80) -> str:
    return line.decode(errors="replace").strip()[:limit]


class ChatUser(HttpUser):
    wait_time = between(1, 2)
    headers = {"X-API-Key": API_KEY}
    conversation_id: str | None = None

    def _ensure_conversation(self) -> bool:
        if self.conversation_id:
            return True
        with self.client.post(
            CONVERSATIONS_PATH,
            json={},
            headers=self.headers,
            name="POST /conversations",
            catch_response=True,
        ) as resp:
            if resp.status_code not in (200, 201):
                resp.failure(f"create failed: {resp.status_code}")
                return False
            self.conversation_id = resp.json()["id"]
            return True

    def on_start(self) -> None:
        self._ensure_conversation()

    @task
    def chat_stream(self) -> None:
        if not self._ensure_conversation():
            return

        question = QUESTIONS[int(time.time()) % len(QUESTIONS)]
        start = time.perf_counter()
        ttft_ms: float | None = None
        got_done = False
        error_line = ""
        last_line = ""

        with self.client.post(
            STREAM_PATH.format(conversation_id=self.conversation_id),
            json={"content": question},
            headers={**self.headers, "Accept": "text/event-stream"},
            stream=True,
            name="POST /stream (SSE)",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"status {resp.status_code}")
                return

            try:
                for line in resp.iter_lines():
                    if not line:
                        continue
                    last_line = _short(line)
                    if ttft_ms is None and line.startswith(b"data:"):
                        ttft_ms = (time.perf_counter() - start) * 1000
                    if not error_line and b"error" in line.lower():
                        error_line = _short(line)
                    if b"[DONE]" in line or b"event: done" in line:
                        got_done = True
            except Exception as exc:  # connection reset / chunked read error
                resp.failure(f"stream broken: {type(exc).__name__}")
                return

            if error_line:
                resp.failure(f"error event: {error_line}")
                return
            if ttft_ms is None:
                resp.failure("no data received")
                return
            if not got_done:
                resp.failure(f"no done event, last: {last_line}")
                return
            resp.success()

        events.request.fire(
            request_type="SSE",
            name="TTFT",
            response_time=ttft_ms,
            response_length=0,
            exception=None,
            context={},
        )