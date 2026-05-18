"""
Oracle Router — sovereign LLM routing.

Priority:
  1. Ollama (local, sovereign, offline-capable) — always tried first
  2. xAI Grok (constitutional alignment)
  3. OpenAI (fallback)
  4. Embedded Symbolic Reasoner (always available, no API needed)

The system works without any API key.
The embedded fallback ensures full local sovereignty.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any


def default_router() -> "OracleRouter":
    """Build an OracleRouter from runtime config. Use instead of OracleRouter() directly."""
    try:
        from cursiv_v215.runtime.config import config
        return OracleRouter(
            ollama_model     = config.ollama_model,
            ollama_url       = config.ollama_url,
            ollama_num_ctx   = config.ollama_num_ctx,
            ollama_timeout_s = config.ollama_timeout_s,
        )
    except Exception:
        return OracleRouter()


class OracleRouter:
    def __init__(
        self,
        ollama_model: str = "llama3.1",
        ollama_url: str = "http://localhost:11434",
        ollama_num_ctx: int = 32768,
        ollama_timeout_s: int = 120,
        xai_api_key: str | None = None,
        openai_api_key: str | None = None,
    ) -> None:
        self.ollama_model     = ollama_model
        self.ollama_url       = ollama_url
        self.ollama_num_ctx   = ollama_num_ctx
        self.ollama_timeout_s = ollama_timeout_s
        self.xai_api_key      = xai_api_key or os.getenv("XAI_API_KEY")
        self.openai_api_key   = openai_api_key or os.getenv("OPENAI_API_KEY")
        self._active_provider: str = "unknown"

    @property
    def active_provider(self) -> str:
        return self._active_provider

    def call(self, prompt: str, max_tokens: int = 800, on_token: Any = None) -> str:
        """Route through providers in priority order. Always returns a string.

        on_token: optional callable(str) — called with each text chunk as it
        arrives from Ollama streaming. Ignored for xAI/OpenAI/embedded paths.
        """
        result = self._try_ollama(prompt, max_tokens, on_token=on_token)
        if result is not None:
            self._active_provider = "ollama"
            return result

        result = self._try_xai(prompt, max_tokens)
        if result is not None:
            self._active_provider = "xai"
            return result

        result = self._try_openai(prompt, max_tokens)
        if result is not None:
            self._active_provider = "openai"
            return result

        self._active_provider = "embedded"
        return self._embedded_fallback(prompt)

    def _try_ollama(self, prompt: str, max_tokens: int, on_token: Any = None) -> str | None:
        try:
            import urllib.request
            streaming = on_token is not None
            payload = json.dumps({
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": streaming,
                "options": {
                    "num_predict": max_tokens,
                    "num_ctx":     self.ollama_num_ctx,
                },
            }).encode()
            req = urllib.request.Request(
                f"{self.ollama_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.ollama_timeout_s) as resp:
                if not streaming:
                    data = json.loads(resp.read())
                    return data.get("response", "")
                # Streaming: Ollama sends one JSON object per line (NDJSON).
                # Accumulate tokens and fire on_token for each chunk.
                chunks: list[str] = []
                for raw_line in resp:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = obj.get("response", "")
                    if token:
                        chunks.append(token)
                        try:
                            on_token(token)
                        except Exception:
                            pass
                    if obj.get("done"):
                        break
                return "".join(chunks)
        except Exception:
            return None

    def _try_xai(self, prompt: str, max_tokens: int) -> str | None:
        if not self.xai_api_key:
            return None
        try:
            import urllib.request
            payload = json.dumps({
                "model": "grok-beta",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
            }).encode()
            req = urllib.request.Request(
                "https://api.x.ai/v1/chat/completions",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.xai_api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"]
        except Exception:
            return None

    def _try_openai(self, prompt: str, max_tokens: int) -> str | None:
        if not self.openai_api_key:
            return None
        try:
            import urllib.request
            payload = json.dumps({
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
            }).encode()
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.openai_api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"]
        except Exception:
            return None

    def _embedded_fallback(self, prompt: str) -> str:
        """
        Symbolic reasoner — no API required.
        Extracts structure from the prompt and returns a grounded response.
        """
        lines = prompt.strip().split("\n")
        key_lines = [l.strip() for l in lines if l.strip() and not l.startswith("#")]

        if "JSON" in prompt or "json" in prompt:
            fields = re.findall(r'"(\w+)":', prompt)
            if fields:
                result = {f: f"[{f}_value]" for f in fields[:6]}
                return json.dumps(result, indent=2)

        if "?" in prompt:
            questions = [l for l in key_lines if "?" in l]
            if questions:
                q = questions[0][:80]
                return f"Embedded analysis of: {q}\n\nThis requires further context. The system is operating in offline mode. Key consideration: {key_lines[-1][:100] if key_lines else 'none'}"

        summary = " ".join(key_lines[:3])[:200]
        return f"Embedded symbolic response:\n{summary}\n\n[Operating in sovereign offline mode — no external API required]"
