import os
import json
import asyncio
from pathlib import Path
from typing import AsyncIterator

import anthropic
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..agents.pipeline import run_pipeline

router = APIRouter(prefix="/api/ai", tags=["ai"])

TEMPLATES_PATH = Path(__file__).parent.parent.parent.parent / "prompt_templates" / "prompt_templates.json"

_templates_cache: dict | None = None


def _load_templates() -> dict:
    global _templates_cache
    if _templates_cache is None:
        with open(TEMPLATES_PATH, "r", encoding="utf-8") as f:
            _templates_cache = json.load(f)
    return _templates_cache


def _get_institution_config(institution: str) -> dict:
    templates = _load_templates()
    institutions = templates.get("institutions", {})
    return institutions.get(institution, {})


SYSTEM_PROMPT = """You are an expert Indian legal document drafter with deep knowledge of Indian legal procedures, especially for quasi-judicial bodies like Lokayuktha, NHRC, SHRC, Women's Commission, Consumer Forums, and civil courts.

Your task is to draft formal, professional Indian legal documents. Follow these rules strictly:
1. Use proper legal language and formatting for Indian courts/commissions
2. Include standard sections: To (authority), Subject, Respectful submission header, numbered paragraphs, prayer/relief section, date/signature block
3. Reference relevant Indian laws and sections where appropriate — NEVER invent act sections or case citations; use [VERIFY: Section __ of __ Act] for any uncertain provision
4. Be specific, factual, and formal
5. End with a proper prayer clause requesting specific relief
6. Use "Respectfully submitted" style openings
7. Always include a verification clause and list of annexures at the end
8. Insert [PETITIONER NAME], [DATE], [PLACE] placeholders where the user must fill in details
9. Always end with: "⚠️ This is an AI-generated draft for reference only. Please review with a qualified advocate before submission." """


class DraftRequest(BaseModel):
    institution: str
    draft_type: str
    complaint: str = ""
    extracted_pdf_text: str = ""
    petitioner_name: str = ""
    respondent_name: str = ""
    location: str = ""
    extra_context: str = ""


async def _stream_claude(user_prompt: str) -> AsyncIterator[str]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    client = anthropic.AsyncAnthropic(api_key=api_key)

    async with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield f"data: {json.dumps({'text': text})}\n\n"

    yield "data: [DONE]\n\n"


@router.post("/draft")
async def generate_draft(req: DraftRequest):
    if not req.complaint and not req.extracted_pdf_text:
        raise HTTPException(status_code=400, detail="Provide a complaint description or upload a case file.")

    inst_config = _get_institution_config(req.institution)

    institution_context = ""
    if inst_config:
        acts = ", ".join(inst_config.get("relevant_acts", []))
        sections = ", ".join(inst_config.get("required_sections", []))
        special = inst_config.get("special_instructions", "")
        addressee = inst_config.get("addressee", req.institution)
        institution_context = f"""
INSTITUTION DETAILS:
Addressee: {addressee}
Relevant Acts: {acts}
Required Sections: {sections}
Special Instructions: {special}
"""

    user_prompt = f"""Draft a {req.draft_type} to be submitted to: {req.institution}
{f"Petitioner Name: {req.petitioner_name}" if req.petitioner_name else ""}
{f"Respondent / Opposite Party: {req.respondent_name}" if req.respondent_name else ""}
{f"Location: {req.location}" if req.location else ""}
{institution_context}
COMPLAINT / SITUATION:
{req.complaint or "[See case file extract below]"}
{f"EXTRACTED FROM UPLOADED CASE FILE:{chr(10)}{req.extracted_pdf_text[:3000]}" if req.extracted_pdf_text else ""}
{f"ADDITIONAL INSTRUCTIONS:{chr(10)}{req.extra_context}" if req.extra_context else ""}

Please draft a complete, properly formatted {req.draft_type} for submission to {req.institution}. Use formal Indian legal language. Include all standard sections and a clear prayer clause."""

    return StreamingResponse(
        _stream_claude(user_prompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/extract-pdf")
async def extract_pdf(file: UploadFile = File(...)):
    filename = file.filename or ""
    content = await file.read()

    if filename.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(content))
            pages = reader.pages[:5]
            text = "\n".join(page.extract_text() or "" for page in pages).strip()
            if not text:
                return {"text": "", "warning": "No selectable text found in PDF. Try typing your complaint manually."}
            return {"text": text}
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not parse PDF: {str(e)}")

    # Plain text file
    try:
        text = content.decode("utf-8", errors="ignore")
        return {"text": text[:50000]}
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not read file: {str(e)}")


@router.post("/draft-v2")
async def generate_draft_pipeline(req: DraftRequest):
    """Five-agent pipeline: intake → jurisdiction → grounds → draft (streaming) → compliance."""
    if not req.complaint and not req.extracted_pdf_text:
        raise HTTPException(status_code=400, detail="Provide a complaint description or upload a case file.")

    inst_config = _get_institution_config(req.institution)

    return StreamingResponse(
        run_pipeline(
            institution=req.institution,
            inst_config=inst_config,
            draft_type=req.draft_type,
            complaint=req.complaint,
            pdf_text=req.extracted_pdf_text,
            petitioner_name=req.petitioner_name,
            respondent_name=req.respondent_name,
            location=req.location,
            extra_context=req.extra_context,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# Keep legacy endpoint so existing integrations don't break
class _LegacyDraftRequest(BaseModel):
    case_id: int
    prompt_context: str
    instruction: str


@router.post("/draft-legacy")
async def generate_draft_legacy(req: _LegacyDraftRequest):
    from ..ai_utils import VECTOR_INDEX, llm_generate
    passages = VECTOR_INDEX.query(req.prompt_context, k=5)
    context = "\n\n".join(passages)
    prompt = (
        f"Context: {context}\n\n"
        f"Instruction: {req.instruction}\n\n"
        "Produce a lawyer-ready draft reply in Indian legal tone. "
        "Mark citations if referenced and flag anything that needs human verification."
    )
    try:
        draft = llm_generate(prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"draft": draft, "sources": passages}
