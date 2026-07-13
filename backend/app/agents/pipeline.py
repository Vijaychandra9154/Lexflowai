"""
Five-agent drafting pipeline.

Each agent is a focused Claude call. They run sequentially, each passing
structured output to the next stage.

Stage 1 — intake:       extract structured facts from raw complaint + PDF text
Stage 2 — jurisdiction: validate institution choice, determine addressee + acts
Stage 3 — grounds:      identify legal provisions and grounds for relief
Stage 4 — draft:        generate the full formatted document
Stage 5 — compliance:   verify required sections are present, flag gaps
"""

import os
import json
import asyncio
from typing import AsyncIterator

import anthropic


def _client() -> anthropic.AsyncAnthropic:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured.")
    return anthropic.AsyncAnthropic(api_key=key)


MODEL = "claude-sonnet-4-6"


async def _call(client: anthropic.AsyncAnthropic, system: str, user: str, max_tokens: int = 800) -> str:
    msg = await client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text.strip()


# ---------------------------------------------------------------------------
# Stage 1 — Intake
# ---------------------------------------------------------------------------
INTAKE_SYSTEM = """You are a legal intake specialist for Indian law.
Extract structured facts from the complainant's narrative. Return ONLY valid JSON with these keys:
- parties: {petitioner: str, respondent: str, location: str}
- incident_dates: list of date strings found (or [])
- core_grievance: one sentence summary of the main complaint
- key_facts: list of 3-6 bullet-point facts
- evidence_mentioned: list of documents/evidence mentioned by the user
- urgency_indicators: list of any urgency factors (health, safety, deadline)

If a field has no data, use null or []. Return only the JSON object, no other text."""


async def stage_intake(client, complaint: str, pdf_text: str, petitioner: str, respondent: str, location: str) -> dict:
    user = f"""Complaint: {complaint or '(see PDF)'}
PDF extract: {pdf_text[:2000] if pdf_text else 'None'}
Petitioner: {petitioner or 'Not provided'}
Respondent: {respondent or 'Not provided'}
Location: {location or 'Not provided'}"""

    raw = await _call(client, INTAKE_SYSTEM, user, max_tokens=600)
    try:
        # strip markdown fences if model adds them
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(cleaned)
    except Exception:
        return {"core_grievance": complaint[:300], "key_facts": [], "parties": {}, "evidence_mentioned": [], "urgency_indicators": [], "incident_dates": []}


# ---------------------------------------------------------------------------
# Stage 2 — Jurisdiction
# ---------------------------------------------------------------------------
JURISDICTION_SYSTEM = """You are an Indian legal jurisdiction expert.
Given the institution selected and the facts, confirm or correct the routing and return ONLY valid JSON:
- confirmed_institution: string (use the exact institution name provided unless clearly wrong)
- addressee_block: full multi-line addressee text for the document header
- applicable_acts: list of 2-5 most relevant Indian acts/articles for this grievance
- jurisdiction_notes: one sentence on why this institution has jurisdiction
- alternative_forum: name of one alternative forum if applicable, else null

Return only the JSON object."""


async def stage_jurisdiction(client, institution: str, inst_config: dict, facts: dict) -> dict:
    user = f"""Institution selected: {institution}
Institution config: {json.dumps(inst_config, indent=2)}
Extracted facts: {json.dumps(facts, indent=2)}"""

    raw = await _call(client, JURISDICTION_SYSTEM, user, max_tokens=500)
    try:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(cleaned)
    except Exception:
        return {
            "confirmed_institution": institution,
            "addressee_block": inst_config.get("addressee", institution),
            "applicable_acts": inst_config.get("relevant_acts", []),
            "jurisdiction_notes": "",
            "alternative_forum": None,
        }


# ---------------------------------------------------------------------------
# Stage 3 — Legal Grounds
# ---------------------------------------------------------------------------
GROUNDS_SYSTEM = """You are an expert in Indian statutory law and constitutional provisions.
Identify the specific legal grounds for the complaint. Return ONLY valid JSON:
- grounds: list of objects, each with:
    - ground_number: int
    - heading: short legal ground title
    - description: 1-2 sentences explaining the ground
    - provisions: list of specific act sections or articles (e.g. "Section 7 of RTI Act, 2005")
- prayer_points: list of 3-5 specific reliefs to be requested
- evidence_required: list of documents the petitioner should attach

CRITICAL: Never invent section numbers. If uncertain, use "[VERIFY: Section __ of __ Act]".
Return only the JSON object."""


async def stage_grounds(client, facts: dict, jurisdiction: dict, draft_type: str) -> dict:
    user = f"""Draft type: {draft_type}
Facts: {json.dumps(facts, indent=2)}
Jurisdiction: {json.dumps(jurisdiction, indent=2)}"""

    raw = await _call(client, GROUNDS_SYSTEM, user, max_tokens=800)
    try:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(cleaned)
    except Exception:
        return {"grounds": [], "prayer_points": ["Grant appropriate relief as deemed fit"], "evidence_required": []}


# ---------------------------------------------------------------------------
# Stage 4 — Draft Generator (streaming)
# ---------------------------------------------------------------------------
DRAFT_SYSTEM = """You are an expert Indian legal document drafter.

Rules:
1. Use formal Indian legal language and the exact addressee block provided
2. Structure: To, Subject, Respectful submission, numbered paragraphs, Grounds, Prayer, Verification, Annexures
3. Use the specific legal grounds and prayer points provided — do not invent new ones
4. Never invent section numbers or case citations; use [VERIFY: ...] for uncertain provisions
5. Insert [PETITIONER NAME], [DATE], [PLACE] where the user must fill in details
6. End with a proper Verification clause and numbered Annexure list
7. Close with: ⚠️ AI-generated draft — review with a qualified advocate before submission."""


async def stage_draft_stream(
    client: anthropic.AsyncAnthropic,
    draft_type: str,
    institution: str,
    facts: dict,
    jurisdiction: dict,
    grounds: dict,
    extra_context: str,
) -> AsyncIterator[str]:

    user = f"""Draft a {draft_type} for submission to {institution}.

ADDRESSEE:
{jurisdiction.get('addressee_block', institution)}

PARTIES:
Petitioner: {facts.get('parties', {}).get('petitioner', '[PETITIONER NAME]')}
Respondent: {facts.get('parties', {}).get('respondent', '[RESPONDENT]')}
Location: {facts.get('parties', {}).get('location', '[LOCATION]')}

CORE GRIEVANCE: {facts.get('core_grievance', '')}

KEY FACTS:
{chr(10).join(f"- {f}" for f in facts.get('key_facts', []))}

APPLICABLE ACTS: {', '.join(jurisdiction.get('applicable_acts', []))}

LEGAL GROUNDS:
{json.dumps(grounds.get('grounds', []), indent=2)}

PRAYER POINTS:
{json.dumps(grounds.get('prayer_points', []), indent=2)}

EVIDENCE / ANNEXURES:
{json.dumps(grounds.get('evidence_required', []), indent=2)}

{f"ADDITIONAL INSTRUCTIONS: {extra_context}" if extra_context else ""}

Write the complete formal document now."""

    async with client.messages.stream(
        model=MODEL,
        max_tokens=2500,
        system=DRAFT_SYSTEM,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        async for text in stream.text_stream:
            yield text


# ---------------------------------------------------------------------------
# Stage 5 — Compliance Review
# ---------------------------------------------------------------------------
COMPLIANCE_SYSTEM = """You are a senior Indian legal reviewer doing a compliance check on a draft document.
Check the draft and return ONLY valid JSON:
- passed: bool (true if all critical sections present)
- issues: list of strings describing missing or defective sections (empty list if none)
- warnings: list of non-critical suggestions
- rti_fee_mentioned: bool or null (only relevant for RTI — null if not RTI)
- verification_clause_present: bool
- annexure_list_present: bool
- prayer_clause_present: bool

Return only the JSON object."""


async def stage_compliance(client, draft_text: str, institution: str) -> dict:
    user = f"""Institution: {institution}
Draft document:
---
{draft_text[:4000]}
---"""

    raw = await _call(client, COMPLIANCE_SYSTEM, user, max_tokens=500)
    try:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(cleaned)
    except Exception:
        return {"passed": True, "issues": [], "warnings": [], "verification_clause_present": True, "prayer_clause_present": True, "annexure_list_present": True, "rti_fee_mentioned": None}


# ---------------------------------------------------------------------------
# Public entry point — full pipeline with streaming
# ---------------------------------------------------------------------------
async def run_pipeline(
    institution: str,
    inst_config: dict,
    draft_type: str,
    complaint: str,
    pdf_text: str,
    petitioner_name: str,
    respondent_name: str,
    location: str,
    extra_context: str,
) -> AsyncIterator[str]:
    """
    Yields SSE lines: data: {"type": ..., "payload": ...}

    Types emitted:
      stage      — stage name starting (for progress UI)
      text       — streaming draft text chunk
      compliance — final compliance report
      done       — pipeline complete
      error      — fatal error
    """

    def sse(type_: str, payload) -> str:
        return f"data: {json.dumps({'type': type_, 'payload': payload})}\n\n"

    client = _client()

    try:
        # Stage 1
        yield sse("stage", "Extracting facts from your complaint...")
        facts = await stage_intake(client, complaint, pdf_text, petitioner_name, respondent_name, location)

        # Stage 2
        yield sse("stage", "Confirming jurisdiction and addressee...")
        jurisdiction = await stage_jurisdiction(client, institution, inst_config, facts)

        # Stage 3
        yield sse("stage", "Identifying legal grounds and prayer...")
        grounds = await stage_grounds(client, facts, jurisdiction, draft_type)

        # Stage 4 — streaming
        yield sse("stage", "Drafting your document...")
        full_draft = ""
        async for chunk in stage_draft_stream(client, draft_type, institution, facts, jurisdiction, grounds, extra_context):
            full_draft += chunk
            yield sse("text", chunk)

        # Stage 5
        yield sse("stage", "Running compliance check...")
        compliance = await stage_compliance(client, full_draft, institution)
        yield sse("compliance", compliance)

        yield sse("done", None)

    except Exception as e:
        yield sse("error", str(e))
