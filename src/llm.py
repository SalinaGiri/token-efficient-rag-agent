"""LLM clients. Ollama (local) reports prefill and decode time separately, which the hardware analysis needs."""
import json
import os
import time
from dataclasses import dataclass, asdict

import requests


@dataclass
class LLMResult:
    text: str
    prompt_tokens: int      # input tokens processed in prefill
    output_tokens: int      # tokens generated in decode
    ttft_ms: float          # client-side time to first token
    wall_ms: float          # client-side total time of the LLM call
    prefill_ms: float       # Ollama prompt_eval_duration
    decode_ms: float        # Ollama eval_duration
    load_ms: float          # model load time (should be ~0 after warm-up)
    done_reason: str        # "length" means the output cap was hit

    def to_dict(self):
        return asdict(self)


class OllamaClient:
    def __init__(self, url, model, num_ctx, seed=0, temperature=0.0, think=None, keep_alive="30m"):
        self.url, self.model = url.rstrip("/"), model
        self.num_ctx, self.seed, self.temperature, self.think, self.keep_alive = num_ctx, seed, temperature, think, keep_alive

    def chat(self, system: str, user: str, max_tokens: int, json_mode: bool = False) -> LLMResult:
        body = {"model": self.model, "stream": True, "keep_alive": self.keep_alive,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "options": {"temperature": self.temperature, "seed": self.seed, "num_ctx": self.num_ctx,
                            "num_predict": max_tokens}}
        if self.think is not None:
            body["think"] = self.think
        if json_mode:
            body["format"] = "json"
        t0 = time.perf_counter()
        ttft, parts, final = None, [], {}
        with requests.post(f"{self.url}/api/chat", json=body, stream=True, timeout=600) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                msg = json.loads(line)
                piece = msg.get("message", {}).get("content", "")
                if piece and ttft is None:
                    ttft = (time.perf_counter() - t0) * 1000
                parts.append(piece)
                if msg.get("done"):
                    final = msg
        wall = (time.perf_counter() - t0) * 1000
        return LLMResult(text="".join(parts).strip(),
                         prompt_tokens=int(final.get("prompt_eval_count", 0)),
                         output_tokens=int(final.get("eval_count", 0)),
                         ttft_ms=ttft if ttft is not None else wall, wall_ms=wall,
                         prefill_ms=final.get("prompt_eval_duration", 0) / 1e6,
                         decode_ms=final.get("eval_duration", 0) / 1e6,
                         load_ms=final.get("load_duration", 0) / 1e6,
                         done_reason=final.get("done_reason", ""))


class OpenAICompatClient:
    """Any OpenAI-compatible chat API (OpenAI, DeepSeek, Qwen/DashScope, ...). Used for the judge."""
    def __init__(self, base_url, model, api_key_env):
        self.base_url, self.model = base_url.rstrip("/"), model
        self.key = os.environ.get(api_key_env)
        if not self.key:
            raise RuntimeError(f"Set the environment variable {api_key_env} with your API key.")

    def chat(self, system: str, user: str, max_tokens: int, json_mode: bool = False) -> LLMResult:
        body = {"model": self.model, "temperature": 0, "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        t0 = time.perf_counter()
        r = requests.post(f"{self.base_url}/chat/completions", json=body, timeout=300,
                          headers={"Authorization": f"Bearer {self.key}"})
        r.raise_for_status()
        data = r.json()
        wall = (time.perf_counter() - t0) * 1000
        usage = data.get("usage", {})
        return LLMResult(text=data["choices"][0]["message"]["content"].strip(),
                         prompt_tokens=usage.get("prompt_tokens", 0), output_tokens=usage.get("completion_tokens", 0),
                         ttft_ms=wall, wall_ms=wall, prefill_ms=0, decode_ms=0, load_ms=0,
                         done_reason=data["choices"][0].get("finish_reason", ""))


def make_judge_client(cfg: dict, ollama_url: str, num_ctx: int):
    if cfg["backend"] == "ollama":
        return OllamaClient(ollama_url, cfg["model"], num_ctx=num_ctx)
    return OpenAICompatClient(cfg["base_url"], cfg["model"], cfg["api_key_env"])
