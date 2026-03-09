"""Chat endpoint — Gemini (google.genai) with Groq fallback."""
import asyncio
import logging
from fastapi import APIRouter
import backend.app.state as state
from backend.app.models.types import ChatRequest
from backend.app.core.config import settings

# Detect library availability at import time so errors surface in startup logs
try:
    from google import genai as _genai
    _GEMINI_LIB_OK = True
except Exception:
    _genai = None  # type: ignore
    _GEMINI_LIB_OK = False

try:
    from groq import Groq as _Groq
    _GROQ_LIB_OK = True
except Exception:
    _Groq = None  # type: ignore
    _GROQ_LIB_OK = False

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger("api.chat")

# Log provider status once at module load (visible in Render logs)
_gemini_configured = bool(settings.GEMINI_API_KEY) and _GEMINI_LIB_OK
_groq_configured = bool(settings.GROQ_API_KEY) and _GROQ_LIB_OK
logger.info(
    "Chat providers: gemini=%s (lib=%s, key=%s) | groq=%s (lib=%s, key=%s)",
    _gemini_configured, _GEMINI_LIB_OK, bool(settings.GEMINI_API_KEY),
    _groq_configured, _GROQ_LIB_OK, bool(settings.GROQ_API_KEY),
)

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


async def _call_groq(user_text: str, model: str | None = None) -> str:
    if not _GROQ_LIB_OK or not _Groq:
        raise RuntimeError("groq library not available")
    client = _Groq(api_key=settings.GROQ_API_KEY)
    ctx = _build_context_snippet()
    full_user = f"{ctx}\n\nUSER: {user_text}"
    msgs = [{"role": "system", "content": _SYSTEM_PROMPT}] + _history[-16:] + [{"role": "user", "content": full_user}]
    model_name = model or settings.DEFAULT_MODEL_NAME or "llama-3.3-70b-versatile"

    def _sync_groq():
        resp = client.chat.completions.create(
            model=model_name,
            messages=msgs,
            temperature=0.7,
            max_tokens=400,
        )
        return (resp.choices[0].message.content or "").strip()

    return await asyncio.wait_for(asyncio.to_thread(_sync_groq), timeout=25.0)


async def _call_gemini(user_text: str) -> str:
    if not _GEMINI_LIB_OK or not _genai:
        raise RuntimeError("google-genai library not available")
    client = _genai.Client(api_key=settings.GEMINI_API_KEY)

    history_text = ""
    for turn in _history[-16:]:
        role = "User" if turn["role"] == "user" else "Assistant"
        history_text += f"{role}: {turn['content']}\n"

    ctx = _build_context_snippet()
    full_prompt = f"{_SYSTEM_PROMPT}\n\n{ctx}\n\n{history_text}User: {user_text}\nAssistant:"

    def _sync_gemini():
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=full_prompt,
        )
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Gemini returned empty response (safety filter or quota)")
        return text

    return await asyncio.wait_for(asyncio.to_thread(_sync_gemini), timeout=25.0)


@router.post("")
async def chat(req: ChatRequest):
    global _history

    user_text = _strip_frontend_context(req.message)

    answer = None
    errors: list[str] = []

    # ── 1. Groq (primary — matches DEFAULT_MODEL_PROVIDER=groq) ──────────────
    if _groq_configured:
        # Try the configured model first, fall back to the fast lightweight one
        for groq_model in [settings.DEFAULT_MODEL_NAME or "llama-3.3-70b-versatile",
                            "llama-3.1-8b-instant"]:
            try:
                answer = await _call_groq(user_text, model=groq_model)
                if answer:
                    break
            except Exception as e:
                err = f"Groq/{groq_model} ({type(e).__name__}: {e})"
                logger.warning(err)
                errors.append(err)

    # ── 2. Gemini fallback ───────────────────────────────────────────────────
    if not answer and _gemini_configured:
        try:
            answer = await _call_gemini(user_text)
        except Exception as e:
            err = f"Gemini ({type(e).__name__}: {e})"
            logger.warning(err)
            errors.append(err)

    if not answer:
        if not _groq_configured and not _gemini_configured:
            msg = ("Chat is not configured — no LLM API keys found. "
                   "Set GROQ_API_KEY or GEMINI_API_KEY in your Render environment variables.")
        else:
            logger.error("All chat providers failed: %s", " | ".join(errors))
            msg = "Chat is temporarily unavailable. Please try again in a moment."
        return {
            "response": msg,
            "confidence": "low",
            "suggested_followup": None,
        }

    # Update history
    _history.append({"role": "user", "content": user_text})
    _history.append({"role": "assistant", "content": answer})
    if len(_history) > 20:
        _history = _history[-20:]

    return {"response": answer, "confidence": "high", "suggested_followup": None}
