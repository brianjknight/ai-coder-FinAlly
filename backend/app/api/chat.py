"""Chat endpoints: delegate to the LLM module."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import db
from app.market import MarketDataSource, PriceCache

from .deps import get_price_cache, get_source

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


@router.post("")
async def chat(
    req: ChatRequest,
    cache: PriceCache = Depends(get_price_cache),
    source: MarketDataSource | None = Depends(get_source),
) -> dict:
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message must not be empty")
    from app.llm import handle_chat  # lazy: keeps the API importable without the LLM stack

    return await handle_chat(req.message, cache, source)


@router.get("/history")
def chat_history(limit: int = 50) -> dict:
    limit = max(1, min(limit, 500))
    return {"messages": db.get_chat_history(limit=limit)}
