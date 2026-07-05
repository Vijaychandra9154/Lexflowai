from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .. import db, models
from ..auth import get_password_hash, verify_password, create_access_token

router = APIRouter(prefix="/api", tags=["auth"])


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/signup", response_model=TokenOut)
def signup(u: UserCreate, db: Session = Depends(db.get_db)):
    exists = db.query(models.User).filter(models.User.email == u.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(
        email=u.email,
        hashed_password=get_password_hash(u.password),
        full_name=u.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/token", response_model=TokenOut)
def login(u: UserCreate, db: Session = Depends(db.get_db)):
    user = db.query(models.User).filter(models.User.email == u.email).first()
    if not user or not verify_password(u.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}
