"""Thin Gemini API wrapper with JSON parsing, thinking control, retry, and live cost tracking."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from .config import MODEL_PRICING_PER_1M, resolve_gemini_api_key


class GeminiUnavailableError(RuntimeError):
    """Raised when no API key is available or the Gemini call cannot proceed."""


FATAL_ERROR_MARKERS = (
    "401",
    "402",
    "403",
    "404",
    "NOT_FOUND",
    "API_KEY_INVALID",
    "PERMISSION_DENIED",
)


def is_fatal_gemini_error(exc: Exception) -> bool:
    msg = str(exc)
    return any(marker in msg for marker in FATAL_ERROR_MARKERS)


def _strip_code_fences(raw: str) -> str:
    text = raw.strip()
    m = re.match(r"^```(?:json)?\s*\n(.*?)\n```$", text, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return text


def _normalize_thinking_level(model: str, level: str | None) -> str | None:
    if not level:
        return None
    norm = level.strip().upper()
    if norm not in ("MINIMAL", "LOW", "MEDIUM", "HIGH"):
        return None
    # Non-lite 3.x Flash models (e.g. gemini-3.8-flash) start at LOW rather than MINIMAL.
    if norm == "MINIMAL" and "lite" not in model.lower():
        return "LOW"
    return norm


@dataclass
class UsageStats:
    calls: int = 0
    prompt_tokens: int = 0
    output_tokens: int = 0
    thought_tokens: int = 0
    cost_usd: float = 0.0

    def record(self, model: str, meta: Any) -> None:
        self.calls += 1
        if meta is None:
            return
        in_tok = int(getattr(meta, "prompt_token_count", 0) or 0)
        out_tok = int(getattr(meta, "candidates_token_count", 0) or 0)
        th_tok = int(getattr(meta, "thoughts_token_count", 0) or 0)
        self.prompt_tokens += in_tok
        self.output_tokens += out_tok
        self.thought_tokens += th_tok

        p_in, p_out = MODEL_PRICING_PER_1M.get(model, (0.75, 3.75))
        self.cost_usd += (in_tok / 1_000_000) * p_in + ((out_tok + th_tok) / 1_000_000) * p_out

    def summary(self) -> str:
        return (
            f"calls={self.calls} | in={self.prompt_tokens:,} tok | "
            f"out={self.output_tokens:,} tok | thoughts={self.thought_tokens:,} tok | "
            f"est_cost=${self.cost_usd:.4f}"
        )


class GeminiHelper:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or resolve_gemini_api_key()
        self._client = None
        self.usage = UsageStats()

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def format_usage_summary(self) -> str:
        return self.usage.summary()

    def _get_client(self):
        if not self.api_key:
            raise GeminiUnavailableError(
                "GEMINI_API_KEY / GOOGLE_API_KEY not found in environment or .env"
            )
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def generate_json(
        self,
        prompt: str,
        model: str,
        image_paths: list[Path] | None = None,
        temperature: float = 0.2,
        thinking_level: str | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        from google.genai import types

        client = self._get_client()
        contents: list[Any] = [prompt]
        opened_images: list[Image.Image] = []

        cfg_kwargs: dict[str, Any] = {
            "temperature": temperature,
            "response_mime_type": "application/json",
        }
        norm_level = _normalize_thinking_level(model, thinking_level)
        if norm_level:
            cfg_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_level=getattr(types.ThinkingLevel, norm_level)
            )
        config = types.GenerateContentConfig(**cfg_kwargs)

        try:
            for img_path in image_paths or []:
                im = Image.open(img_path).convert("RGB")
                opened_images.append(im)
                contents.append(im)

            last_err: Exception | None = None
            for attempt in range(max_retries):
                try:
                    resp = client.models.generate_content(
                        model=model,
                        contents=contents,
                        config=config,
                    )
                    self.usage.record(model, getattr(resp, "usage_metadata", None))
                    text = resp.text or ""
                    return json.loads(_strip_code_fences(text))
                except Exception as exc:
                    last_err = exc
                    if is_fatal_gemini_error(exc):
                        raise
                    time.sleep(2.0 * (attempt + 1))
            raise RuntimeError(f"Gemini request failed after {max_retries} attempts: {last_err}")
        finally:
            for im in opened_images:
                im.close()

    def embed_texts(self, texts: list[str], model: str) -> list[list[float]]:
        client = self._get_client()
        vectors: list[list[float]] = []
        batch_size = 50
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            resp = client.models.embed_content(model=model, contents=chunk)
            for emb in resp.embeddings:
                vectors.append(list(emb.values))
        return vectors
