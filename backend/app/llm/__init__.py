<<<<<<< HEAD
"""LLM chat integration: FinAlly AI assistant (LiteLLM -> OpenRouter -> Cerebras)."""

from .schemas import LLMResponse, TradeRequest, WatchlistChangeRequest
from .service import handle_chat

__all__ = ["LLMResponse", "TradeRequest", "WatchlistChangeRequest", "handle_chat"]
=======
"""LLM chat integration module.

Public API:
    process_chat_message - Core chat orchestrator
    create_chat_router   - FastAPI router factory for POST /api/chat
    ChatRequest          - Incoming chat request schema
    ChatResponse         - Outgoing chat response schema
"""

from .models import ChatRequest, ChatResponse
from .router import create_chat_router
from .service import process_chat_message

__all__ = [
    "process_chat_message",
    "create_chat_router",
    "ChatRequest",
    "ChatResponse",
]
>>>>>>> 4e94a35bae4b2c154c3398af2e05b336f98fdbde
