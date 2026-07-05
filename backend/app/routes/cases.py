from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from .. import db, models, schemas

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.post("/", response_model=schemas.CaseOut)
def create_case(case: schemas.CaseCreate, db: Session = Depends(db.get_db)):
    c = models.Case(
        title=case.title,
        case_number=case.case_number,
        forum=case.forum,
        metadata=case.metadata,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.get("/{case_id}", response_model=schemas.CaseOut)
def get_case(case_id: int, db: Session = Depends(db.get_db)):
    c = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Case not found")
    return c


@router.post("/{case_id}/upload")
async def upload_document(case_id: int, file: UploadFile = File(...), db: Session = Depends(db.get_db)):
    content = await file.read()
    try:
        text = content.decode(errors="ignore")[:100000]
    except Exception:
        text = ""
    doc = models.Document(case_id=case_id, filename=file.filename, content=text)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    from ..ai_utils import VECTOR_INDEX
    VECTOR_INDEX.add([text[:10000] if text else file.filename])
    return {"ok": True, "doc_id": doc.id}
