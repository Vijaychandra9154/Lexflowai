from pydantic import BaseModel
from typing import Optional, Dict


class CaseCreate(BaseModel):
    title: str
    case_number: Optional[str] = None
    forum: Optional[str] = None
    metadata: Optional[Dict] = {}


class CaseOut(BaseModel):
    id: int
    title: str
    case_number: Optional[str]
    forum: Optional[str]
    metadata: Optional[Dict]

    class Config:
        orm_mode = True
