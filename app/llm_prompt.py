"""Prompt construction for the verification LLM."""
from typing import Iterable, List, Dict, Optional


def format_evidence(evidence: Iterable[dict]) -> str:
    lines = []
    for item in evidence:
        source = item.get("source", "unknown")
        score = item.get("score", 0.0)
        text = item.get("text", "").strip()
        url = item.get("url")
        url_str = f"\nURL: {url}" if url else ""
        lines.append(f"Source: {source} (score={score:.2f}){url_str}\n{text}")
    return "\n\n".join(lines)


def make_prompt(claim: str, evidence_list: Iterable[dict]) -> str:
    evidence_section = format_evidence(evidence_list)
    prompt = f"""
You are a financial news fact-checking assistant.

CLAIM:
{claim}

EVIDENCE (retrieved from verified sources):
{evidence_section if evidence_section else 'No relevant evidence retrieved.'}

Task:
1. Compare the claim with the evidence.
2. Give a JSON answer with:
   - verdict: "True", "False", "Misleading", or "Unverifiable"
   - confidence: number between 0.0 and 1.0
   - reasoning: short explanation
   - citations: list of source names you used

Rules:
- Output only a single valid JSON object.
- Do not include markdown, code fences, or any text before/after the JSON.
"""
    return prompt.strip()


def make_chat_prompt(
    message: str,
    evidence_list: Iterable[dict],
    history: List[Dict[str, str]] | None = None,
    context: Optional[str] = None,
) -> str:
    history = history or []
    # Keep last 2 exchanges (user/assistant) to aid context without bloating tokens
    trimmed = history[-4:]
    history_lines = []
    for h in trimmed:
        role = h.get("role", "user")
        content = h.get("content", "")
        history_lines.append(f"{role.title()}: {content}")
    history_block = "\n".join(history_lines)

    evidence_section = format_evidence(evidence_list)
    prompt = f"""
You are a financial Q&A assistant constrained to answer using provided evidence.

Conversation (recent turns):
{history_block if history_block else '(no prior context)'}

Context:
{context if context else '(no additional context)'}

User question:
{message}

EVIDENCE:
{evidence_section if evidence_section else 'No relevant evidence retrieved.'}

Task:
1. Answer succinctly in 2-4 sentences.
2. If the evidence is insufficient, say so and suggest what specific data would verify it.
3. Provide a JSON object with fields:
   - answer: short natural language answer
   - citations: list of source names or URLs you used

Rules:
- Output only a single valid JSON object. No extra text.
 - If the question is vague, use the Context to infer the intended topic and stay on-topic.
 - Prefer directly relevant evidence; ignore tangential market commentary.
"""
    return prompt.strip()
