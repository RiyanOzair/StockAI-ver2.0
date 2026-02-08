"""Streamlit-native chatbot UI fallback.

Provides a simple, robust chat UI using Streamlit widgets (no JS bridge).
Intended as a fallback when the floating orb causes issues or for debugging.
"""
import streamlit as st
from typing import Optional, Any
from ..ui import chatbot as ui_chatbot
import os
from datetime import datetime

# Ensure log directory exists
_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'log')
_LOG_DIR = os.path.abspath(_LOG_DIR)
os.makedirs(_LOG_DIR, exist_ok=True)
_LOG_FILE = os.path.join(_LOG_DIR, 'chat_ui.log')


def _log_entry(role: str, text: str) -> None:
    try:
        ts = datetime.utcnow().isoformat() + 'Z'
        with open(_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{ts} | {role.upper()} | {text.replace('\n',' ')}\n")
    except Exception:
        pass


def render_streamlit_chat(app_context: Optional[Any] = None, config: Optional[Any] = None) -> None:
    """Render a simple chat box that uses `StockAIAdvisor` under the hood.

    - Keeps messages in `st.session_state['streamlit_chat_messages']`.
    - Uses `StockAIAdvisor.ask()` to get replies synchronously.
    """
    if "streamlit_chat_messages" not in st.session_state:
        st.session_state.streamlit_chat_messages = [
            {
                "role": "assistant",
                "content": "Hello — I am StockAI. Ask me about the market or the simulation.",
            }
        ]

    advisor = None
    try:
        advisor = ui_chatbot.StockAIAdvisor()
    except Exception:
        advisor = None

    st.sidebar.markdown("### Chat (Fallback)")
    chat_box = st.sidebar.container()

    with chat_box:
        for m in st.session_state.streamlit_chat_messages:
            if m["role"] == "assistant":
                st.markdown(f"**Assistant:** {m['content']}")
            else:
                st.markdown(f"**You:** {m['content']}")

        user_input = st.text_input("Message", key="streamlit_chat_input")
        if st.button("Send", key="streamlit_chat_send") and user_input and user_input.strip():
            text = user_input.strip()
            st.session_state.streamlit_chat_messages.append({"role": "user", "content": text})
            _log_entry('user', text)
            # get reply
            try:
                if advisor:
                    reply = advisor.ask(text, context=str(app_context) if app_context else "")
                else:
                    reply = "Chat advisor not available."
            except Exception as e:
                reply = f"Error: {e}"
            st.session_state.streamlit_chat_messages.append({"role": "assistant", "content": reply})
            _log_entry('assistant', reply)
            # clear input
            st.session_state.streamlit_chat_input = ""
