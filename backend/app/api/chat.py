"""Chat endpoint — Gemini (google.genai) with Groq fallback."""
import logging
from fastapi import APIRouter
import backend.app.state as state
from backend.app.models.types import ChatRequest
from backend.app.core.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger("api.chat")

_SYSTEM_PROMPT = (
    "You are StockAI's market advisor — an expert AI assistant embedded in a simulated "
    "stock market. You have access to live simulation data (provided in user messages). "
    "Answer concisely (2-4 sentences). Be analytical, data-driven, and helpful."
)

# Rolling conversation history (last 10 turns)
_history: list = []


def _build_context_snippet() -> str:
    try:
        sim = state.simulation
        prices = {
            s: round(state.market_books[s].last_price or state.STOCKS[s].initial_price, 2)
            for s in state.STOCKS
        }
        agents_active = sum(1 for a in state.agents if a.status == "active")
        top = max(prices, key=lambda s: (
            (prices[s] - state.STOCKS[s].initial_price) / state.STOCKS[s].initial_price
        ))
        return (
            f"[Day {sim.day}/{sim.total_days}, "
            f"running={sim.is_running}, trades={sim.total_trade_count}, "
            f"agents={agents_active}, top mover={state.STOCKS[top].name} @ ${prices[top]}]"
        )
    except Exception:
        return "[Simulation not started]"


def _strip_frontend_context(msg: str) -> str:
    """Remove the [Context: ...] block the frontend sometimes appends."""
    if "[Context:" in msg:
        return msg[:msg.index("[Context:")].strip()
    return msg


async def _call_gemini(user_text: str) -> str:
    from google import genai
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    # Build full conversation as a flat prompt (genai SDK stateless approach)
    history_text = ""
    for turn in _history[-16:]:  # last 8 exchanges
        role = "User" if turn["role"] == "user" else "Assistant"
        history_text += f"{role}: {turn['content']}\n"

    ctx = _build_context_snippet()
    full_prompt = f"{_SYSTEM_PROMPT}\n\n{ctx}\n\n{history_text}User: {user_text}\nAssistant:"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=full_prompt,
    )
    return (response.text or "").strip()


async def _call_groq(user_text: str) -> str:
    from groq import Groq
    client = Groq(api_key=settings.GROQ_API_KEY)
    ctx = _build_context_snippet()
    full_user = f"{ctx}\n\nUSER: {user_text}"
    msgs = [{"role": "system", "content": _SYSTEM_PROMPT}] + _history[-16:] + [{"role": "user", "content": full_user}]
    resp = client.chat.completions.create(
        model=settings.DEFAULT_MODEL_NAME or "llama-3.3-70b-versatile",
        messages=msgs,
        temperature=0.7,
        max_tokens=400,
    )
    return (resp.choices[0].message.content or "").strip()


@router.post("")
async def chat(req: ChatRequest):
    global _history

    user_text = _strip_frontend_context(req.message)

    answer = None
    # Try Gemini first
    if settings.GEMINI_API_KEY:
        try:
            answer = await _call_gemini(user_text)
        except Exception as e:
            logger.warning(f"Gemini failed, trying Groq fallback: {e}")

    # Fallback to Groq
    if not answer and settings.GROQ_API_KEY:
        try:
            answer = await _call_groq(user_text)
        except Exception as e:
            logger.error(f"Groq chat error: {e}")

    if not answer:
        return {
            "response": "Chat is temporarily unavailable. Please try again in a moment.",
            "confidence": "low",
            "suggested_followup": None,
        }

    # Update history
    _history.append({"role": "user", "content": user_text})
    _history.append({"role": "assistant", "content": answer})
    if len(_history) > 20:
        _history = _history[-20:]

    return {"response": answer, "confidence": "high", "suggested_followup": None}

_SYSTEM_PROMPT = (
    "You are StockAI's market advisor — an expert AI assistant embedded in a simulated "
    "stock market. You have access to live simulation data (provided in user messages). "
    "Answer concisely (2-4 sentences). Be analytical, data-driven, and helpful. "
    "If asked about stocks, agents, trades, or market events, use the provided context. "
    "If no simulation is running yet, offer general guidance."
)

# Simple in-memory conversation history (per-process, not per-session — fine for single-user demo)
_history: list = []


def _build_context_snippet() -> str:
    """Pull live sim data into a compact context string."""
    try:
        sim = state.simulation
        prices = {
            s: round(state.market_books[s].last_price or state.STOCKS[s].initial_price, 2)
            for s in state.STOCKS
        }
        agents_active = sum(1 for a in state.agents if a.status == "active")
        top = max(prices, key=lambda s: (
            (prices[s] - state.STOCKS[s].initial_price) / state.STOCKS[s].initial_price
        ))
        return (
            f"[Sim context — Day {sim.day}/{sim.total_days}, "
            f"running={sim.is_running}, trades={sim.total_trade_count}, "
            f"agents={agents_active}, top mover={state.STOCKS[top].name} "
            f"@ ${prices[top]}]"
        )
    except Exception:
        return "[Simulation not started]"


@router.post("")
async def chat(req: ChatRequest):
    global _history

    if not settings.GROQ_API_KEY:
        return {
            "response": "Chat is unavailable — GROQ_API_KEY is not configured.",
            "confidence": "low",
            "suggested_followup": None,
        }

    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
    except Exception as e:
        logger.error(f"Groq client init failed: {e}")
        return {
            "response": "Chat service is temporarily unavailable.",
            "confidence": "low",
            "suggested_followup": None,
        }

    # Append live context to user message
    ctx = _build_context_snippet()
    user_text = req.message
    # Strip stale [Context: ...] appended by the frontend
    if "[Context:" in user_text:
        user_text = user_text[:user_text.index("[Context:")].strip()
    full_user = f"{ctx}\n\nUSER: {user_text}"

    # Keep last 10 turns to stay within token limits
    _history.append({"role": "user", "content": full_user})
    if len(_history) > 20:
        _history = _history[-20:]

    messages = [{"role": "system", "content": _SYSTEM_PROMPT}] + _history

    try:
        resp = client.chat.completions.create(
            model=settings.DEFAULT_MODEL_NAME or "llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=400,
        )
        answer = resp.choices[0].message.content or "No response generated."
        _history.append({"role": "assistant", "content": answer})
        if len(_history) > 20:
            _history = _history[-20:]
        return {
            "response": answer,
            "confidence": "high",
            "suggested_followup": None,
        }
    except Exception as e:
        logger.error(f"Groq chat error: {e}")
        err = str(e).lower()
        if "rate" in err or "429" in err:
            msg = "Rate limit reached — please wait a moment before asking again."
        else:
            msg = "Sorry, I encountered an error. Please try again."
        return {"response": msg, "confidence": "low", "suggested_followup": None}
