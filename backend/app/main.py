from fastapi import FastAPI
from .db import engine
from .models import Base
from .routes import cases, ai_controller, auth_routes

Base.metadata.create_all(bind=engine)
app = FastAPI(title="LexFlowAI Backend")

app.include_router(cases.router)
app.include_router(ai_controller.router)
app.include_router(auth_routes.router)


@app.get("/api/health")
def health():
    return {"status": "LexFlowAI backend up"}
