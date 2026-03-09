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
