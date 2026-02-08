# Changelog

## Unreleased

- Use Streamlit-native chat fallback by default (reliable, no JS bridge).
- Added `chatbot/ui/streamlit_chat.py` — simple sidebar chat UI using `StockAIAdvisor`.
- Implemented `ui/chatbot.py` `StockAIAdvisor` wrapper (selects Groq/Gemini/Mock).
- Improved JS bridge robustness (if floating orb is re-enabled).
- Removed `chatbot/ui/floating_orb.py` to reduce UI fragility and page lag.
- All tests pass: 20 passed, 1 skipped.

---

Notes:
- The floating orb can be reintroduced later if desired, but the Streamlit fallback
  is recommended for stability and easier debugging.
