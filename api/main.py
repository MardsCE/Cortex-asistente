from fastapi import FastAPI
from pydantic import BaseModel
from services.openrouter_service import openrouter_service

app = FastAPI(title="Cortex API", version="1.0.0")


class ChatRequest(BaseModel):
    message: str
    user_id: str


class ChatResponse(BaseModel):
    response: str
    imagenes: list[str] = []


@app.get("/")
async def root():
    return {"name": "Cortex", "status": "active", "assistant": "Syn"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    resultado = await openrouter_service.ask(request.message, request.user_id)
    return ChatResponse(response=resultado["texto"], imagenes=resultado.get("imagenes", []))
