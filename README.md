# LexFlowAI Starter — Final Pack

AI-assisted legal case management SaaS starter (FastAPI + Next.js + OpenAI + Pinecone).

## Quickstart (Local)

1. Unzip this project.
2. Create `.env` from `.env.example` and fill your keys (OpenAI, Pinecone, etc.).
3. Backend:

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

4. Frontend (new terminal):

```bash
cd frontend
npm install
npm run dev
```

5. Open http://localhost:3000 in your browser.

## Docker

```bash
docker-compose up --build
```

## Render Deployment

Use `render.yaml` for blueprint deploy. Set env vars in Render dashboard (OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME, JWT_SECRET, etc.).
