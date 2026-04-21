from __future__ import annotations

import json
from typing import Literal

from anthropic import Anthropic
from pydantic import BaseModel, Field, ValidationError


class ClaudeDecision(BaseModel):
    action: Literal["YES", "NO", "SKIP"]
    confidence: float = Field(ge=0, le=1)
    estimated_prob_yes: float = Field(ge=0, le=1)
    market_implied_prob_yes: float = Field(ge=0, le=1)
    edge_bps: float
    expected_value_per_1usd: float
    liquidity_score: float = Field(ge=0, le=1)
    risk_flags: list[str]
    rationale_bullets: list[str]


class ClaudeClient:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model
        self.client = Anthropic(api_key=api_key) if api_key else None

    def decide(self, prompt: str, fallback: ClaudeDecision) -> ClaudeDecision:
        if not self.client:
            return fallback
        try:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=400,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(
                b.text for b in resp.content if getattr(b, "type", None) == "text" and hasattr(b, "text")
            )
            data = json.loads(text)
            return ClaudeDecision.model_validate(data)
        except (ValidationError, json.JSONDecodeError, Exception):
            return fallback
