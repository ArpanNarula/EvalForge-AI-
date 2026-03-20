"""Deterministic multi-response generator for local demos and tests."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import List

from models.schemas import GeneratedResponse, GenerationStrategy, PromptRequest


class LLMService:
    async def generate_responses(self, request: PromptRequest) -> List[GeneratedResponse]:
        strategies = request.strategies[: max(1, request.num_responses)] or [
            GenerationStrategy.BALANCED,
            GenerationStrategy.CONCISE,
            GenerationStrategy.DETAILED,
        ]
        tasks = [
            self._generate_for_strategy(index, strategy, request.prompt, request.rag_context)
            for index, strategy in enumerate(strategies)
        ]
        return await asyncio.gather(*tasks)

    async def _generate_for_strategy(
        self,
        index: int,
        strategy: GenerationStrategy,
        prompt: str,
        rag_context: str | None,
    ) -> GeneratedResponse:
        lines = self._render_lines(prompt, strategy, rag_context)
        text = "\n".join(lines).strip()
        return GeneratedResponse(
            id=index,
            strategy=strategy,
            strategy_label=strategy.value.title(),
            text=text,
            word_count=len(text.split()),
            char_count=len(text),
            generated_at=datetime.utcnow(),
        )

    def _render_lines(
        self,
        prompt: str,
        strategy: GenerationStrategy,
        rag_context: str | None,
    ) -> List[str]:
        rag_hint = " Prior successful examples were consulted." if rag_context else ""
        topic = prompt.strip().rstrip("?")

        if strategy == GenerationStrategy.CONCISE:
            return [
                f"{topic}:",
                f"In short, the core idea is to answer the prompt directly and avoid unnecessary detours.{rag_hint}",
                "Focus on the main mechanism, why it matters, and one concrete implication.",
            ]

        if strategy == GenerationStrategy.DETAILED:
            return [
                f"Here is a detailed explanation of {topic.lower()}:",
                "1. Start by defining the core concept in plain language.",
                "2. Walk through the process step by step so the reader can follow the logic.",
                "3. Close with why the concept matters in practice and what tradeoffs it introduces."
                f"{rag_hint}",
            ]

        if strategy == GenerationStrategy.CREATIVE:
            return [
                f"Think of {topic.lower()} as a workshop problem:",
                "You first identify the goal, then compare a few ways to reach it, and finally justify the best path.",
                f"That framing keeps the explanation vivid while still answering the prompt.{rag_hint}",
            ]

        if strategy == GenerationStrategy.STRUCTURED:
            return [
                f"{topic}",
                "- Core idea: describe what it is.",
                "- Mechanism: explain how it works.",
                f"- Practical takeaway: explain why someone should care.{rag_hint}",
            ]

        return [
            f"{topic}:",
            "A balanced answer should define the concept, explain how it works, and keep the explanation readable.",
            f"It should stay grounded in the prompt while still giving enough detail to be useful.{rag_hint}",
        ]

