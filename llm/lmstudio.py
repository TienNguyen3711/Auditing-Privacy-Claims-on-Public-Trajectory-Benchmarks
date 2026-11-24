"""Minimal client for the local LM Studio server (OpenAI-compatible chat API).

PROTOTYPING ONLY (PLAN.md, decisions): LM Studio serves quantised third-party weights, so its outputs never enter the
paper. Reported numbers come from the transformers runner on pinned checkpoints.
"""
from __future__ import annotations

import json
import urllib.request

BASE_URL = "http://localhost:1234/v1"


def chat(model: str, prompt: str, max_tokens: int = 200, temperature: float = 0.0, seed: int = 0,
         timeout: float = 600, base_url: str = BASE_URL) -> dict:
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens,
            "temperature": temperature, "seed": seed}
    req = urllib.request.Request(f"{base_url}/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    msg = data["choices"][0]["message"]
    return {"text": msg.get("content") or "", "usage": data.get("usage", {}), "model": data.get("model", model)}
