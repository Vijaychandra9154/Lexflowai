from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..ai_utils import VECTOR_INDEX, llm_generate

router = APIRouter(prefix="/api/ai", tags=["ai"])


class DraftRequest(BaseModel):
    case_id: int
    prompt_context: str
    instruction: str


@router.post("/draft")
async def generate_draft(req: DraftRequest):
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
