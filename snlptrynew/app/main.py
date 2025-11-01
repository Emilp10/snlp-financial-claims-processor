"""FastAPI entrypoint for the fake financial news checker."""
from __future__ import annotations

import json
from typing import Any, Dict

import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

from app.config import get_settings
from app.llm_prompt import make_prompt, make_chat_prompt
from app.llm_parse import parse_llm_json
from app.retrieval import RetrievalError, get_retriever
from app.schemas import (
    ClaimRequest,
    ClaimResponse,
    EvidenceChunk,
    VerdictResult,
    ChatRequest,
    ChatResponse,
    ChatResult,
)
from app.online_retrieval import fetch_online_evidence
from app.keywords import extract_keywords
import re

settings = get_settings()

client_kwargs = {"api_key": settings.openai_api_key}
if settings.openai_base_url:
    client_kwargs["base_url"] = settings.openai_base_url
client = OpenAI(**client_kwargs)

app = FastAPI(title="Fake Financial News Checker", version="0.1.0")

# Configure CORS from settings (supports IPv4/IPv6 localhost by default)
allowed_origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/check", response_model=ClaimResponse)
async def check_claim(claim: ClaimRequest) -> ClaimResponse:
    try:
        retriever = get_retriever()
    except RetrievalError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    evidence = retriever.retrieve(claim.text, top_k=settings.top_k)
    prompt = make_prompt(claim.text, evidence)

    try:
        # Prefer JSON mode when supported by the model
        completion = client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=600,
        )
        content = completion.choices[0].message.content or ""
    except Exception:
        # Fallback: retry without json mode
        try:
            completion = client.chat.completions.create(
                model=settings.openai_chat_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
            )
            content = completion.choices[0].message.content or ""
        except Exception as exc:  # pragma: no cover - third-party client errors
            raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}") from exc

    parsed: Dict[str, Any] = parse_llm_json(content)

    result = VerdictResult(**parsed)
    # Hybrid fallback: if verdict is weak, fetch online evidence and retry once
    should_expand = settings.online_fallback_enabled and (
        result.verdict.lower() == "unverifiable" or result.confidence < settings.supported_th
    )

    if should_expand:
        try:
            kw = extract_keywords(claim.text)
            online = await fetch_online_evidence(
                claim.text,
                days=settings.online_days,
                max_articles=settings.online_top_k * 4,
                keywords=kw,
            )
        except Exception:
            online = []
        if online:
            combined = evidence + online
            retry_prompt = make_prompt(claim.text, combined)
            try:
                retry = client.chat.completions.create(
                    model=settings.openai_chat_model,
                    messages=[{"role": "user", "content": retry_prompt}],
                    response_format={"type": "json_object"},
                    max_tokens=600,
                )
                content2 = retry.choices[0].message.content or ""
            except Exception:
                retry = client.chat.completions.create(
                    model=settings.openai_chat_model,
                    messages=[{"role": "user", "content": retry_prompt}],
                    max_tokens=600,
                )
                content2 = retry.choices[0].message.content or ""
            parsed2 = parse_llm_json(content2)
            result = VerdictResult(**parsed2)
            evidence = combined

    evidence_models = [EvidenceChunk(**{k: v for k, v in item.items() if k in {"text", "source", "chunk_index", "score"}}) for item in evidence]
    return ClaimResponse(claim=claim.text, result=result, evidence=evidence_models)


# Simple in-memory conversation store (dev-only)
_chat_sessions: dict[str, list[dict[str, str]]] = {}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    try:
        retriever = get_retriever()
    except RetrievalError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    session_id = req.session_id or str(__import__("uuid").uuid4())
    history = _chat_sessions.setdefault(session_id, [])
    # Record user message
    history.append({"role": "user", "content": req.message})
    # Trim history to last 6 turns for brevity
    if len(history) > 12:
        del history[:-12]

    # Retrieve evidence
    evidence = retriever.retrieve(req.message, top_k=settings.top_k)

    # Optionally expand online
    if (req.expand_online is None and settings.online_fallback_enabled) or req.expand_online:
        try:
            kw = req.keywords or extract_keywords((req.message or "") + " " + (req.context or ""))
            online = await fetch_online_evidence(
                req.message,
                days=req.days or settings.online_days,
                max_articles=settings.online_top_k * 4,
                keywords=kw,
            )
        except Exception:
            online = []
        if online:
            evidence = evidence + online

    # Ask LLM with a chat-style prompt
    prompt = make_chat_prompt(req.message, evidence, history=history, context=req.context)
    try:
        completion = client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=400,
        )
        content = completion.choices[0].message.content or ""
    except Exception:
        completion = client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
        )
        content = completion.choices[0].message.content or ""

    parsed: Dict[str, Any] = parse_llm_json(content)
    # Map parsed into chat result shape
    try:
        chat_result = ChatResult(**parsed)
    except Exception:
        # Fallback: coerce generically
        chat_result = ChatResult(answer=str(parsed), citations=[])

    # Record assistant answer
    history.append({"role": "assistant", "content": chat_result.answer})

    evidence_models = [EvidenceChunk(**{k: v for k, v in item.items() if k in {"text", "source", "chunk_index", "score"}}) for item in evidence]
    return ChatResponse(session_id=session_id, result=chat_result, evidence=evidence_models)
