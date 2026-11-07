import json
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


class ChatUser(HttpUser):
    wait_time = between(1, 2)
    headers = {"X-API-Key": API_KEY}

    def on_start(self) -> None:
        with self.client.post(
            CONVERSATIONS_PATH,
            json={},
            headers=self.headers,
            name="POST /conversations",
            catch_response=True,
        ) as resp:
            if resp.status_code not in (200, 201):
                resp.failure(f"create failed: {resp.status_code}")
                self.conversation_id = None
                return
            self.conversation_id = resp.json()["id"]

    @task
    def chat_stream(self) -> None:
        if not self.conversation_id:
            return

        question = QUESTIONS[int(time.time()) % len(QUESTIONS)]
        start = time.perf_counter()
        ttft_ms: float | None = None
        got_done = False

        with self.client.post(
            STREAM_PATH.format(conversation_id=self.conversation_id),
            json={"content": question},  # TODO: asli body schema
            headers={**self.headers, "Accept": "text/event-stream"},
            stream=True,
            name="POST /stream (SSE)",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"status {resp.status_code}")
                return

            for line in resp.iter_lines():
                if not line:
                    continue
                if ttft_ms is None and line.startswith(b"data:"):
                    ttft_ms = (time.perf_counter() - start) * 1000
                if b"[DONE]" in line or b"event: done" in line:
                    got_done = True

            total_ms = (time.perf_counter() - start) * 1000
            if ttft_ms is None or not got_done:
                resp.failure("stream incomplete")
                return
            resp.success()

        # TTFT ko alag metric ke taur par report karo
        events.request.fire(
            request_type="SSE",
            name="TTFT",
            response_time=ttft_ms,
            response_length=0,
            exception=None,
            context={},
        )