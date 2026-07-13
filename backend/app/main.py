from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import engine
from .models import Base
from .routes import cases, ai_controller, auth_routes

Base.metadata.create_all(bind=engine)
app = FastAPI(title="LexFlowAI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.netlify.app",
        "https://*.netlify.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cases.router)
app.include_router(ai_controller.router)
app.include_router(auth_routes.router)


@app.get("/api/health")
def health():
    return {"status": "LexFlowAI backend up"}
