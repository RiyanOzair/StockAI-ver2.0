"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         StockAI - Market Simulation Lab                      ║
║              Agent-Based Trading Simulation with Behavioral Finance          ║
║                         Production-Ready Version 2.0                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
import time
import pandas as pd
import numpy as np
import json
import os

# Import simulation engine
from simulation_engine import (
    get_engine, reset_engine, SimulationEngine, 
    SimulationState, AgentState, MarketEvent,
    PRIMARY_STOCKS, STOCK_UNIVERSE, get_all_stocks, get_stock_sectors, get_stocks_by_sector
)

# Import additional styles  
from styles import get_all_styles, STOCK_CARD_STYLES, NEWS_TICKER_STYLES, FLOATING_ORB_STYLES

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="StockAI — Market Simulation Lab",
    page_icon="ui/favicon.svg",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════

if "engine" not in st.session_state:
    st.session_state.engine = get_engine()
if "app_started" not in st.session_state:
    st.session_state.app_started = False
if "show_guidelines" not in st.session_state:
    st.session_state.show_guidelines = False
if "show_credits" not in st.session_state:
    st.session_state.show_credits = False
if "auto_run" not in st.session_state:
    st.session_state.auto_run = False
if "sim_speed" not in st.session_state:
    st.session_state.sim_speed = "Normal"
if "custom_agent" not in st.session_state:
    st.session_state.custom_agent = {
        "enabled": False,
        "name": "",
        "nickname": "",
        "display_name": "",
        "character": "Balanced",
        "herding_level": "Medium",
        "loss_aversion_level": "Medium",
        "overconfidence_level": "Low",
        "anchoring_level": "Medium",
    }
if "custom_agent_avatar" not in st.session_state:
    st.session_state.custom_agent_avatar = None
if "manual_events" not in st.session_state:
    st.session_state.manual_events = []
if "custom_agent_loaded" not in st.session_state:
    st.session_state.custom_agent_loaded = False

# ═══════════════════════════════════════════════════════════════════════════════
# PERSISTENCE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

PROFILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "res", "custom_agent_profile.json")

def load_custom_agent_profile():
    if st.session_state.custom_agent_loaded:
        return
    try:
        if os.path.exists(PROFILE_PATH):
            with open(PROFILE_PATH, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if isinstance(payload, dict):
                st.session_state.custom_agent.update(payload)
    except Exception:
        pass
    st.session_state.custom_agent_loaded = True

def save_custom_agent_profile():
    try:
        os.makedirs(os.path.dirname(PROFILE_PATH), exist_ok=True)
        with open(PROFILE_PATH, "w", encoding="utf-8") as f:
            json.dump(st.session_state.custom_agent, f, indent=2)
    except Exception:
        pass

load_custom_agent_profile()

engine: SimulationEngine = st.session_state.engine

# ═══════════════════════════════════════════════════════════════════════════════
# PRODUCTION CSS - Premium Dark Theme with Glassmorphism
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
/* ═══════════════════════════════════════════════════════════════════════════════
   IMPORTS & FONTS
   ═══════════════════════════════════════════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ═══════════════════════════════════════════════════════════════════════════════
   CSS VARIABLES
   ═══════════════════════════════════════════════════════════════════════════════ */
:root {
    /* Backgrounds */
    --bg-primary: #000000;
    --bg-secondary: #0f0f0f;
    --bg-tertiary: #1a1a1a;
    --bg-card: #121212;
    --bg-card-solid: #141414;
    --bg-card-hover: #1e1e1e;
    --bg-glass: rgba(255, 255, 255, 0.06);
    
    /* Text */
    --text-primary: #ffffff;
    --text-secondary: #b4b4b4;
    --text-muted: #8a8a8a;
    --text-dim: #666666;
    
    /* Accent Colors */
    --accent-green: #26a69a;
    --accent-green-dim: rgba(38, 166, 154, 0.15);
    --accent-red: #ef5350;
    --accent-red-dim: rgba(239, 83, 80, 0.15);
    --accent-blue: #2962ff;
    --accent-blue-dim: rgba(41, 98, 255, 0.15);
    --accent-purple: #7c3aed;
    --accent-purple-dim: rgba(124, 58, 237, 0.15);
    --accent-yellow: #ffa726;
    --accent-yellow-dim: rgba(255, 167, 38, 0.15);
    --accent-cyan: #26c6da;
    --accent-pink: #ec407a;
    
    /* Gradients */
    --gradient-primary: linear-gradient(135deg, #26a69a 0%, #2962ff 100%);
    --gradient-green: linear-gradient(135deg, #26a69a 0%, #1f8b7e 100%);
    --gradient-blue: linear-gradient(135deg, #2962ff 0%, #1e4fc2 100%);
    --gradient-purple: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%);
    --gradient-warm: linear-gradient(135deg, #ffa726 0%, #ef5350 100%);
    --gradient-dark: linear-gradient(180deg, #000000 0%, #0a0a0a 100%);
    
    /* Borders */
    --border-subtle: rgba(255, 255, 255, 0.1);
    --border-light: rgba(255, 255, 255, 0.15);
    --border-medium: rgba(255, 255, 255, 0.22);
    
    /* Shadows */
    --shadow-sm: 0 2px 4px rgba(0, 0, 0, 0.4), 0 0 1px rgba(255, 255, 255, 0.05);
    --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.5), 0 0 2px rgba(255, 255, 255, 0.08);
    --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.6), 0 0 3px rgba(255, 255, 255, 0.1);
    --shadow-glow-green: 0 0 16px rgba(38, 166, 154, 0.3), 0 0 32px rgba(38, 166, 154, 0.15);
    --shadow-glow-blue: 0 0 16px rgba(41, 98, 255, 0.3), 0 0 32px rgba(41, 98, 255, 0.15);
    --shadow-glow-purple: 0 0 16px rgba(124, 58, 237, 0.3), 0 0 32px rgba(124, 58, 237, 0.15);
    
    /* Spacing */
    --radius-sm: 6px;
    --radius-md: 8px;
    --radius-lg: 8px;
    --radius-xl: 12px;
    --radius-full: 9999px;
}

/* ═══════════════════════════════════════════════════════════════════════════════
   GLOBAL STYLES
   ═══════════════════════════════════════════════════════════════════════════════ */
* {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

code, pre, .monospace {
    font-family: 'JetBrains Mono', monospace !important;
}

/* Hide Streamlit defaults */
#MainMenu, footer, header, .stDeployButton {
    display: none !important;
}

/* Main app background */
.stApp {
    background: var(--gradient-dark);
}

/* Block container */
.block-container {
    padding: 1.5rem 2rem !important;
    max-width: 100% !important;
}

/* ═══════════════════════════════════════════════════════════════════════════════
   GLASSMORPHISM CARDS
   ═══════════════════════════════════════════════════════════════════════════════ */
.glass-card {
    background: var(--bg-card);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 24px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.glass-card:hover {
    background: var(--bg-card-hover);
    border-color: var(--border-light);
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
}

/* ═══════════════════════════════════════════════════════════════════════════════
   METRIC CARDS - Premium Style
   ═══════════════════════════════════════════════════════════════════════════════ */
.metric-card {
    background: var(--bg-card-solid);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 24px;
    text-align: center;
    position: relative;
    overflow: hidden;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    min-height: 180px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    transform-style: preserve-3d;
}

.metric-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: var(--border-medium);
    opacity: 0;
    transition: opacity 0.2s ease;
}

.metric-card:hover {
    transform: perspective(800px) rotateY(2deg) rotateX(-2deg) translateY(-4px);
    border-color: var(--border-light);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5), 0 0 20px rgba(41, 98, 255, 0.15);
}

.metric-card:hover::before {
    opacity: 1;
}

.metric-icon {
    /* Reduced emoji/icon size for a more professional look */
    font-size: clamp(16px, 3.2vw, 28px);
    margin-bottom: 8px;
    display: block;
    line-height: 1;
}

.metric-value {
    font-size: clamp(28px, 6vw, 56px);
    font-weight: 800;
    letter-spacing: -1px;
    margin-bottom: 4px;
    line-height: 1.1;
}

.metric-label {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 1.5px;
}

.metric-change {
    font-size: 12px;
    font-weight: 600;
    margin-top: 8px;
    padding: 4px 10px;
    border-radius: var(--radius-full);
    display: inline-block;
}

.metric-green { color: var(--accent-green); }
.metric-red { color: var(--accent-red); }
.metric-blue { color: var(--accent-blue); }
.metric-purple { color: var(--accent-purple); }
.metric-yellow { color: var(--accent-yellow); }
.metric-cyan { color: var(--accent-cyan); }

/* ═══════════════════════════════════════════════════════════════════════════════
   HEADER & NAVIGATION
   ═══════════════════════════════════════════════════════════════════════════════ */

/* Header container - targets the first element block */
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"]:first-child {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xl);
    padding: 16px 24px;
    margin-bottom: 20px;
}

.header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
}

.brand {
    display: flex;
    align-items: center;
    gap: 14px;
}

.brand-icon {
    width: 44px;
    height: 44px;
    background: var(--accent-blue);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: var(--shadow-sm);
}

.brand-icon svg {
    width: 28px;
    height: 28px;
}

.brand-text h1 {
    margin: 0 0 -2px 0;
    font-size: clamp(26px, 5.5vw, 36px);
    font-weight: 800;
    color: var(--text-primary);
    line-height: 1;
}

.brand-text p {
    margin: -8px 0 0 0;
    font-size: 12px;
    color: var(--text-muted);
    font-weight: 500;
    letter-spacing: 0.3px;
}

/* Status Badge */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 20px;
    border-radius: var(--radius-full);
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.5px;
}

.header-status {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    justify-content: center;
    gap: 6px;
}

.header-guidelines-btn {
    background: var(--bg-tertiary);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 10px 18px;
    color: var(--text-secondary);
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    gap: 8px;
}

.header-guidelines-btn:hover {
    background: var(--bg-card);
    border-color: var(--accent-blue);
    color: var(--text-primary);
}

.status-idle { background: rgba(113, 113, 122, 0.2); color: #a1a1aa; }
.status-configured { background: var(--accent-blue-dim); color: #60a5fa; }
.status-running { background: var(--accent-green-dim); color: #34d399; animation: pulse 2s infinite; }
.status-paused { background: var(--accent-yellow-dim); color: #fbbf24; }
.status-completed { background: var(--accent-purple-dim); color: #a78bfa; }

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

/* ═══════════════════════════════════════════════════════════════════════════════
   TABS - Premium Style
   ═══════════════════════════════════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: var(--bg-card);
    padding: 6px;
    border-radius: var(--radius-lg);
    border: 1px solid var(--border-subtle);
}

.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: var(--radius-md);
    padding: 12px 24px;
    color: var(--text-secondary);
    font-weight: 600;
    font-size: 14px;
    transition: all 0.2s ease;
    border-bottom: 2px solid transparent;
}

.stTabs [data-baseweb="tab"]:hover {
    background: var(--bg-glass);
    color: var(--text-primary);
}

.stTabs [aria-selected="true"] {
    background: var(--bg-card) !important;
    color: var(--accent-blue) !important;
    border-bottom: 2px solid var(--accent-blue) !important;
    box-shadow: none;
}

.stTabs [data-baseweb="tab-panel"] {
    padding-top: 28px;
}

.stTabs [data-baseweb="tab-highlight"] {
    display: none;
}

.stTabs [data-baseweb="tab-border"] {
    display: none;
}

/* ═══════════════════════════════════════════════════════════════════════════════
   BUTTONS
   ═══════════════════════════════════════════════════════════════════════════════ */
.stButton > button {
    background: var(--accent-green);
    color: white;
    border: none;
    border-radius: var(--radius-md);
    padding: 12px 24px;
    font-weight: 600;
    font-size: 14px;
    letter-spacing: 0.3px;
    transition: all 0.2s ease;
    box-shadow: var(--shadow-sm);
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4), 0 0 20px rgba(38, 166, 154, 0.4);
    background: #1f8b7e;
}

.stButton > button[type="primary"] {
    box-shadow: 0 0 15px rgba(38, 166, 154, 0.3), var(--shadow-sm);
    animation: pulse 2s ease-in-out infinite;
}

.stButton > button:active {
    transform: translateY(0);
}

/* Secondary button */
.stButton > button[kind="secondary"] {
    background: var(--bg-card);
    border: 1px solid var(--border-light);
    color: var(--text-primary);
}

.stButton > button[kind="secondary"]:hover {
    background: var(--bg-card-hover);
    border-color: var(--border-medium);
    box-shadow: var(--shadow-md);
    transform: translateY(-1px);
}

/* ═══════════════════════════════════════════════════════════════════════════════
   FORM ELEMENTS
   ═══════════════════════════════════════════════════════════════════════════════ */
/* Slider styling - clean track without background colors */
.stSlider > div > div > div {
    background: transparent !important;
}

.stSlider [data-baseweb="slider"] {
    padding: 12px 0;
}

.stSlider [data-baseweb="slider"] > div {
    background: transparent !important;
}

.stSlider [data-baseweb="slider"] [data-testid="stTickBar"] {
    background: rgba(255, 255, 255, 0.1) !important;
}

.stSlider [data-baseweb="slider"] div[role="slider"] {
    background: var(--accent-green) !important;
    border: none !important;
}

.stSlider [data-testid="stThumbValue"] {
    background: transparent !important;
}

.stSelectbox > div > div,
.stMultiSelect > div > div {
    background: var(--bg-card-solid) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
}

.stSelectbox > div > div:hover,
.stMultiSelect > div > div:hover {
    border-color: var(--border-light) !important;
}

.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    background: var(--bg-card-solid) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
}

.stToggle > label > div {
    background: var(--bg-tertiary) !important;
}

/* ═══════════════════════════════════════════════════════════════════════════════
   INFO CARDS & SECTIONS
   ═══════════════════════════════════════════════════════════════════════════════ */
.info-card {
    background: var(--bg-card);
    backdrop-filter: blur(20px);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 16px 20px;
    margin-bottom: 12px;
}

.info-card h4 {
    margin: 0 0 8px 0;
    font-size: 14px;
    font-weight: 700;
    color: var(--text-primary);
    display: flex;
    align-items: center;
    gap: 8px;
}

.info-card p {
    margin: 4px 0;
    color: var(--text-secondary);
    font-size: 13px;
    line-height: 1.6;
}

.info-card strong {
    color: var(--text-primary);
    font-weight: 600;
}

.section-title {
    font-size: 20px;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 10px;
}

.section-subtitle {
    font-size: 14px;
    color: var(--text-muted);
    margin-top: -12px;
    margin-bottom: 20px;
}

/* ═══════════════════════════════════════════════════════════════════════════════
   BBS FORUM MESSAGES
   ═══════════════════════════════════════════════════════════════════════════════ */
.bbs-message {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 16px 20px;
    margin-bottom: 12px;
    transition: all 0.2s ease;
}

.bbs-message:hover {
    background: var(--bg-card-hover);
    border-color: var(--border-light);
}

.bbs-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}

.bbs-agent {
    font-weight: 700;
    font-size: 14px;
    color: var(--accent-blue);
}

.bbs-meta {
    display: flex;
    align-items: center;
    gap: 12px;
}

.bbs-day {
    font-size: 12px;
    color: var(--text-dim);
    font-weight: 500;
}

.bbs-sentiment {
    font-size: 11px;
    padding: 3px 10px;
    border-radius: var(--radius-full);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.bbs-content {
    color: var(--text-secondary);
    font-size: 14px;
    line-height: 1.6;
}

.bbs-bullish { border-left: 3px solid var(--accent-green); }
.bbs-bullish .bbs-sentiment { background: var(--accent-green-dim); color: var(--accent-green); }

.bbs-bearish { border-left: 3px solid var(--accent-red); }
.bbs-bearish .bbs-sentiment { background: var(--accent-red-dim); color: var(--accent-red); }

.bbs-neutral { border-left: 3px solid var(--text-dim); }
.bbs-neutral .bbs-sentiment { background: rgba(113, 113, 122, 0.2); color: var(--text-muted); }

/* ═══════════════════════════════════════════════════════════════════════════════
   AGENT CARDS & RANKINGS
   ═══════════════════════════════════════════════════════════════════════════════ */
.agent-row {
    display: flex;
    align-items: center;
    padding: 16px 20px;
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    margin-bottom: 10px;
    transition: all 0.2s ease;
}

.agent-row:hover {
    background: var(--bg-card-hover);
    border-color: var(--accent-blue);
    transform: translateX(4px);
}

.agent-rank {
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    font-weight: 800;
    margin-right: 16px;
}

.agent-info {
    flex: 1;
}

.agent-name {
    font-size: 15px;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 2px;
}

.agent-strategy {
    font-size: 12px;
    color: var(--text-muted);
    font-weight: 500;
}

.agent-pnl {
    text-align: right;
}

.agent-pnl-value {
    font-size: 18px;
    font-weight: 800;
}

.agent-pnl-total {
    font-size: 12px;
    color: var(--text-muted);
}

/* ═══════════════════════════════════════════════════════════════════════════════
   EVENT CARDS
   ═══════════════════════════════════════════════════════════════════════════════ */
.event-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 16px 20px;
    margin-bottom: 12px;
}

.event-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 8px;
}

.event-title {
    font-size: 15px;
    font-weight: 700;
    color: var(--text-primary);
}

.event-severity {
    font-size: 11px;
    padding: 4px 12px;
    border-radius: var(--radius-full);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.event-description {
    color: var(--text-secondary);
    font-size: 13px;
    line-height: 1.6;
}

.event-high { border-left: 3px solid var(--accent-red); }
.event-high .event-severity { background: var(--accent-red-dim); color: var(--accent-red); }

.event-medium { border-left: 3px solid var(--accent-yellow); }
.event-medium .event-severity { background: var(--accent-yellow-dim); color: var(--accent-yellow); }

.event-low { border-left: 3px solid var(--accent-green); }
.event-low .event-severity { background: var(--accent-green-dim); color: var(--accent-green); }

/* ═══════════════════════════════════════════════════════════════════════════════
   PROGRESS BARS
   ═══════════════════════════════════════════════════════════════════════════════ */
.progress-container {
    background: rgba(255, 255, 255, 0.08);
    border-radius: var(--radius-full);
    height: 10px;
    overflow: hidden;
    position: relative;
}

.progress-bar {
    height: 100%;
    background: var(--gradient-primary);
    border-radius: var(--radius-full);
    transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
}

.progress-bar::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.3) 50%, transparent 100%);
    animation: shimmer 2s infinite;
}

@keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}

/* ═══════════════════════════════════════════════════════════════════════════════
   LANDING PAGE STYLES
   ═══════════════════════════════════════════════════════════════════════════════ */
.landing-container {
    min-height: auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    text-align: center;
    padding: 20px 20px 10px 20px;
}

.landing-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 24px;
    background: var(--bg-card);
    border: 1px solid var(--accent-green);
    border-radius: var(--radius-full);
    font-size: 13px;
    font-weight: 600;
    color: var(--accent-green);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 12px;
}

.landing-title {
    font-size: 7.5rem !important;
    font-weight: 900 !important;
    letter-spacing: -0.04em !important;
    background: var(--gradient-primary);
    background-size: 200% 200%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 6px;
    line-height: 0.85;
    animation: gradientShift 4s ease infinite;
}
    margin-bottom: 6px;
    line-height: 0.85;
    animation: gradientShift 4s ease infinite;
}

.landing-subtitle {
    font-size: 24px;
    font-weight: 600;
    color: var(--text-secondary);
    margin-bottom: 8px;
}

.landing-description {
    font-size: 14px;
    color: var(--text-muted);
    max-width: 580px;
    line-height: 1.6;
    margin-bottom: 12px;
}

.feature-grid {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 12px;
    margin-bottom: 20px;
    max-width: 820px;
}

.feature-grid .feature-badge {
    flex: 0 0 auto;
}

.feature-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 14px 28px;
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-left: 3px solid var(--accent-blue);
    border-radius: var(--radius-md);
    font-size: 14px;
    font-weight: 600;
    color: var(--text-secondary);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    cursor: default;
}

.feature-badge:nth-child(1) { border-left-color: var(--accent-green); color: var(--accent-green); }
.feature-badge:nth-child(2) { border-left-color: var(--accent-blue); color: var(--accent-blue); }
.feature-badge:nth-child(3) { border-left-color: var(--accent-purple); color: var(--accent-purple); }
.feature-badge:nth-child(4) { border-left-color: var(--accent-cyan); color: var(--accent-cyan); }
.feature-badge:nth-child(5) { border-left-color: var(--accent-yellow); color: var(--accent-yellow); }
.feature-badge:nth-child(6) { border-left-color: var(--accent-pink); color: var(--accent-pink); }

.feature-badge:nth-child(1):hover { 
    background: rgba(16, 185, 129, 0.1);
    border-color: var(--accent-green);
    box-shadow: 0 0 25px rgba(16, 185, 129, 0.4), 0 0 50px rgba(16, 185, 129, 0.2);
    transform: translateY(-4px) scale(1.02);
}
.feature-badge:nth-child(2):hover { 
    background: rgba(59, 130, 246, 0.1);
    border-color: var(--accent-blue);
    box-shadow: 0 0 25px rgba(59, 130, 246, 0.4), 0 0 50px rgba(59, 130, 246, 0.2);
    transform: translateY(-4px) scale(1.02);
}
.feature-badge:nth-child(3):hover { 
    background: rgba(139, 92, 246, 0.1);
    border-color: var(--accent-purple);
    box-shadow: 0 0 25px rgba(139, 92, 246, 0.4), 0 0 50px rgba(139, 92, 246, 0.2);
    transform: translateY(-4px) scale(1.02);
}
.feature-badge:nth-child(4):hover { 
    background: rgba(6, 182, 212, 0.1);
    border-color: var(--accent-cyan);
    box-shadow: 0 0 25px rgba(6, 182, 212, 0.4), 0 0 50px rgba(6, 182, 212, 0.2);
    transform: translateY(-4px) scale(1.02);
}
.feature-badge:nth-child(5):hover { 
    background: rgba(245, 158, 11, 0.1);
    border-color: var(--accent-yellow);
    box-shadow: 0 0 25px rgba(245, 158, 11, 0.4), 0 0 50px rgba(245, 158, 11, 0.2);
    transform: translateY(-4px) scale(1.02);
}
.feature-badge:nth-child(6):hover { 
    background: rgba(236, 72, 153, 0.1);
    border-color: var(--accent-pink);
    box-shadow: 0 0 25px rgba(236, 72, 153, 0.4), 0 0 50px rgba(236, 72, 153, 0.2);
    transform: translateY(-4px) scale(1.02);
}

.tech-stack {
    display: flex;
    justify-content: center;
    gap: 24px;
    margin-top: 48px;
    padding-top: 32px;
    border-top: 1px solid var(--border-subtle);
}

.tech-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    color: var(--text-dim);
    font-size: 12px;
    font-weight: 500;
}

.tech-item span {
    font-size: 24px;
}

/* ═══════════════════════════════════════════════════════════════════════════════
   GUIDELINES PAGE
   ═══════════════════════════════════════════════════════════════════════════════ */
.guidelines-hero {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xl);
    padding: 40px 48px;
    text-align: center;
    margin-bottom: 24px;
    display: flex;
    flex-direction: column;
    align-items: center;
}

.guidelines-title {
    font-size: 36px;
    font-weight: 800;
    color: var(--text-primary);
    margin-bottom: 12px;
    text-align: center;
}

.guidelines-subtitle {
    font-size: 15px;
    color: var(--text-muted);
    max-width: 600px;
    margin: 0 auto;
    line-height: 1.6;
    text-align: center !important;
    display: block;
}

.guidelines-section-title {
    font-size: 16px;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 16px 0 !important;
    padding-bottom: 0;
    border-bottom: none;
}

.guidelines-section-title.key-features {
    margin-top: 32px !important;
}

.step-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 20px 24px;
    margin-bottom: 14px;
    display: flex;
    gap: 18px;
    align-items: flex-start;
    transition: all 0.2s ease;
}

.step-card:hover {
    border-color: var(--border-light);
    transform: translateX(4px);
}

.step-number {
    width: 42px;
    height: 42px;
    min-width: 42px;
    background: var(--gradient-primary);
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: 800;
    color: white;
    flex-shrink: 0;
}

.step-content h4 {
    margin: 0 0 6px 0;
    font-size: 15px;
    font-weight: 700;
    color: var(--text-primary);
}

.step-content p {
    margin: 0;
    font-size: 14px;
    color: var(--text-secondary);
    line-height: 1.6;
}

/* Guidelines Strategy Card */
.strategy-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 20px 24px;
    margin-bottom: 14px;
    min-height: 90px;
    border-left: 3px solid var(--accent-green);
    transition: all 0.2s ease;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.strategy-card:hover {
    border-color: var(--border-light);
    transform: translateX(4px);
}

.strategy-card.conservative { border-left-color: #10b981; }
.strategy-card.aggressive { border-left-color: #ef4444; }
.strategy-card.balanced { border-left-color: #3b82f6; }
.strategy-card.growth { border-left-color: #8b5cf6; }

.strategy-card h4 {
    margin: 0 0 8px 0;
    font-size: 15px;
    font-weight: 700;
    color: var(--text-primary);
}

.strategy-card p {
    margin: 0;
    font-size: 14px;
    color: var(--text-secondary);
    line-height: 1.6;
}

/* Guidelines Bias Card */
.bias-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 20px 16px;
    text-align: center;
    min-height: 160px;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    align-items: center;
    transition: all 0.2s ease;
}

.bias-card:hover {
    border-color: var(--border-light);
    transform: translateY(-2px);
}

.bias-card.herding { border-top: 3px solid #8b5cf6; }
.bias-card.loss-aversion { border-top: 3px solid #ef4444; }
.bias-card.overconfidence { border-top: 3px solid #f59e0b; }
.bias-card.anchoring { border-top: 3px solid #3b82f6; }

.bias-card .bias-icon {
    font-size: 20px;
    margin-right: 6px;
}

.bias-card h4 {
    margin: 0 0 12px 0;
    font-size: 15px;
    font-weight: 700;
    color: var(--text-primary);
    display: flex;
    align-items: center;
    justify-content: center;
}

.bias-card p {
    margin: 0;
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.5;
}

/* Guidelines Feature Card */
.feature-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 18px 20px;
    margin-bottom: 14px;
    min-height: 110px;
    transition: all 0.2s ease;
}

.feature-card:hover {
    border-color: var(--border-light);
}

.feature-card.charts { border-left: 3px solid #10b981; }
.feature-card.forum { border-left: 3px solid #06b6d4; }
.feature-card.events { border-left: 3px solid #f59e0b; }
.feature-card.leaderboard { border-left: 3px solid #ec4899; }
.feature-card.analysis { border-left: 3px solid #8b5cf6; }
.feature-card.export { border-left: 3px solid #3b82f6; }

.feature-card h4 {
    margin: 0 0 8px 0;
    font-size: 14px;
    font-weight: 700;
    color: var(--text-primary);
}

.feature-card p {
    margin: 0;
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.5;
}

/* ═══════════════════════════════════════════════════════════════════════════════
   EMPTY STATES
   ═══════════════════════════════════════════════════════════════════════════════ */
.empty-state {
    text-align: center;
    padding: 60px 20px;
    color: var(--text-muted);
}

.empty-state-icon {
    font-size: 64px;
    margin-bottom: 16px;
    opacity: 0.5;
}

.empty-state-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-secondary);
    margin-bottom: 8px;
}

.empty-state-description {
    font-size: 14px;
    color: var(--text-muted);
}

/* ═══════════════════════════════════════════════════════════════════════════════
   FOOTER
   ═══════════════════════════════════════════════════════════════════════════════ */
.app-footer {
    text-align: center;
    padding: 32px 20px;
    margin-top: 48px;
    border-top: 1px solid var(--border-subtle);
}

.footer-brand {
    font-size: 16px;
    font-weight: 700;
    color: var(--text-secondary);
    margin-bottom: 8px;
}

.footer-links {
    display: flex;
    justify-content: center;
    gap: 24px;
    margin-bottom: 16px;
}

.footer-links a {
    color: var(--text-muted);
    font-size: 13px;
    text-decoration: none;
    transition: color 0.2s ease;
}

.footer-links a:hover {
    color: var(--accent-blue);
}

.footer-copyright {
    font-size: 12px;
    color: var(--text-dim);
}

/* ═══════════════════════════════════════════════════════════════════════════════
   ANIMATIONS
   ═══════════════════════════════════════════════════════════════════════════════ */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes slideInRight {
    from { opacity: 0; transform: translateX(20px); }
    to { opacity: 1; transform: translateX(0); }
}

@keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-10px); }
}

.animate-fade-in {
    animation: fadeIn 0.5s ease-out forwards;
}

.animate-slide-in {
    animation: slideInRight 0.5s ease-out forwards;
}

.animate-float {
    animation: float 3s ease-in-out infinite;
}

/* ═══════════════════════════════════════════════════════════════════════════════
   RESPONSIVE
   ═══════════════════════════════════════════════════════════════════════════════ */
@media (max-width: 768px) {
    .landing-title {
        font-size: 48px;
    }
    
    .landing-subtitle {
        font-size: 20px;
    }
    
    .metric-value {
        font-size: 28px;
    }
    
    .app-header {
        flex-direction: column;
        gap: 16px;
        text-align: center;
    }
}

/* ═══════════════════════════════════════════════════════════════════════════════
   NEWS TICKER
   ═══════════════════════════════════════════════════════════════════════════════ */
.news-ticker-container {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    overflow: hidden;
    margin-bottom: 20px;
}

.news-ticker-header {
    padding: 10px 20px;
    background: linear-gradient(90deg, rgba(239, 68, 68, 0.12), rgba(245, 158, 11, 0.12));
    border-bottom: 1px solid var(--border-subtle);
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 12px;
    font-weight: 700;
    color: var(--accent-yellow);
    text-transform: uppercase;
    letter-spacing: 1px;
}

.news-ticker {
    overflow: hidden;
    white-space: nowrap;
    padding: 12px 0;
}

.news-ticker-content {
    display: inline-block;
    animation: ticker 60s linear infinite;
}

.news-ticker-content:hover {
    animation-play-state: paused;
}

.news-item {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 0 40px;
    color: var(--text-secondary);
    font-size: 13px;
}

.news-item .severity-high { color: var(--accent-red); }
.news-item .severity-medium { color: var(--accent-yellow); }
.news-item .severity-low { color: var(--accent-green); }

.news-item .stock-mention {
    background: var(--accent-blue-dim);
    padding: 2px 8px;
    border-radius: var(--radius-sm);
    color: var(--accent-blue);
    font-weight: 600;
}

@keyframes ticker {
    0% { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}

/* ═══════════════════════════════════════════════════════════════════════════════
   STOCK CARDS - Enhanced
   ═══════════════════════════════════════════════════════════════════════════════ */
.stock-card {
    position: relative;
    overflow: hidden;
}

.stock-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    opacity: 0.8;
}

.stock-card.sector-tech::before { background: linear-gradient(90deg, #3b82f6, #8b5cf6); }
.stock-card.sector-energy::before { background: linear-gradient(90deg, #f59e0b, #ef4444); }
.stock-card.sector-retail::before { background: linear-gradient(90deg, #f59e0b, #22c55e); }
.stock-card.sector-crypto::before { background: linear-gradient(90deg, #f59e0b, #eab308); }
.stock-card.sector-automotive::before { background: linear-gradient(90deg, #ef4444, #f97316); }
.stock-card.sector-entertainment::before { background: linear-gradient(90deg, #dc2626, #ec4899); }
.stock-card.sector-ai::before { background: linear-gradient(90deg, #8b5cf6, #06b6d4); }
.stock-card.sector-semiconductors::before { background: linear-gradient(90deg, #84cc16, #22c55e); }
.stock-card.sector-finance::before { background: linear-gradient(90deg, #0ea5e9, #3b82f6); }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def format_currency(value: float) -> str:
    """Format number as currency."""
    if abs(value) >= 1_000_000:
        return f"${value/1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"${value/1_000:.1f}K"
    return f"${value:.2f}"

def format_percent(value: float) -> str:
    """Format number as percentage."""
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"

def get_status_class(status: str) -> str:
    """Get CSS class for status."""
    return f"status-{status.lower()}"

def get_status_emoji(status: str) -> str:
    """Get emoji for status."""
    emojis = {
        "IDLE": "●",
        "CONFIGURED": "●",
        "RUNNING": "●",
        "PAUSED": "●",
        "COMPLETED": "●"
    }
    return emojis.get(status, "●")

def create_sparkline(values: list, color: str = "#10b981") -> go.Figure:
    """Create a mini sparkline chart."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=values,
        mode='lines',
        line=dict(color=color, width=2),
        fill='tozeroy',
        fillcolor=f'rgba{tuple(list(int(color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)) + [0.1])}'
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=40,
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False),
        yaxis=dict(visible=False)
    )
    return fig

# ═══════════════════════════════════════════════════════════════════════════════
# LANDING PAGE
# ═══════════════════════════════════════════════════════════════════════════════

def render_landing_page():
    """Render the premium landing page."""
    
    landing_html = """<div class="landing-container">
    <div class="landing-badge">Research Laboratory</div>
    <h1 class="landing-title animate-fade-in">StockAI</h1>
    <p class="landing-subtitle">Behavioral Finance & Multi-Agent Market Simulation Engine</p>
    <p class="landing-description">Experience cutting-edge agent-based modeling where AI-powered traders with realistic behavioral biases compete in dynamic markets. Analyze trading patterns, behavioral profiles, market sentiment, and real-time simulation metrics to understand how psychology drives market dynamics.</p>
    <div class="feature-grid">
        <div class="feature-badge">50+ AI Agents</div>
        <div class="feature-badge">Real-Time Analytics</div>
        <div class="feature-badge">Behavioral Profiles</div>
        <div class="feature-badge">Market Simulation</div>
        <div class="feature-badge">Pattern Analysis</div>
        <div class="feature-badge">Custom Agents</div>
    </div>
</div>"""
    
    st.markdown(landing_html, unsafe_allow_html=True)
    
    # Action buttons - tighter layout
    col1, col2, col3, col4, col5 = st.columns([2, 1, 0.2, 1, 2])
    
    with col2:
        if st.button("View Guidelines", width='stretch', type="secondary"):
            st.session_state.show_guidelines = True
            st.rerun()
    
    with col4:
        if st.button("Launch Simulation", width='stretch', type="primary"):
            st.session_state.app_started = True
            st.rerun()
    
    # Stats showcase - reduced spacing
    st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)
    
    cols = st.columns(4)
    stats = [
        ("📅", "264", "Trading Days/Year", "metric-green"),
        ("🔁", "3", "Sessions Per Day", "metric-blue"),
        ("🧠", "4", "Behavioral Biases", "metric-purple"),
        ("🌐", "∞", "Stock Universes", "metric-yellow"),
    ]
    
    for col, (icon, value, label, color) in zip(cols, stats):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <span class="metric-icon">{icon}</span>
                <div class="metric-value {color}">{value}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Tech stack
    st.markdown("""
    <div class="tech-stack">
        <div class="tech-item">Python</div>
        <div class="tech-item">Streamlit</div>
        <div class="tech-item">Plotly</div>
        <div class="tech-item">Multi-Agent AI</div>
        <div class="tech-item">Behavioral Finance</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("""
    <div class="app-footer">
        <div class="footer-brand">StockAI Research Laboratory</div>
        <div class="footer-copyright">
            © 2026 Final Year Project · Behavioral Finance + Multi-Agent Systems
        </div>
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# GUIDELINES PAGE
# ═══════════════════════════════════════════════════════════════════════════════

def render_guidelines_page():
    """Render the guidelines/documentation page."""
    
    # Back button
    col1, col2, col3 = st.columns([1, 6, 1])
    with col1:
        if st.button("← Back", type="secondary"):
            st.session_state.show_guidelines = False
            st.rerun()
    
    # Hero section
    st.markdown("""
    <div class="guidelines-hero">
        <h1 class="guidelines-title">📖 User Guidelines</h1>
        <p class="guidelines-subtitle">
            Learn how to use the StockAI Market Simulation Lab effectively. 
            This platform simulates trading environments with AI-powered agents 
            exhibiting realistic behavioral biases.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Two column layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<p class="guidelines-section-title">Getting Started</p>', unsafe_allow_html=True)
        
        steps = [
            ("1", "Configure Simulation", "Set up your simulation parameters including number of agents, trading days, market volatility, and random seed."),
            ("2", "Launch Simulation", "Click 'Run Day' to advance one trading day at a time, or enable auto-advance for continuous simulation."),
            ("3", "Monitor Dashboard", "Watch real-time updates of stock prices, agent activities, and market events on the Overview tab."),
            ("4", "Analyze Results", "Use the Comparative Analysis tab to compare agent strategies and identify patterns."),
        ]
        
        for num, title, desc in steps:
            st.markdown(f'''
            <div class="step-card">
                <div class="step-number">{num}</div>
                <div class="step-content">
                    <h4>{title}</h4>
                    <p>{desc}</p>
                </div>
            </div>
            ''', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<p class="guidelines-section-title">Agent Strategies</p>', unsafe_allow_html=True)
        
        strategies = [
            ("conservative", "🛡️", "Conservative", "Low risk tolerance, prefers stable assets, minimal trading activity. Uses stop-loss orders to protect capital and limit downside exposure."),
            ("aggressive", "🔥", "Aggressive", "High risk tolerance, actively trades on momentum, uses leverage. May take large positions and pursue short-term gains aggressively."),
            ("balanced", "⚖️", "Balanced", "Moderate risk approach, diversifies between assets, follows fundamental analysis. Aims for steady growth with controlled volatility."),
            ("growth", "🚀", "Growth-Oriented", "Focuses on high-growth opportunities, willing to accept volatility for potential returns. Prioritizes capital appreciation over income."),
        ]
        
        for style, icon, name, desc in strategies:
            st.markdown(f'''
            <div class="strategy-card {style}">
                <h4>{icon} {name}</h4>
                <p>{desc}</p>
            </div>
            ''', unsafe_allow_html=True)
    
    # Behavioral Biases Section
    st.markdown('<p class="guidelines-section-title">Behavioral Biases</p>', unsafe_allow_html=True)
    
    cols = st.columns(4)
    biases = [
        ("herding", "🐑", "Herding", "Agents follow crowd behavior, buying when others buy and selling when others sell."),
        ("loss-aversion", "😰", "Loss Aversion", "Agents feel losses more strongly than gains, leading to risk-averse behavior."),
        ("overconfidence", "😤", "Overconfidence", "Agents overestimate their abilities, leading to excessive trading."),
        ("anchoring", "⚓", "Anchoring", "Agents rely too heavily on initial information when making decisions."),
    ]
    
    for col, (style, icon, name, desc) in zip(cols, biases):
        with col:
            st.markdown(f'''
            <div class="bias-card {style}">
                <h4><span class="bias-icon">{icon}</span> {name}</h4>
                <p>{desc}</p>
            </div>
            ''', unsafe_allow_html=True)
    
    # Key Features
    st.markdown('<div style="margin-top: 32px;"></div>', unsafe_allow_html=True)
    st.markdown('<p class="guidelines-section-title key-features">Platform Capabilities</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    features = [
        ("charts", "📊 Interactive Charts", "Real-time Plotly visualizations of stock prices, agent trades, and behavioral metrics with event markers."),
        ("agents", "🤖 Agent Intelligence", "Detailed agent profiles showing behavioral indicators, trading history, P&L, and personality traits."),
        ("simulation", "🎮 Advanced Simulation", "Run for custom durations (5/10/30 days), with auto-advance and adjustable simulation speed."),
        ("duration", "⏱️ Flexible Duration", "Pre-built duration buttons for quick runs, plus full manual control for detailed testing."),
        ("analysis", "🔬 Behavioral Metrics", "Track 4 key biases: Herding, Loss Aversion, Overconfidence, and Anchoring in real-time."),
        ("stocks", "📈 Custom Universe", "Trade multiple stocks with filterable extended market universe and detailed price history."),
    ]
    
    for col, features_subset in zip([col1, col2, col3], [features[:2], features[2:4], features[4:]]):
        with col:
            for style, name, desc in features_subset:
                st.markdown(f'''
                <div class="feature-card {style}">
                    <h4>{name}</h4>
                    <p>{desc}</p>
                </div>
                ''', unsafe_allow_html=True)
    
    # Continue button
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("Start Simulation", width='stretch', type="primary"):
            st.session_state.app_started = True
            st.session_state.show_guidelines = False
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER COMPONENT
# ═══════════════════════════════════════════════════════════════════════════════

def render_header():
    """Render the main application header."""
    state = engine.get_state()
    
    status_class = get_status_class(state.status)
    status_emoji = get_status_emoji(state.status)
    current_time = datetime.now().strftime('%b %d, %Y · %H:%M')
    
    # Create header using a container for styling
    with st.container():
        col1, col2, col3, col4 = st.columns([2.5, 3, 1.5, 1])
        
        with col1:
            st.markdown("""
            <div class="brand">
                <div class="brand-icon">
                    <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M6 22L12 16L18 20L26 10" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                        <circle cx="26" cy="10" r="3" fill="white"/>
                        <path d="M6 26V22" stroke="white" stroke-width="2" stroke-linecap="round"/>
                        <path d="M12 26V16" stroke="white" stroke-width="2" stroke-linecap="round"/>
                        <path d="M18 26V20" stroke="white" stroke-width="2" stroke-linecap="round"/>
                        <path d="M24 26V14" stroke="white" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                </div>
                <div class="brand-text">
                    <h1>StockAI</h1>
                    <p>Market Simulation Lab</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if state.status != "IDLE":
                progress = (state.current_day / state.total_days * 100) if state.total_days > 0 else 0
                st.markdown(f"""
                <div style="text-align: center; padding-top: 8px;">
                    <span style="font-size: 26px; font-weight: 800; color: var(--text-primary);">Day {state.current_day}</span>
                    <span style="color: var(--text-muted); font-size: 14px; font-weight: 500;"> / {state.total_days}</span>
                    <div class="progress-container" style="margin-top: 8px; max-width: 180px; margin-left: auto; margin-right: auto;">
                        <div class="progress-bar" style="width: {progress}%;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div style="text-align: right; padding-top: 8px; display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
                <span class="status-badge {status_class}">{status_emoji} {state.status}</span>
                <div style="font-size: 11px; color: var(--text-dim);">{current_time}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown("<div style='padding-top: 8px;'></div>", unsafe_allow_html=True)
            if st.button("Guidelines", key="header_guidelines", width='stretch'):
                st.session_state.show_guidelines = True
                st.session_state.app_started = False
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# NEWS TICKER COMPONENT
# ═══════════════════════════════════════════════════════════════════════════════

def render_news_ticker(state):
    """Render a scrolling news ticker with market events."""
    if not state.events and not state.extra_stocks:
        return
    
    # Build news items from events and stock movements
    news_items = []
    
    # Add recent events
    recent_events = [e for e in state.events if e.day <= state.current_day][-5:]
    for event in recent_events:
        severity_class = f"severity-{event.severity.lower()}"
        news_items.append(f'<span class="{severity_class}">●</span> <strong>{event.title}</strong>: {event.description[:50]}...')
    
    # Add stock movements for extra stocks
    for stock in (state.extra_stocks or [])[:6]:
        if abs(stock.change_percent) > 3:
            direction = "📈" if stock.change_percent > 0 else "📉"
            stock_meta = STOCK_UNIVERSE.get(stock.name, {"emoji": "📊"})
            news_items.append(f'{direction} <span class="stock-mention">{stock_meta.get("emoji", "📊")} {stock.name}</span> {stock.change_percent:+.1f}%')
    
    # Add primary stock movements
    if state.stock_a and abs(state.stock_a.change_percent) > 2:
        direction = "📈" if state.stock_a.change_percent > 0 else "📉"
        stock_meta = PRIMARY_STOCKS.get(state.stock_a.name, {"emoji": "⛽"})
        news_items.append(f'{direction} <span class="stock-mention">{stock_meta.get("emoji", "⛽")} {state.stock_a.name}</span> {state.stock_a.change_percent:+.1f}%')
    
    if state.stock_b and abs(state.stock_b.change_percent) > 2:
        direction = "📈" if state.stock_b.change_percent > 0 else "📉"
        stock_meta = PRIMARY_STOCKS.get(state.stock_b.name, {"emoji": "⚡"})
        news_items.append(f'{direction} <span class="stock-mention">{stock_meta.get("emoji", "⚡")} {state.stock_b.name}</span> {state.stock_b.change_percent:+.1f}%')
    
    if not news_items:
        news_items = ["Welcome to StockAI Market Simulation • Configure and run to see market updates"]
    
    # Duplicate items for continuous scroll effect
    items_html = "".join([f'<span class="news-item">{item}</span>' for item in news_items])
    items_html = items_html + items_html  # Duplicate for seamless loop
    
    st.markdown(f"""
    <div class="news-ticker-container">
        <div class="news-ticker-header">
            <span>📰</span> Market News
        </div>
        <div class="news-ticker">
            <div class="news-ticker-content">
                {items_html}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# OVERVIEW TAB
# ═══════════════════════════════════════════════════════════════════════════════

def render_overview():
    """Render the overview dashboard."""
    state = engine.get_state()
    
    # Mode Banner - indicate simulation mode (Demo vs LLM)
    if state.status not in ["IDLE"]:
        if state.llm_mode:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(38,166,154,0.15), rgba(16,185,129,0.15)); 
                        border: 1px solid rgba(38,166,154,0.4); border-radius: 8px; 
                        padding: 10px 16px; margin-bottom: 16px; 
                        display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 18px;">🧠</span>
                <div style="flex: 1;">
                    <span style="font-weight: 600; color: var(--accent-green);">LLM Mode Active</span>
                    <span style="color: var(--text-secondary); font-size: 13px;"> — Agents powered by Groq Llama 3.3 70B. 
                    {state.llm_calls_made} API calls made.</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(99,102,241,0.1), rgba(168,85,247,0.1)); 
                        border: 1px solid rgba(139,92,246,0.3); border-radius: 8px; 
                        padding: 10px 16px; margin-bottom: 16px; 
                        display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 18px;">🎮</span>
                <div style="flex: 1;">
                    <span style="font-weight: 600; color: var(--accent-purple);">Demo Mode</span>
                    <span style="color: var(--text-muted); font-size: 13px;"> — Agents use simulated behavior patterns. 
                    Enable LLM Mode in Controls to use AI-powered trading.</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # News ticker at the top
    if state.current_day > 0:
        render_news_ticker(state)
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    
    # Key Metrics Row
    st.markdown('<p class="section-title">Market Overview</p>', unsafe_allow_html=True)
    
    cols = st.columns(5)
    
    metrics = [
        ("💰", format_currency(state.total_capital) if state.total_capital > 0 else "$0", "Total Capital", "metric-green", "+2.4%"),
        ("🤖", str(state.active_agents), "Active Agents", "metric-blue", f"of {len(state.agents) if state.agents else 0}"),
        ("🐑", f"{state.herding_percentage:.0f}%" if state.herding_percentage > 0 else "0%", "Herding Index", "metric-purple", "behavioral"),
        ("📊", state.market_sentiment.title() if state.market_sentiment else "—", "Market Sentiment", "metric-yellow", "current"),
        ("⚠️", state.system_risk if state.system_risk else "LOW", "System Risk", "metric-red" if state.system_risk == "HIGH" else "metric-green", "level"),
    ]
    
    for col, (icon, value, label, color, extra) in zip(cols, metrics):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <span class="metric-icon">{icon}</span>
                <div class="metric-value {color}">{value}</div>
                <div class="metric-label">{label}</div>
                <div class="metric-change" style="background: var(--bg-tertiary);">{extra}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    
    # Main content
    col1, col2 = st.columns([2.5, 1])
    
    with col1:
        st.markdown('<p class="section-title">Stock Performance</p>', unsafe_allow_html=True)
        
        if state.stock_a and len(state.stock_a.price_history) > 1:
            price_data = engine.get_price_history_df()
            if not price_data:
                st.markdown("""
                <div class="empty-state">
                    <div class="empty-state-title">No Price Data Yet</div>
                    <div class="empty-state-description">Configure and run the simulation to see price charts</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Get actual stock names and metadata
                stock_a_name = state.stock_a.name
                stock_b_name = state.stock_b.name if state.stock_b else "ZapTech"
                stock_a_meta = PRIMARY_STOCKS.get(stock_a_name, {"color": "#f59e0b", "emoji": "⛽"})
                stock_b_meta = PRIMARY_STOCKS.get(stock_b_name, {"color": "#3b82f6", "emoji": "⚡"})
                
                fig = go.Figure()

                # Stock A (primary)
                fig.add_trace(go.Scatter(
                    x=price_data["days"],
                    y=price_data["stock_a"],
                    name=f"{stock_a_meta.get('emoji', '⛽')} {stock_a_name}",
                    line=dict(color=stock_a_meta.get('color', '#f59e0b'), width=3),
                    fill='tozeroy',
                    fillcolor=f"rgba({int(stock_a_meta.get('color', '#f59e0b').lstrip('#')[0:2], 16)},{int(stock_a_meta.get('color', '#f59e0b').lstrip('#')[2:4], 16)},{int(stock_a_meta.get('color', '#f59e0b').lstrip('#')[4:6], 16)},0.08)",
                    hovertemplate=f'Day %{{x}}<br>{stock_a_name}: $%{{y:.2f}}<extra></extra>'
                ))

                # Stock B (secondary)
                fig.add_trace(go.Scatter(
                    x=price_data["days"],
                    y=price_data["stock_b"],
                    name=f"{stock_b_meta.get('emoji', '⚡')} {stock_b_name}",
                    line=dict(color=stock_b_meta.get('color', '#3b82f6'), width=3),
                    fill='tozeroy',
                    fillcolor=f"rgba({int(stock_b_meta.get('color', '#3b82f6').lstrip('#')[0:2], 16)},{int(stock_b_meta.get('color', '#3b82f6').lstrip('#')[2:4], 16)},{int(stock_b_meta.get('color', '#3b82f6').lstrip('#')[4:6], 16)},0.08)",
                    hovertemplate=f'Day %{{x}}<br>{stock_b_name}: $%{{y:.2f}}<extra></extra>'
                ))

                # Event overlays (recent and high-impact)
                if state.events:
                    severity_colors = {
                        "LOW": "rgba(16,185,129,0.6)",
                        "MEDIUM": "rgba(245,158,11,0.7)",
                        "HIGH": "rgba(239,68,68,0.8)"
                    }
                    event_candidates = [e for e in state.events if e.day <= state.current_day]
                    if not event_candidates:
                        event_candidates = state.events
                    for e in event_candidates[:6]:
                        fig.add_vline(
                            x=e.day,
                            line_width=1,
                            line_dash="dot",
                            line_color=severity_colors.get(e.severity, "rgba(148,163,184,0.6)"),
                            annotation_text=e.title,
                            annotation_position="top left",
                            annotation_font_size=10,
                            annotation_font_color=severity_colors.get(e.severity, "#94a3b8")
                        )

                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#a1a1aa', family='Inter'),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1,
                        bgcolor='rgba(0,0,0,0)',
                        font=dict(size=12)
                    ),
                    margin=dict(l=0, r=0, t=50, b=0),
                    xaxis=dict(
                        showgrid=True,
                        gridcolor='rgba(255,255,255,0.04)',
                        title=dict(text="Trading Day", font=dict(size=11)),
                        tickfont=dict(size=10)
                    ),
                    yaxis=dict(
                        showgrid=True,
                        gridcolor='rgba(255,255,255,0.04)',
                        title=dict(text="Price ($)", font=dict(size=11)),
                        tickfont=dict(size=10),
                        tickprefix="$"
                    ),
                    height=380,
                    hovermode='x unified'
                )

                st.plotly_chart(fig, width='stretch')

                # Stock price cards
                pcol1, pcol2 = st.columns(2)
                
                # Get stock metadata
                stock_a_name = state.stock_a.name
                stock_b_name = state.stock_b.name if state.stock_b else "ZapTech"
                stock_a_meta = PRIMARY_STOCKS.get(stock_a_name, {"color": "#f59e0b", "emoji": "⛽", "sector": "Energy"})
                stock_b_meta = PRIMARY_STOCKS.get(stock_b_name, {"color": "#3b82f6", "emoji": "⚡", "sector": "Tech"})

                with pcol1:
                    change_a = state.stock_a.change_percent
                    color_a = "#10b981" if change_a >= 0 else "#ef4444"
                    st.markdown(f"""
                    <div class="info-card" style="border-left: 4px solid {stock_a_meta.get('color', '#f59e0b')};">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 4px; display: flex; align-items: center; gap: 6px;">
                                    <span style="font-size: 16px;">{stock_a_meta.get('emoji', '⛽')}</span>
                                    {stock_a_name.upper()}
                                </div>
                                <div style="font-size: 28px; font-weight: 800; color: var(--text-primary);">${state.stock_a.price:.2f}</div>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 18px; font-weight: 700; color: {color_a};">
                                    {'+' if change_a >= 0 else ''}{change_a:.2f}%
                                </div>
                                <div style="font-size: 11px; color: var(--text-dim);">from initial</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with pcol2:
                    stock_b = state.stock_b
                    change_b = stock_b.change_percent if stock_b else 0
                    price_b = stock_b.price if stock_b else 0.0
                    color_b = "#10b981" if change_b >= 0 else "#ef4444"
                    st.markdown(f"""
                    <div class="info-card" style="border-left: 4px solid {stock_b_meta.get('color', '#3b82f6')};">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 4px; display: flex; align-items: center; gap: 6px;">
                                    <span style="font-size: 16px;">{stock_b_meta.get('emoji', '⚡')}</span>
                                    {stock_b_name.upper()}
                                </div>
                                <div style="font-size: 28px; font-weight: 800; color: var(--text-primary);">${price_b:.2f}</div>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 18px; font-weight: 700; color: {color_b};">
                                    {'+' if change_b >= 0 else ''}{change_b:.2f}%
                                </div>
                                <div style="font-size: 11px; color: var(--text-dim);">from initial</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-state-icon">📈</div>
                <div class="empty-state-title">No Price Data Yet</div>
                <div class="empty-state-description">Configure and run the simulation to see price charts</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown('<p class="section-title">Agent Forum</p>', unsafe_allow_html=True)
        
        messages = engine.get_recent_messages(6)
        
        if messages:
            for msg in reversed(messages):
                sentiment_class = f"bbs-{msg.sentiment}"
                st.markdown(f"""
                <div class="bbs-message {sentiment_class}">
                    <div class="bbs-header">
                        <span class="bbs-agent">{msg.agent_name}</span>
                        <div class="bbs-meta">
                            <span class="bbs-sentiment">{msg.sentiment}</span>
                            <span class="bbs-day">Day {msg.day}</span>
                        </div>
                    </div>
                    <div class="bbs-content">{msg.message}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="empty-state" style="padding: 40px;">
                <div class="empty-state-icon">💭</div>
                <div class="empty-state-title">No Messages Yet</div>
                <div class="empty-state-description">Agent discussions will appear here</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Today's Events
    if state.current_day > 0:
        events = engine.get_today_events()
        if events:
            st.markdown('<p class="section-title">Today\'s Market Events</p>', unsafe_allow_html=True)
            
            cols = st.columns(min(len(events), 3))
            for col, event in zip(cols, events[:3]):
                with col:
                    severity_class = f"event-{event.severity.lower()}"
                    st.markdown(f"""
                    <div class="event-card {severity_class}">
                        <div class="event-header">
                            <span class="event-title">{event.title}</span>
                            <span class="event-severity">{event.severity}</span>
                        </div>
                        <p class="event-description">{event.description}</p>
                    </div>
                    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATION CONTROLS TAB
# ═══════════════════════════════════════════════════════════════════════════════

def render_controls():
    """Render simulation controls."""
    state = engine.get_state()
    
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        st.markdown('<p class="section-title">Simulation Configuration</p>', unsafe_allow_html=True)
        st.markdown('<p class="section-subtitle">Set up your simulation parameters</p>', unsafe_allow_html=True)
        
        with st.form("config_form", border=False):
            # LLM Mode toggle
            st.markdown("**🧠 AI Mode**")
            llm_available = engine.is_llm_available()
            llm_mode = st.toggle(
                "Enable LLM Mode (Groq Llama 3.3 70B)",
                value=False,
                disabled=not llm_available,
                help="Uses real AI to make trading decisions. Requires GROQ_API_KEY in .env" if llm_available else "GROQ_API_KEY not found in .env file"
            )
            
            if llm_mode:
                st.markdown("""
                <div style="background: rgba(38,166,154,0.1); border: 1px solid rgba(38,166,154,0.3); 
                            border-radius: 6px; padding: 8px 12px; font-size: 12px; color: var(--text-secondary);">
                    ⚡ <strong style="color: var(--accent-green);">LLM Mode</strong> — Each agent uses Groq Llama 3.3 70B for decisions. 
                    Max 20 agents due to API rate limits. Simulation runs slower (~3s per agent per session).
                </div>
                """, unsafe_allow_html=True)
            elif not llm_available:
                st.markdown("""
                <div style="background: rgba(239,83,80,0.1); border: 1px solid rgba(239,83,80,0.3); 
                            border-radius: 6px; padding: 8px 12px; font-size: 12px; color: var(--text-secondary);">
                    ⚠️ GROQ_API_KEY not found. Add it to your <code>.env</code> file to enable LLM mode. 
                    Get a free key at <a href="https://console.groq.com" target="_blank" style="color: var(--accent-blue);">console.groq.com</a>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            
            # Agent settings
            st.markdown("**Agent Settings**")
            fcol1, fcol2 = st.columns(2)
            with fcol1:
                max_agents = 20 if llm_mode else 100
                default_agents = 10 if llm_mode else 50
                agent_count = st.slider("Number of Agents", 2, max_agents, min(default_agents, max_agents), 1 if llm_mode else 5,
                    help=f"{'Max 20 in LLM mode due to API limits' if llm_mode else 'More agents = more complex market dynamics'}")
            with fcol2:
                total_days = st.slider("Simulation Days", 10, 264, 30, 5,
                    help="264 days = 1 trading year")
            
            st.markdown("**Market Settings**")
            fcol1, fcol2 = st.columns(2)
            with fcol1:
                volatility = st.select_slider(
                    "Market Volatility",
                    options=["Low", "Medium", "High", "Extreme"],
                    value="Medium",
                    help="Higher volatility = larger price swings"
                )
            with fcol2:
                event_intensity = st.slider("Event Intensity", 1, 10, 5,
                    help="Frequency and impact of market events")
            
            st.markdown("**Advanced Settings**")
            fcol1, fcol2 = st.columns(2)
            with fcol1:
                loan_enabled = st.toggle("Enable Loan Market", value=True,
                    help="Allow agents to take loans and use leverage")
            with fcol2:
                random_seed = st.number_input("Random Seed", 1, 9999, 42,
                    help="For reproducible simulations")

            
            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
            
            st.markdown("""
            <style>
            button[data-testid="stFormSubmitButton"] {
                background: linear-gradient(135deg, var(--accent-green) 0%, #059669 100%) !important;
                color: white !important;
                border: none !important;
            }
            button[data-testid="stFormSubmitButton"]:hover {
                background: linear-gradient(135deg, #10b981 0%, #047857 100%) !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            submitted = st.form_submit_button("Apply Configuration", width='stretch')
            
            if submitted:
                try:
                    engine.configure(
                        agent_count=agent_count,
                        total_days=total_days,
                        volatility=volatility,
                        event_intensity=event_intensity,
                        loan_market_enabled=loan_enabled,
                        random_seed=random_seed,
                        custom_agent=st.session_state.custom_agent if st.session_state.custom_agent.get("enabled") else None,
                        manual_events=st.session_state.manual_events,
                        llm_mode=llm_mode,
                    )
                    st.success("✅ Configuration applied successfully!")
                    st.rerun()
                except ValueError as e:
                    st.error(f"⚠️ Configuration Error: {e}")
                except Exception as e:
                    st.error(f"❌ Unexpected error: {e}")
    
    with col2:
        st.markdown('<p class="section-title">Simulation Controls</p>', unsafe_allow_html=True)
        st.markdown('<p class="section-subtitle">Run and manage your simulation</p>', unsafe_allow_html=True)
        
        # Control buttons
        btn_cols = st.columns(3)
        
        with btn_cols[0]:
            run_disabled = state.status not in ["CONFIGURED", "PAUSED", "RUNNING"]
            if st.button("Run Day", width='stretch', disabled=run_disabled):
                try:
                    spinner_msg = "🧠 LLM agents thinking..." if state.llm_mode else "Simulating..."
                    with st.spinner(spinner_msg):
                        engine.run_day()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Simulation error: {e}")
                    st.session_state.auto_run = False
        
        with btn_cols[1]:
            if state.status == "RUNNING":
                if st.button("Pause", width='stretch'):
                    engine.pause()
                    st.rerun()
            else:
                if st.button("Pause", width='stretch', disabled=True):
                    pass
        
        with btn_cols[2]:
            reset_disabled = state.status == "IDLE"
            if st.button("Reset", width='stretch', disabled=reset_disabled):
                engine.reset()
                st.session_state.auto_run = False
                st.rerun()
        
        # Duration-based run buttons
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        st.markdown("**Run for Duration**")
        
        duration_cols = st.columns(3)
        run_disabled = state.status not in ["CONFIGURED", "PAUSED", "RUNNING"]
        
        with duration_cols[0]:
            if st.button("📅 5 Days", width='stretch', disabled=run_disabled):
                try:
                    with st.spinner("Running 5 days..."):
                        for _ in range(5):
                            engine.run_day()
                    st.success("✅ 5-day simulation completed!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Simulation error: {e}")
        
        with duration_cols[1]:
            if st.button("📅 10 Days", width='stretch', disabled=run_disabled):
                try:
                    with st.spinner("Running 10 days..."):
                        for _ in range(10):
                            engine.run_day()
                    st.success("✅ 10-day simulation completed!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Simulation error: {e}")
        
        with duration_cols[2]:
            if st.button("📅 30 Days", width='stretch', disabled=run_disabled):
                try:
                    with st.spinner("Running 30 days..."):
                        for _ in range(30):
                            engine.run_day()
                    st.success("✅ 30-day simulation completed!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Simulation error: {e}")
        
        # Auto-run
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        
        if state.status in ["CONFIGURED", "RUNNING", "PAUSED"]:
            auto_run = st.toggle("⚡ Auto-advance simulation", value=st.session_state.auto_run,
                help="Automatically advance simulation every 2 seconds")
            st.session_state.auto_run = auto_run

            st.session_state.sim_speed = st.select_slider(
                "Simulation Speed",
                options=["Slow", "Normal", "Fast", "Ultra"],
                value=st.session_state.sim_speed,
                help="Controls how quickly days advance during auto-run"
            )
            
            if auto_run and state.status != "COMPLETED":
                delay = {
                    "Slow": 2.5,
                    "Normal": 1.5,
                    "Fast": 0.7,
                    "Ultra": 0.25
                }.get(st.session_state.sim_speed, 1.5)
                try:
                    engine.run_day()
                except Exception as e:
                    st.error(f"❌ Auto-run error: {e}")
                    st.session_state.auto_run = False
                time.sleep(delay)
                st.rerun()
        
        # Status card
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="info-card">
            <h4>📊 Current Status</h4>
            <p><strong>Status:</strong> <span class="status-badge {get_status_class(state.status)}" style="padding: 4px 12px; font-size: 11px;">
                {get_status_emoji(state.status)} {state.status}
            </span></p>
            <p><strong>Mode:</strong> {'🧠 LLM (Groq Llama 3.3)' if state.llm_mode else '🎮 Demo (Simulated)'}</p>
            <p><strong>Progress:</strong> Day {state.current_day} of {state.total_days}</p>
            <p><strong>Active Agents:</strong> {state.active_agents}</p>
            <p><strong>Volatility:</strong> {state.volatility}</p>
            <p><strong>Loan Market:</strong> {'Enabled' if state.loan_market_enabled else 'Disabled'}</p>
            {'<p><strong>LLM API Calls:</strong> ' + str(state.llm_calls_made) + '</p>' if state.llm_mode else ''}
        </div>
        """, unsafe_allow_html=True)

        # Rewind control
        if state.snapshots:
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            with st.expander("⏪ Rewind Simulation", expanded=False):
                days = sorted({s["day"] for s in state.snapshots})
                target_day = st.selectbox("Select Day", days, index=max(0, len(days) - 1))
                if st.button("Rewind to Day", width='stretch') and target_day is not None:
                    engine.rewind_to_day(int(target_day))
                    st.success(f"Rewound to Day {target_day}.")
                    st.rerun()

        # Manual events list
        if st.session_state.manual_events:
            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
            st.markdown('<p class="section-subtitle">🧩 Manual Events Queue</p>', unsafe_allow_html=True)
            for idx, evt in enumerate(st.session_state.manual_events[:6]):
                st.markdown(f"""
                <div class="info-card" style="padding: 12px 16px;">
                    <div style="display:flex; justify-content: space-between; align-items:center;">
                        <div>
                            <div style="font-weight: 700; color: var(--text-primary);">Day {evt['day']} · {evt['title']}</div>
                            <div style="font-size: 12px; color: var(--text-muted);">{evt['event_type'].title()} · {evt['severity']}</div>
                        </div>
                        <div style="font-size: 11px; color: var(--text-dim);">Manual</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            if st.button("🧹 Clear Manual Events", width='stretch'):
                st.session_state.manual_events = []
                st.rerun()

        # Manual event creator
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        with st.expander("➕ Add Manual Event", expanded=False):
            with st.form("manual_event_form", border=False):
                mcol1, mcol2 = st.columns(2)
                with mcol1:
                    event_day = st.number_input("Event Day", 1, max(10, state.total_days if state.total_days else 10), 1)
                    event_type = st.selectbox("Event Type", ["macro", "sentiment", "corporate"], index=0)
                    severity = st.selectbox("Severity", ["LOW", "MEDIUM", "HIGH"], index=1)
                with mcol2:
                    event_title = st.text_input("Event Title", value="Inflation Surprise")
                    event_description = st.text_area("Event Description", value="CPI print comes in hotter than expected.")
                    event_impact = st.text_input("Expected Impact", value="Higher volatility and sector rotation expected")

                if st.form_submit_button("Add Event", width='stretch'):
                    st.session_state.manual_events.append({
                        "day": int(event_day),
                        "event_type": event_type,
                        "title": event_title.strip() or "Manual Event",
                        "description": event_description.strip() or "User-defined market event",
                        "severity": severity,
                        "impact": event_impact.strip() or "User-defined impact"
                    })
                    st.success("Manual event added. Apply configuration to include it.")
        
        # Quick actions
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        
        qcol1, qcol2 = st.columns(2)
        with qcol1:
            if st.button("Guidelines", width='stretch', type="secondary"):
                st.session_state.show_guidelines = True
                st.session_state.app_started = False
                st.rerun()
        with qcol2:
            if st.button("🏠 Home", width='stretch', type="secondary"):
                st.session_state.app_started = False
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# MARKET VIEW TAB
# ═══════════════════════════════════════════════════════════════════════════════

def render_market():
    """Render detailed market view."""
    state = engine.get_state()
    
    if not state.stock_a or state.current_day == 0:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📊</div>
            <div class="empty-state-title">No Market Data</div>
            <div class="empty-state-description">Configure and run the simulation to see market data</div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Header with export button
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.markdown('<p class="section-title">Market Analysis</p>', unsafe_allow_html=True)
    with header_col2:
        # Data export dropdown
        export_format = st.selectbox("Export Data", ["Select...", "CSV", "JSON"], key="market_export_format", label_visibility="collapsed")
        if export_format == "CSV":
            # Export price history as CSV
            price_data = engine.get_price_history_df()
            if price_data:
                import io
                csv_buffer = io.StringIO()
                pd.DataFrame(price_data).to_csv(csv_buffer, index=False)
                st.download_button(
                    "⬇️ Download CSV",
                    data=csv_buffer.getvalue(),
                    file_name=f"stockai_market_data_{state.current_day}.csv",
                    mime="text/csv",
                    width='stretch'
                )
        elif export_format == "JSON":
            # Export comprehensive state as JSON
            export_data = {
                "simulation_day": state.current_day,
                "status": state.status,
                "stocks": {
                    "stock_a": {"name": state.stock_a.name, "price": state.stock_a.price, "change": state.stock_a.change_percent},
                    "stock_b": {"name": state.stock_b.name, "price": state.stock_b.price, "change": state.stock_b.change_percent} if state.stock_b else None
                },
                "agents_summary": {
                    "total": len(state.agents),
                    "active": state.active_agents,
                    "bankrupt": len([a for a in state.agents if a.is_bankrupt])
                },
                "events": [{"day": e.day, "title": e.title, "severity": e.severity} for e in state.events[-10:]]
            }
            st.download_button(
                "⬇️ Download JSON",
                data=json.dumps(export_data, indent=2),
                file_name=f"stockai_snapshot_{state.current_day}.json",
                mime="application/json",
                width='stretch'
            )
    
    # Get stock metadata from the universe
    stock_a_meta = PRIMARY_STOCKS.get(state.stock_a.name, {"sector": "Energy", "emoji": "⛽", "description": "Established company"})
    stock_b_meta = PRIMARY_STOCKS.get(state.stock_b.name if state.stock_b else "ZapTech", {"sector": "Tech", "emoji": "⚡", "description": "Tech startup"})
    
    # Calculate high/low safely
    def get_high_low(price_history):
        if not price_history:
            return 0.0, 0.0
        try:
            prices = [p['price'] if isinstance(p, dict) else p for p in price_history]
            return max(prices), min(prices)
        except:
            return 0.0, 0.0
    
    high_a, low_a = get_high_low(state.stock_a.price_history)
    high_b, low_b = get_high_low(state.stock_b.price_history) if state.stock_b else (0.0, 0.0)
    
    # Stock overview cards
    col1, col2 = st.columns(2)
    
    with col1:
        change_a = state.stock_a.change_percent
        color_a = "#10b981" if change_a >= 0 else "#ef4444"
        arrow_a = "↑" if change_a >= 0 else "↓"
        
        st.markdown(f"""
        <div class="metric-card" style="text-align: left; padding: 28px; border-left: 4px solid {stock_a_meta.get('color', '#f59e0b')};">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                        <span style="font-size: 24px;">{stock_a_meta.get('emoji', '⛽')}</span>
                        <span style="font-size: 13px; color: var(--text-muted); letter-spacing: 1px;">{state.stock_a.name.upper()}</span>
                        <span style="font-size: 10px; padding: 3px 8px; background: var(--bg-glass); border-radius: 20px; color: var(--text-dim);">{stock_a_meta.get('sector', 'Energy')}</span>
                    </div>
                    <div style="font-size: 42px; font-weight: 800; color: var(--text-primary);">${state.stock_a.price:.2f}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 24px; font-weight: 700; color: {color_a};">
                        {arrow_a} {abs(change_a):.2f}%
                    </div>
                    <div style="font-size: 12px; color: var(--text-dim); margin-top: 4px;">
                        Initial: ${state.stock_a.initial_price:.2f}
                    </div>
                </div>
            </div>
            <div style="margin-top: 16px; display: flex; gap: 24px;">
                <div>
                    <div style="font-size: 11px; color: var(--text-dim);">HIGH</div>
                    <div style="font-size: 14px; font-weight: 600; color: #10b981;">${high_a:.2f}</div>
                </div>
                <div>
                    <div style="font-size: 11px; color: var(--text-dim);">LOW</div>
                    <div style="font-size: 14px; font-weight: 600; color: #ef4444;">${low_a:.2f}</div>
                </div>
                <div>
                    <div style="font-size: 11px; color: var(--text-dim);">VOLATILITY</div>
                    <div style="font-size: 14px; font-weight: 600; color: var(--text-secondary);">{stock_a_meta.get('volatility', 0.8)}x</div>
                </div>
            </div>
            <div style="margin-top: 12px; font-size: 12px; color: var(--text-dim);">
                {stock_a_meta.get('description', 'Established company')}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        stock_b = state.stock_b
        change_b = stock_b.change_percent if stock_b else 0
        price_b = stock_b.price if stock_b else 0.0
        initial_b = stock_b.initial_price if stock_b else 0.0
        stock_b_name = stock_b.name if stock_b else "ZapTech"
        color_b = "#10b981" if change_b >= 0 else "#ef4444"
        arrow_b = "↑" if change_b >= 0 else "↓"
        
        st.markdown(f"""
        <div class="metric-card" style="text-align: left; padding: 28px; border-left: 4px solid {stock_b_meta.get('color', '#3b82f6')};">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                        <span style="font-size: 24px;">{stock_b_meta.get('emoji', '⚡')}</span>
                        <span style="font-size: 13px; color: var(--text-muted); letter-spacing: 1px;">{stock_b_name.upper()}</span>
                        <span style="font-size: 10px; padding: 3px 8px; background: var(--bg-glass); border-radius: 20px; color: var(--text-dim);">{stock_b_meta.get('sector', 'Tech')}</span>
                    </div>
                    <div style="font-size: 42px; font-weight: 800; color: var(--text-primary);">${price_b:.2f}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 24px; font-weight: 700; color: {color_b};">
                        {arrow_b} {abs(change_b):.2f}%
                    </div>
                    <div style="font-size: 12px; color: var(--text-dim); margin-top: 4px;">
                        Initial: ${initial_b:.2f}
                    </div>
                </div>
            </div>
            <div style="margin-top: 16px; display: flex; gap: 24px;">
                <div>
                    <div style="font-size: 11px; color: var(--text-dim);">HIGH</div>
                    <div style="font-size: 14px; font-weight: 600; color: #10b981;">${high_b:.2f}</div>
                </div>
                <div>
                    <div style="font-size: 11px; color: var(--text-dim);">LOW</div>
                    <div style="font-size: 14px; font-weight: 600; color: #ef4444;">${low_b:.2f}</div>
                </div>
                <div>
                    <div style="font-size: 11px; color: var(--text-dim);">VOLATILITY</div>
                    <div style="font-size: 14px; font-weight: 600; color: var(--text-secondary);">{stock_b_meta.get('volatility', 1.3)}x</div>
                </div>
            </div>
            <div style="margin-top: 12px; font-size: 12px; color: var(--text-dim);">
                {stock_b_meta.get('description', 'Tech startup')}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
    
    # Detailed chart
    price_data = engine.get_price_history_df()
    if not price_data:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📉</div>
            <div class="empty-state-title">No Price Data Yet</div>
            <div class="empty-state-description">Run at least one trading day to see market charts</div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Get actual stock names for chart labels
    stock_a_name = state.stock_a.name
    stock_b_name = state.stock_b.name if state.stock_b else "ZapTech"
    
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.7, 0.3],
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=("", "")
    )
    
    # Calculate moving averages for smoother trend visualization
    stock_a_prices = price_data["stock_a"]
    stock_b_prices = price_data["stock_b"]
    days = price_data["days"]
    
    def moving_average(data, window=5):
        if len(data) < window:
            return data
        result = []
        for i in range(len(data)):
            if i < window - 1:
                result.append(sum(data[:i+1]) / (i+1))
            else:
                result.append(sum(data[i-window+1:i+1]) / window)
        return result
    
    # Stock A - Area chart with gradient effect
    fig.add_trace(go.Scatter(
        x=days,
        y=stock_a_prices,
        name=stock_a_name,
        mode='lines',
        line=dict(color=stock_a_meta.get('color', '#f59e0b'), width=2.5),
        fill='tozeroy',
        fillcolor=f"rgba({int(stock_a_meta.get('color', '#f59e0b')[1:3], 16)}, {int(stock_a_meta.get('color', '#f59e0b')[3:5], 16)}, {int(stock_a_meta.get('color', '#f59e0b')[5:7], 16)}, 0.1)",
        hovertemplate=f'<b>{stock_a_name}</b><br>Day %{{x}}<br>Price: $%{{y:.2f}}<extra></extra>'
    ), row=1, col=1)
    
    # Stock A Moving Average
    if len(stock_a_prices) >= 3:
        ma_a = moving_average(stock_a_prices, 5)
        fig.add_trace(go.Scatter(
            x=days,
            y=ma_a,
            name=f"{stock_a_name} MA(5)",
            mode='lines',
            line=dict(color=stock_a_meta.get('color', '#f59e0b'), width=1, dash='dot'),
            opacity=0.6,
            hovertemplate=f'<b>{stock_a_name} MA</b><br>$%{{y:.2f}}<extra></extra>'
        ), row=1, col=1)
    
    # Stock B - Area chart with gradient effect
    fig.add_trace(go.Scatter(
        x=days,
        y=stock_b_prices,
        name=stock_b_name,
        mode='lines',
        line=dict(color=stock_b_meta.get('color', '#3b82f6'), width=2.5),
        fill='tozeroy',
        fillcolor=f"rgba({int(stock_b_meta.get('color', '#3b82f6')[1:3], 16)}, {int(stock_b_meta.get('color', '#3b82f6')[3:5], 16)}, {int(stock_b_meta.get('color', '#3b82f6')[5:7], 16)}, 0.1)",
        hovertemplate=f'<b>{stock_b_name}</b><br>Day %{{x}}<br>Price: $%{{y:.2f}}<extra></extra>'
    ), row=1, col=1)
    
    # Stock B Moving Average
    if len(stock_b_prices) >= 3:
        ma_b = moving_average(stock_b_prices, 5)
        fig.add_trace(go.Scatter(
            x=days,
            y=ma_b,
            name=f"{stock_b_name} MA(5)",
            mode='lines',
            line=dict(color=stock_b_meta.get('color', '#3b82f6'), width=1, dash='dot'),
            opacity=0.6,
            hovertemplate=f'<b>{stock_b_name} MA</b><br>$%{{y:.2f}}<extra></extra>'
        ), row=1, col=1)
    
    # Add range selector buttons
    range_buttons = []
    if len(days) > 10:
        range_buttons = [
            dict(count=5, label="5D", step="day", stepmode="backward"),
            dict(count=10, label="10D", step="day", stepmode="backward"),
            dict(step="all", label="All")
        ]
    
    fig.add_trace(go.Scatter(
        x=price_data["days"],
        y=price_data["stock_b"],
        name=stock_b_name,
        line=dict(color=stock_b_meta.get('color', '#3b82f6'), width=2.5),
        hovertemplate='$%{y:.2f}<extra>' + stock_b_name + '</extra>'
    ), row=1, col=1)

    # Event overlays (market view) with improved styling
    if state.events:
        severity_colors = {
            "LOW": "rgba(16,185,129,0.5)",
            "MEDIUM": "rgba(245,158,11,0.6)",
            "HIGH": "rgba(239,68,68,0.7)"
        }
        event_candidates = [e for e in state.events if e.day <= state.current_day]
        if not event_candidates:
            event_candidates = state.events
        for e in event_candidates[:6]:
            # Add shaded region for event impact
            fig.add_vrect(
                x0=e.day - 0.5,
                x1=e.day + 0.5,
                fillcolor=severity_colors.get(e.severity, "rgba(148,163,184,0.2)"),
                opacity=0.3,
                line_width=0,
                row=1, col=1
            )
            fig.add_vline(
                x=e.day,
                line_width=2,
                line_dash="solid",
                line_color=severity_colors.get(e.severity, "rgba(148,163,184,0.6)"),
                annotation_text=f"📰 {e.title[:20]}...",
                annotation_position="top left",
                annotation_font_size=9,
                annotation_font_color="#a1a1aa",
                row=1, col=1
            )
    
    # Improved Spread/Volume chart - Waterfall style
    if len(stock_a_prices) > 0:
        spread = [b - a for a, b in zip(stock_a_prices, stock_b_prices)]
        
        # Create gradient colors based on spread values
        max_spread = max(abs(min(spread)), abs(max(spread))) if spread else 1
        colors = []
        for s in spread:
            if s >= 0:
                intensity = min(1, abs(s) / max_spread * 0.8 + 0.2)
                colors.append(f'rgba(16, 185, 129, {intensity})')
            else:
                intensity = min(1, abs(s) / max_spread * 0.8 + 0.2)
                colors.append(f'rgba(239, 68, 68, {intensity})')
        
        fig.add_trace(go.Bar(
            x=days,
            y=spread,
            name="Price Spread",
            marker=dict(
                color=colors,
                line=dict(width=0)
            ),
            showlegend=True,
            hovertemplate='<b>Spread</b><br>Day %{x}<br>Δ $%{y:.2f}<extra></extra>'
        ), row=2, col=1)
        
        # Add zero line
        fig.add_hline(
            y=0,
            line_width=1,
            line_dash="solid",
            line_color="rgba(255,255,255,0.2)",
            row=2, col=1
        )
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#a1a1aa', family='Inter'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(0,0,0,0)',
            font=dict(size=11)
        ),
        margin=dict(l=10, r=10, t=60, b=10),
        height=520,
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor="rgba(12, 12, 18, 0.95)",
            bordercolor="rgba(255,255,255,0.1)",
            font=dict(color="#f8fafc", size=12)
        )
    )
    
    # Update axes styling
    fig.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.03)', zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.03)', zeroline=False)
    fig.update_yaxes(tickprefix="$", tickfont=dict(size=10), row=1, col=1)
    fig.update_yaxes(tickprefix="$", tickfont=dict(size=10), title_text="Spread", title_font=dict(size=10), row=2, col=1)
    fig.update_xaxes(title_text="Trading Day", title_font=dict(size=10), row=2, col=1)
    
    st.plotly_chart(fig, width='stretch')

    # Extra stocks (fun off-brand names with full metadata)
    if state.extra_stocks:
        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
        st.markdown('<p class="section-title">Extended Market Universe</p>', unsafe_allow_html=True)
        st.markdown('<p class="section-subtitle">Off-brand parody stocks from across all sectors</p>', unsafe_allow_html=True)
        
        # Group stocks by sector
        all_stocks = get_all_stocks()
        
        cols = st.columns(3)
        for idx, stock in enumerate(state.extra_stocks):
            col = cols[idx % 3]
            stock_meta = STOCK_UNIVERSE.get(stock.name, {"sector": "Other", "emoji": "📊", "color": "#8b5cf6", "description": "Stock"})
            with col:
                change = stock.change_percent
                color = "#10b981" if change >= 0 else "#ef4444"
                sector_class = f"sector-{stock_meta.get('sector', 'other').lower().replace(' ', '-')}"
                st.markdown(f"""
                <div class="info-card stock-card {sector_class}" style="border-left: 4px solid {stock_meta.get('color', '#8b5cf6')};">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                                <span style="font-size: 20px;">{stock_meta.get('emoji', '📊')}</span>
                                <span style="font-size: 14px; font-weight: 700; color: var(--text-primary);">{stock.name}</span>
                            </div>
                            <div style="font-size: 10px; padding: 2px 8px; background: var(--bg-glass); border-radius: 12px; color: var(--text-dim); display: inline-block;">{stock_meta.get('sector', 'Other')}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 22px; font-weight: 800; color: var(--text-primary);">${stock.price:.2f}</div>
                            <div style="font-size: 13px; font-weight: 600; color: {color};">{'+' if change >= 0 else ''}{change:.2f}%</div>
                        </div>
                    </div>
                    <div style="margin-top: 10px; font-size: 11px; color: var(--text-dim); line-height: 1.4;">
                        {stock_meta.get('description', '')[:60]}{'...' if len(stock_meta.get('description', '')) > 60 else ''}
                    </div>
                    <div style="margin-top: 8px; display: flex; gap: 12px; font-size: 10px; color: var(--text-muted);">
                        <span>Vol: {stock_meta.get('volatility', 1.0)}x</span>
                        <span>Init: ${stock.initial_price:.2f}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Combined chart for all extra stocks with selector
        if price_data and price_data.get("extra_stocks"):
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            
            # Stock selector
            available_stocks = list(price_data["extra_stocks"].keys())
            selected_stocks = st.multiselect(
                "Select stocks to display",
                options=available_stocks,
                default=available_stocks[:3] if available_stocks else [],
                key="extra_stocks_selector"
            )
            
            if selected_stocks:
                fig_combined = go.Figure()
                
                # Color palette for multiple lines
                colors = ["#8b5cf6", "#3b82f6", "#10b981", "#06b6d4", "#f59e0b", "#ec4899"]
                
                for idx, stock_name in enumerate(selected_stocks):
                    series = price_data["extra_stocks"][stock_name]
                    fig_combined.add_trace(go.Scatter(
                        x=price_data["days"],
                        y=series,
                        name=stock_name,
                        line=dict(color=colors[idx % len(colors)], width=2),
                        hovertemplate=f"{stock_name}: $%{{y:.2f}}<extra></extra>"
                    ))
                
                # Add event markers
                if state.events:
                    severity_colors = {
                        "LOW": "rgba(16,185,129,0.6)",
                        "MEDIUM": "rgba(245,158,11,0.7)",
                        "HIGH": "rgba(239,68,68,0.8)"
                    }
                    event_candidates = [e for e in state.events if e.day <= state.current_day]
                    if not event_candidates:
                        event_candidates = state.events
                    for e in event_candidates[:8]:
                        fig_combined.add_vline(
                            x=e.day,
                            line_width=1,
                            line_dash="dot",
                            line_color=severity_colors.get(e.severity, "rgba(148,163,184,0.6)")
                        )
                
                fig_combined.update_layout(
                    title=dict(text="Extended Market Universe Price Trends", font=dict(size=14, color="#a1a1aa")),
                    xaxis_title="Day",
                    yaxis_title="Price ($)",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=60, r=20, t=50, b=60),
                    height=400,
                    hovermode='x unified',
                    legend=dict(x=0.02, y=0.98, bgcolor='rgba(0,0,0,0.3)', bordercolor='rgba(255,255,255,0.1)', borderwidth=1)
                )
                fig_combined.update_xaxes(showgrid=True, gridwidth=1, gridcolor="rgba(255,255,255,0.05)", zeroline=False)
                fig_combined.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(255,255,255,0.05)", zeroline=False)
                st.plotly_chart(fig_combined, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# PERSONALIZATION TAB
# ═══════════════════════════════════════════════════════════════════════════════

def get_default_custom_agent():
    """Return default custom agent settings."""
    return {
        "enabled": False,
        "name": "",
        "nickname": "",
        "display_name": "Custom Agent",
        "character": "Balanced",
        "herding_level": "Medium",
        "loss_aversion_level": "Medium",
        "overconfidence_level": "Low",
        "anchoring_level": "Medium",
        "risk_tolerance": 50,
        "trading_frequency": "Medium",
        "initial_capital": 10000,
        "strategy_preference": "Mixed",
        "avatar_type": "icon",  # "icon" or "image"
        "avatar_icon": "fox",   # Selected icon name
    }

# Avatar icons with animated SVG representations
AVATAR_ICONS = {
    "fox": {"emoji": "🦊", "name": "Fox", "color": "#f97316", "trait": "Cunning"},
    "bear": {"emoji": "🐻", "name": "Bear", "color": "#78716c", "trait": "Cautious"},
    "bull": {"emoji": "🐂", "name": "Bull", "color": "#10b981", "trait": "Aggressive"},
    "wolf": {"emoji": "🐺", "name": "Wolf", "color": "#6366f1", "trait": "Strategic"},
    "eagle": {"emoji": "🦅", "name": "Eagle", "color": "#eab308", "trait": "Visionary"},
    "owl": {"emoji": "🦉", "name": "Owl", "color": "#8b5cf6", "trait": "Analytical"},
    "shark": {"emoji": "🦈", "name": "Shark", "color": "#3b82f6", "trait": "Ruthless"},
    "lion": {"emoji": "🦁", "name": "Lion", "color": "#f59e0b", "trait": "Bold"},
}

def render_personalize():
    """Render agent personalization page with improved layout."""
    state = engine.get_state()
    
    # Initialize avatar icon state
    if "avatar_icon_selected" not in st.session_state:
        st.session_state.avatar_icon_selected = st.session_state.custom_agent.get("avatar_icon", "fox")
    if "avatar_type" not in st.session_state:
        st.session_state.avatar_type = st.session_state.custom_agent.get("avatar_type", "icon")

    # Header Section
    st.markdown('<p class="section-title">Create Your Agent</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-subtitle">Design a personalized trading agent with unique traits and appearance</p>', unsafe_allow_html=True)
    
    # Main 2-column layout: Settings (left) | Preview (right)
    settings_col, preview_col = st.columns([1.3, 1])
    
    with settings_col:
        # ═══════════════════════════════════════════════════════════════════════
        # LEFT SIDE: SETTINGS PANEL
        # ═══════════════════════════════════════════════════════════════════════
        
        # Section 1: Identity
        with st.expander("👤 **Identity & Avatar**", expanded=True):
            enable = st.toggle("Enable Custom Agent", value=st.session_state.custom_agent.get("enabled", False),
                              help="When enabled, your custom agent will participate in simulations")
            
            name_cols = st.columns(2)
            with name_cols[0]:
                name = st.text_input("Agent Name", value=st.session_state.custom_agent.get("name", ""), 
                                    placeholder="e.g., Rajesh", help="Primary name") or ""
            with name_cols[1]:
                nickname = st.text_input("Title/Nickname", value=st.session_state.custom_agent.get("nickname", ""), 
                                        placeholder='e.g., The Fox', help="Optional title") or ""
            
            st.markdown("**Choose Avatar**")
            avatar_type = st.radio("Avatar Type", ["🎨 Select Icon", "📷 Upload Image"], 
                                   index=0 if st.session_state.avatar_type == "icon" else 1,
                                   horizontal=True, label_visibility="collapsed")
            
            if "Select Icon" in avatar_type:
                st.session_state.avatar_type = "icon"
                st.markdown('<p style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">Click an icon to select your agent\'s avatar</p>', unsafe_allow_html=True)
                
                # Icon selection grid - 4 columns
                icon_cols = st.columns(4)
                for idx, (icon_key, icon_data) in enumerate(AVATAR_ICONS.items()):
                    with icon_cols[idx % 4]:
                        is_selected = st.session_state.avatar_icon_selected == icon_key
                        border_style = f"3px solid {icon_data['color']}" if is_selected else "2px solid rgba(255,255,255,0.1)"
                        bg_style = f"rgba({int(icon_data['color'][1:3], 16)}, {int(icon_data['color'][3:5], 16)}, {int(icon_data['color'][5:7], 16)}, 0.15)" if is_selected else "var(--bg-tertiary)"
                        
                        if st.button(f"{icon_data['emoji']}", key=f"icon_{icon_key}", 
                                    help=f"{icon_data['name']} - {icon_data['trait']}",
                                    type="primary" if is_selected else "secondary"):
                            st.session_state.avatar_icon_selected = icon_key
                            st.rerun()
                        
                        st.markdown(f"<p style='text-align:center; font-size:10px; color:var(--text-muted); margin-top:-8px;'>{icon_data['name']}</p>", unsafe_allow_html=True)
            else:
                st.session_state.avatar_type = "image"
                uploaded_avatar = st.file_uploader("Upload Avatar Image", type=["png", "jpg", "jpeg"], 
                                                   accept_multiple_files=False, key="avatar_upload")
                if uploaded_avatar:
                    st.session_state.custom_agent_avatar = uploaded_avatar.read()
        
        # Section 2: Personality & Strategy
        with st.expander("🧠 **Personality & Strategy**", expanded=True):
            ps_cols = st.columns(2)
            with ps_cols[0]:
                character = st.selectbox("Personality Type", ["Conservative", "Balanced", "Growth-Oriented", "Aggressive"],
                                        index=["Conservative", "Balanced", "Growth-Oriented", "Aggressive"].index(
                                            st.session_state.custom_agent.get("character", "Balanced")),
                                        help="Defines overall trading approach")
            with ps_cols[1]:
                strategy = st.selectbox("Strategy", ["Value Investing", "Momentum", "Contrarian", "Mixed"],
                                       index=["Value Investing", "Momentum", "Contrarian", "Mixed"].index(
                                           st.session_state.custom_agent.get("strategy_preference", "Mixed")),
                                       help="Preferred trading strategy")
        
        # Section 3: Trading Parameters
        with st.expander("📊 **Trading Parameters**", expanded=True):
            risk_tolerance = st.slider("Risk Tolerance", 0, 100, 
                                      st.session_state.custom_agent.get("risk_tolerance", 50),
                                      help="0 = Very Conservative, 100 = Very Aggressive")
            
            param_cols = st.columns(2)
            with param_cols[0]:
                trading_freq = st.selectbox("Trading Frequency", ["Low", "Medium", "High"],
                                           index=["Low", "Medium", "High"].index(
                                               st.session_state.custom_agent.get("trading_frequency", "Medium")))
            with param_cols[1]:
                initial_capital = st.number_input("Initial Capital ($)", min_value=1000, max_value=1000000, 
                                                 value=st.session_state.custom_agent.get("initial_capital", 10000),
                                                 step=1000)
        
        # Section 4: Behavioral Biases
        with st.expander("🧬 **Behavioral Biases**", expanded=False):
            st.markdown('<p style="font-size: 12px; color: var(--text-muted);">Psychological factors affecting decisions</p>', unsafe_allow_html=True)
            bias_cols = st.columns(2)
            with bias_cols[0]:
                herding = st.selectbox("Herding", ["Low", "Medium", "High"], 
                                      index=["Low", "Medium", "High"].index(
                                          st.session_state.custom_agent.get("herding_level", "Medium")),
                                      help="Tendency to follow the crowd")
                loss_aversion = st.selectbox("Loss Aversion", ["Low", "Medium", "High"], 
                                            index=["Low", "Medium", "High"].index(
                                                st.session_state.custom_agent.get("loss_aversion_level", "Medium")))
            with bias_cols[1]:
                overconfidence = st.selectbox("Overconfidence", ["Low", "Medium", "High"], 
                                             index=["Low", "Medium", "High"].index(
                                                 st.session_state.custom_agent.get("overconfidence_level", "Low")))
                anchoring = st.selectbox("Anchoring", ["Low", "Medium", "High"], 
                                        index=["Low", "Medium", "High"].index(
                                            st.session_state.custom_agent.get("anchoring_level", "Medium")))
        
        # Save Button
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        if st.button("💾 Save Agent Configuration", width='stretch', type="primary", key="save_agent_main"):
            display_name = name.strip()
            if nickname.strip():
                display_name = f"{name.strip()} \"{nickname.strip()}\"" if name.strip() else f"\"{nickname.strip()}\""
            st.session_state.custom_agent = {
                "enabled": enable,
                "name": name.strip(),
                "nickname": nickname.strip(),
                "display_name": display_name.strip() or "Custom Agent",
                "character": character,
                "strategy_preference": strategy,
                "risk_tolerance": risk_tolerance,
                "trading_frequency": trading_freq,
                "initial_capital": initial_capital,
                "herding_level": herding,
                "loss_aversion_level": loss_aversion,
                "overconfidence_level": overconfidence,
                "anchoring_level": anchoring,
                "avatar_type": st.session_state.avatar_type,
                "avatar_icon": st.session_state.avatar_icon_selected,
            }
            save_custom_agent_profile()
            st.success("✅ Agent saved! Enable in Controls tab to activate.")
        
        # Profile Management (collapsed)
        with st.expander("📁 **Profile Management**", expanded=False):
            mgmt_cols = st.columns(3)
            with mgmt_cols[0]:
                st.download_button("⬇️ Export", data=json.dumps(st.session_state.custom_agent, indent=2),
                                  file_name="stockai_agent.json", mime="application/json", width='stretch')
            with mgmt_cols[1]:
                if st.button("🔄 Reset", width='stretch', key="reset_agent_profile"):
                    st.session_state.custom_agent = get_default_custom_agent()
                    st.session_state.custom_agent_avatar = None
                    st.session_state.avatar_icon_selected = "fox"
                    save_custom_agent_profile()
                    st.rerun()
            with mgmt_cols[2]:
                uploaded = st.file_uploader("Import", type=["json"], key="profile_import", label_visibility="collapsed")
            if uploaded:
                try:
                    payload = json.loads(uploaded.read().decode("utf-8"))
                    if isinstance(payload, dict):
                        merged = get_default_custom_agent()
                        merged.update(payload)
                        st.session_state.custom_agent = merged
                        st.session_state.avatar_icon_selected = merged.get("avatar_icon", "fox")
                        save_custom_agent_profile()
                        st.success("✅ Imported!")
                        st.rerun()
                except Exception:
                    st.error("Invalid file.")
    
    with preview_col:
        # ═══════════════════════════════════════════════════════════════════════
        # RIGHT SIDE: AGENT PREVIEW CARD
        # ═══════════════════════════════════════════════════════════════════════
        
        is_enabled = st.session_state.custom_agent.get("enabled", False)
        preview_name = st.session_state.custom_agent.get("display_name") or "Custom Agent"
        preview_character = st.session_state.custom_agent.get("character", "Balanced")
        preview_strategy = st.session_state.custom_agent.get("strategy_preference", "Mixed")
        preview_risk = st.session_state.custom_agent.get("risk_tolerance", 50)
        preview_freq = st.session_state.custom_agent.get("trading_frequency", "Medium")
        preview_capital = st.session_state.custom_agent.get("initial_capital", 10000)
        
        # Get selected icon
        icon_key = st.session_state.avatar_icon_selected
        icon_data = AVATAR_ICONS.get(icon_key, AVATAR_ICONS["fox"])
        
        # Status and risk colors
        status_color = "#10b981" if is_enabled else "#6b7280"
        risk_color = "#10b981" if preview_risk < 33 else "#f59e0b" if preview_risk < 66 else "#ef4444"
        risk_label = "Low" if preview_risk < 33 else "Medium" if preview_risk < 66 else "High"
        
        # Preview Card - build HTML parts
        icon_color = icon_data['color']
        icon_emoji = icon_data['emoji'] if st.session_state.avatar_type == 'icon' else '📷'
        icon_trait = icon_data['trait']
        icon_name = icon_data['name']
        status_bg = 'rgba(16,185,129,0.2)' if is_enabled else 'rgba(107,114,128,0.2)'
        status_text = '● ACTIVE' if is_enabled else '○ INACTIVE'
        
        preview_html = f"""
        <style>
            @keyframes rotateGlow {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}
            @keyframes avatarPulse {{ 0%, 100% {{ transform: scale(1); }} 50% {{ transform: scale(1.05); }} }}
        </style>
        <div style="background: linear-gradient(135deg, var(--bg-card) 0%, rgba(30, 30, 44, 0.9) 100%); border: 1px solid var(--border-light); border-radius: 20px; padding: 32px 24px; text-align: center; position: relative; overflow: hidden;">
            <div style="position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: radial-gradient(circle, {icon_color}15 0%, transparent 50%); animation: rotateGlow 10s linear infinite; pointer-events: none;"></div>
            <div style="position: absolute; top: 16px; right: 16px; padding: 6px 14px; background: {status_bg}; border: 1px solid {status_color}50; border-radius: 20px; font-size: 12px; color: {status_color}; font-weight: 600;">{status_text}</div>
            <div style="width: 100px; height: 100px; margin: 16px auto 20px; background: linear-gradient(135deg, {icon_color}30 0%, {icon_color}10 100%); border: 3px solid {icon_color}; border-radius: 24px; display: flex; align-items: center; justify-content: center; font-size: 52px; box-shadow: 0 8px 32px {icon_color}40; animation: avatarPulse 3s ease-in-out infinite;">{icon_emoji}</div>
            <div style="font-size: 28px; font-weight: 800; color: var(--text-primary); margin-bottom: 4px;">{preview_name}</div>
            <div style="display: inline-block; padding: 4px 12px; background: {icon_color}20; border: 1px solid {icon_color}40; border-radius: 12px; font-size: 12px; color: {icon_color}; margin-bottom: 16px;">{icon_trait} {icon_name}</div>
            <div style="font-size: 14px; color: var(--accent-blue); font-weight: 500; margin-bottom: 20px;">{preview_character} • {preview_strategy}</div>
            <div style="display: flex; justify-content: center; gap: 24px; padding: 16px; background: var(--bg-tertiary); border-radius: 12px;">
                <div style="text-align: center;"><div style="font-size: 22px; font-weight: 700; color: {risk_color};">{preview_risk}%</div><div style="font-size: 11px; color: var(--text-muted);">Risk ({risk_label})</div></div>
                <div style="text-align: center;"><div style="font-size: 22px; font-weight: 700; color: var(--text-primary);">{preview_freq}</div><div style="font-size: 11px; color: var(--text-muted);">Frequency</div></div>
                <div style="text-align: center;"><div style="font-size: 22px; font-weight: 700; color: var(--accent-green);">${preview_capital:,.0f}</div><div style="font-size: 11px; color: var(--text-muted);">Capital</div></div>
            </div>
        </div>
        """
        st.markdown(preview_html, unsafe_allow_html=True)
        
        # Custom image display (if uploaded)
        if st.session_state.avatar_type == "image" and st.session_state.custom_agent_avatar:
            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
            st.image(st.session_state.custom_agent_avatar, caption="Custom Avatar", width=150)
        
        # Bias Profile Visualization
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        st.markdown("##### 🧬 Bias Profile")
        
        bias_levels = {"Low": 33, "Medium": 66, "High": 100}
        herding_val = bias_levels.get(st.session_state.custom_agent.get("herding_level", "Medium"), 66)
        loss_val = bias_levels.get(st.session_state.custom_agent.get("loss_aversion_level", "Medium"), 66)
        over_val = bias_levels.get(st.session_state.custom_agent.get("overconfidence_level", "Low"), 33)
        anchor_val = bias_levels.get(st.session_state.custom_agent.get("anchoring_level", "Medium"), 66)
        
        st.markdown(f"""
        <div class="info-card" style="padding: 16px;">
            <div style="margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="font-size: 12px; color: var(--text-secondary);">🐑 Herding</span>
                    <span style="font-size: 12px; color: var(--text-muted);">{st.session_state.custom_agent.get("herding_level", "Medium")}</span>
                </div>
                <div style="height: 6px; background: var(--bg-tertiary); border-radius: 3px; overflow: hidden;">
                    <div style="width: {herding_val}%; height: 100%; background: linear-gradient(90deg, #3b82f6, #8b5cf6); border-radius: 3px; transition: width 0.3s ease;"></div>
                </div>
            </div>
            <div style="margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="font-size: 12px; color: var(--text-secondary);">😰 Loss Aversion</span>
                    <span style="font-size: 12px; color: var(--text-muted);">{st.session_state.custom_agent.get("loss_aversion_level", "Medium")}</span>
                </div>
                <div style="height: 6px; background: var(--bg-tertiary); border-radius: 3px; overflow: hidden;">
                    <div style="width: {loss_val}%; height: 100%; background: linear-gradient(90deg, #10b981, #f59e0b); border-radius: 3px; transition: width 0.3s ease;"></div>
                </div>
            </div>
            <div style="margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="font-size: 12px; color: var(--text-secondary);">💪 Overconfidence</span>
                    <span style="font-size: 12px; color: var(--text-muted);">{st.session_state.custom_agent.get("overconfidence_level", "Low")}</span>
                </div>
                <div style="height: 6px; background: var(--bg-tertiary); border-radius: 3px; overflow: hidden;">
                    <div style="width: {over_val}%; height: 100%; background: linear-gradient(90deg, #f59e0b, #ef4444); border-radius: 3px; transition: width 0.3s ease;"></div>
                </div>
            </div>
            <div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="font-size: 12px; color: var(--text-secondary);">⚓ Anchoring</span>
                    <span style="font-size: 12px; color: var(--text-muted);">{st.session_state.custom_agent.get("anchoring_level", "Medium")}</span>
                </div>
                <div style="height: 6px; background: var(--bg-tertiary); border-radius: 3px; overflow: hidden;">
                    <div style="width: {anchor_val}%; height: 100%; background: linear-gradient(90deg, #6366f1, #ec4899); border-radius: 3px; transition: width 0.3s ease;"></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Live Performance (if agent in simulation)
        if state.agents:
            match = next((a for a in state.agents if a.name == preview_name), None)
            if match:
                st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
                st.markdown("##### 📈 Live Performance")
                pnl_color = "#10b981" if match.pnl_percent >= 0 else "#ef4444"
                st.markdown(f"""
                <div class="info-card" style="padding: 16px; border-left: 4px solid {pnl_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 24px; font-weight: 700; color: {pnl_color};">{format_percent(match.pnl_percent)}</div>
                            <div style="font-size: 12px; color: var(--text-muted);">Return</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 18px; font-weight: 600; color: var(--text-primary);">{format_currency(match.total_value)}</div>
                            <div style="font-size: 12px; color: var(--text-muted);">Total Value</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# AI ADVISOR TAB
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# CREDITS TAB
# ═══════════════════════════════════════════════════════════════════════════════

def render_credits():
    """Render credits page."""
    st.markdown('<p class="section-title">Credits</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-subtitle">Meet the team behind StockAI</p>', unsafe_allow_html=True)

    cols = st.columns(3)
    members = [
        ("Riyan Ozair", "Project Lead", "AI Systems · Frontend · Research"),
        ("Samiullah", "Simulation Engineer", "Market Dynamics · Backend"),
        ("Nabeel Rizwan", "Product & UX", "Interface · Storytelling · Testing")
    ]
    for col, (name, role, skills) in zip(cols, members):
        with col:
            st.markdown(f"""
            <div class="glass-card" style="text-align: center;">
                <div style="font-size: 20px; font-weight: 800; color: var(--text-primary);">{name}</div>
                <div style="font-size: 12px; color: var(--text-muted); margin-top: 6px;">{role}</div>
                <div style="font-size: 12px; color: var(--text-dim); margin-top: 10px;">{skills}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div class="info-card" style="text-align: center;">
        <div style="font-size: 14px; color: var(--text-muted);">Academic Guide</div>
        <div style="font-size: 18px; font-weight: 800; color: var(--text-primary); margin-top: 6px;">Prof. Bushra Siddiqua</div>
        <div style="font-size: 12px; color: var(--text-dim); margin-top: 4px;">Supervision · Research Direction</div>
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# CREDITS PAGE (Standalone - accessed via footer link)
# ═══════════════════════════════════════════════════════════════════════════════

def render_credits_page():
    """Render standalone credits page with back navigation."""
    # Inject styles
    st.markdown(get_all_styles(), unsafe_allow_html=True)
    
    # Back button
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("← Back", type="secondary", key="credits_back"):
            st.session_state.show_credits = False
            st.rerun()
    
    # Header
    st.markdown("""
    <div style="text-align: center; padding: 60px 20px 40px 20px;">
        <div style="font-size: 48px; margin-bottom: 16px;">👥</div>
        <h1 style="font-size: 36px; font-weight: 800; color: #f8fafc; margin: 0;">Meet the Team</h1>
        <p style="font-size: 16px; color: #71717a; margin-top: 12px;">The minds behind StockAI Market Simulation</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Team members
    cols = st.columns(3)
    members = [
        ("Riyan Ozair", "Project Lead", "AI Systems · Frontend · Research", "🧠"),
        ("Samiullah", "Simulation Engineer", "Market Dynamics · Backend", "⚙️"),
        ("Nabeel Rizwan", "Product & UX", "Interface · Storytelling · Testing", "🎨")
    ]
    
    for col, (name, role, skills, emoji) in zip(cols, members):
        with col:
            st.markdown(f"""
            <div style="
                background: rgba(22, 22, 32, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 20px;
                padding: 32px 24px;
                text-align: center;
                transition: all 0.3s ease;
            ">
                <div style="
                    width: 80px;
                    height: 80px;
                    background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 36px;
                    margin: 0 auto 20px auto;
                    box-shadow: 0 8px 24px rgba(139, 92, 246, 0.3);
                ">{emoji}</div>
                <div style="font-size: 22px; font-weight: 800; color: #f8fafc;">{name}</div>
                <div style="
                    font-size: 13px; 
                    color: #8b5cf6; 
                    font-weight: 600;
                    margin-top: 8px;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                ">{role}</div>
                <div style="
                    font-size: 13px; 
                    color: #71717a; 
                    margin-top: 16px;
                    line-height: 1.6;
                ">{skills}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    
    # Academic guide
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(59, 130, 246, 0.1) 100%);
        border: 1px solid rgba(139, 92, 246, 0.2);
        border-radius: 20px;
        padding: 32px;
        text-align: center;
        max-width: 500px;
        margin: 0 auto;
    ">
        <div style="font-size: 14px; color: #8b5cf6; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Academic Supervisor</div>
        <div style="font-size: 24px; font-weight: 800; color: #f8fafc; margin-top: 12px;">Prof. Bushra Siddiqua</div>
        <div style="font-size: 14px; color: #71717a; margin-top: 8px;">Research Direction · Technical Guidance</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    
    # Project info
    st.markdown("""
    <div style="text-align: center; padding: 20px;">
        <div style="font-size: 14px; color: #52525b;">
            Final Year Project • 2025-2026<br>
            Built with ❤️ using Python, Streamlit, and Plotly
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Continue to app button
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🚀 Launch StockAI", type="primary", width='stretch', key="credits_launch"):
            st.session_state.show_credits = False
            st.session_state.app_started = True
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT INTELLIGENCE TAB
# ═══════════════════════════════════════════════════════════════════════════════

def render_agents():
    """Render agent intelligence dashboard."""
    state = engine.get_state()
    
    if not state.agents:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">🤖</div>
            <div class="empty-state-title">No Agent Data</div>
            <div class="empty-state-description">Configure the simulation to see agent data</div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    st.markdown('<p class="section-title">Agent Intelligence</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-subtitle">Deep dive into individual agent profiles and behavior</p>', unsafe_allow_html=True)
    
    # Agent selector
    col1, col2, col3 = st.columns([2, 1, 1])
    
    # Check if custom agent is active
    custom_agent_name = st.session_state.custom_agent.get("display_name", "")
    custom_agent_enabled = st.session_state.custom_agent.get("enabled", False)
    
    with col1:
        agent_options = []
        for a in state.agents[:30]:
            # Add star indicator for custom agent
            if custom_agent_enabled and a.name == custom_agent_name:
                agent_options.append(f"⭐ {a.name} ({a.character}) - YOUR AGENT")
            else:
                agent_options.append(f"{a.name} ({a.character})")
        selected = st.selectbox("Select Agent", agent_options, label_visibility="collapsed")
    
    if selected:
        idx = agent_options.index(selected)
        agent = state.agents[idx]
        is_custom_agent = custom_agent_enabled and agent.name == custom_agent_name
        
        # Agent overview
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        
        # Custom agent highlight banner
        if is_custom_agent:
            st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(168,85,247,0.15)); border: 1px solid rgba(139,92,246,0.3); border-radius: 12px; padding: 12px 16px; margin-bottom: 16px; display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 24px;">⭐</span>
                <div>
                    <div style="font-weight: 700; color: var(--accent-purple);">Your Custom Agent</div>
                    <div style="font-size: 12px; color: var(--text-muted);">This is the personalized agent you created</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Card styling for custom agent
        card_border = "border: 2px solid rgba(139,92,246,0.5);" if is_custom_agent else ""
        card_glow = "box-shadow: 0 0 20px rgba(139,92,246,0.2);" if is_custom_agent else ""
        
        with col1:
            st.markdown(f"""
            <div class="metric-card" style="{card_border} {card_glow}">
                <span class="metric-icon">{'⭐' if is_custom_agent else ''}</span>
                <div class="metric-value metric-blue" style="font-size: 18px;">{agent.name}</div>
                <div class="metric-label">{agent.character}</div>
                <div class="metric-change" style="background: {'var(--accent-red-dim)' if agent.is_bankrupt else 'var(--accent-green-dim)'}; color: {'var(--accent-red)' if agent.is_bankrupt else 'var(--accent-green)'};">
                    <span style="font-size: 10px;">●</span> {'Bankrupt' if agent.is_bankrupt else 'Active'}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            pnl_color = "metric-green" if agent.pnl_percent >= 0 else "metric-red"
            st.markdown(f"""
            <div class="metric-card" style="{card_border} {card_glow}">
                <div class="metric-value {pnl_color}">{format_percent(agent.pnl_percent)}</div>
                <div class="metric-label">Total P&L</div>
                <div class="metric-change" style="background: var(--bg-tertiary);">
                    {format_currency(agent.total_value)}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value metric-green">{format_currency(agent.cash)}</div>
                <div class="metric-label">Cash Balance</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            stock_a_name = state.stock_a.name if state.stock_a else "A"
            stock_b_name = state.stock_b.name if state.stock_b else "B"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value metric-purple">{agent.stock_a_amount + agent.stock_b_amount}</div>
                <div class="metric-label">Total Shares</div>
                <div class="metric-change" style="background: var(--bg-tertiary);">
                    {stock_a_name}: {agent.stock_a_amount} | {stock_b_name}: {agent.stock_b_amount}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
        
        # Behavioral biases and actions
        col1, col2 = st.columns([1, 1.5])
        
        with col1:
            st.markdown("#### Behavioral Profile")
            
            # Calculate behavioral metrics from actual simulation data
            # Calculate win rate from action history
            if agent.action_history:
                buy_actions = [a for a in agent.action_history if a.get("action") == "BUY"]
                win_rate = (len(buy_actions) / len(agent.action_history) * 100) if agent.action_history else 0
            else:
                win_rate = 0
            
            biases = [
                ("🐑", "Herding", engine.state.herding_percentage, "#8b5cf6", "Percentage of agents following crowd behavior"),
                ("😰", "Loss Aversion", (50 if agent.loss_aversion_level == "High" else (33 if agent.loss_aversion_level == "Medium" else 10)), "#ef4444", "Agent's reaction to losses"),
                ("😤", "Overconfidence", agent.pnl_percent if agent.pnl_percent > 0 else min(100, abs(agent.pnl_percent) / 2), "#f59e0b", "Win rate confidence level"),
                ("⚓", "Anchoring", len(agent.action_history) * 5 % 100, "#3b82f6", "Trades influenced by anchoring"),
            ]
            
            for icon, name, value, color, description in biases:
                level_pct = min(100, max(0, value))
                # Determine level text based on percentage
                if level_pct < 33:
                    level_text = "Low"
                elif level_pct < 66:
                    level_text = "Medium"
                else:
                    level_text = "High"
                    
                st.markdown(f"""
                <div class="info-card" style="padding: 16px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                        <span style="font-weight: 600; color: var(--text-primary);">{icon} {name}</span>
                        <span style="font-size: 12px; font-weight: 600; color: {color};">{level_text}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 10px; color: var(--text-dim);">{description}</span>
                        <span style="font-size: 11px; color: {color}; font-weight: 600;">{level_pct:.1f}%</span>
                    </div>
                    <div class="progress-container" style="height: 6px;">
                        <div class="progress-bar" style="width: {level_pct}%; background: {color};"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("#### Recent Trading Activity")
            
            if agent.action_history:
                for action in agent.action_history[-5:][::-1]:
                    action_color = "#10b981" if action["action"] == "BUY" else "#ef4444"
                    action_icon = "📈" if action["action"] == "BUY" else "📉"
                    
                    # Map stock letter to actual stock name
                    stock_letter = action['stock']
                    if stock_letter == "A" and state.stock_a:
                        stock_display_name = state.stock_a.name
                    elif stock_letter == "B" and state.stock_b:
                        stock_display_name = state.stock_b.name
                    else:
                        stock_display_name = stock_letter
                    
                    st.markdown(f"""
                    <div class="info-card" style="border-left: 3px solid {action_color}; padding: 16px; margin-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span style="font-size: 16px; font-weight: 700; color: {action_color};">
                                    {action_icon} {action['action']} {stock_display_name}
                                </span>
                                <div style="font-size: 14px; color: var(--text-secondary); margin-top: 4px;">
                                    {action['amount']} shares @ ${action['price']:.2f}
                                </div>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 11px; color: var(--text-dim);">
                                    Day {action['day']}, Session {action['session']}
                                </div>
                            </div>
                        </div>
                        <p style="margin: 8px 0 0 0; font-size: 13px; color: var(--text-muted); font-style: italic;">
                            "{action.get('reasoning', 'No reasoning recorded')}"
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="empty-state" style="padding: 40px;">
                    <div class="empty-state-icon">📋</div>
                    <div class="empty-state-title">No Trading Activity</div>
                    <div class="empty-state-description">This agent hasn't made any trades yet</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)

        # Global reasoning feed
        st.markdown("#### Agent Reasoning Feed")
        feed = []
        for a in state.agents:
            for action in a.action_history[-10:]:
                # Map stock letter to actual stock name
                stock_letter = action.get("stock", "")
                if stock_letter == "A" and state.stock_a:
                    stock_display_name = state.stock_a.name
                elif stock_letter == "B" and state.stock_b:
                    stock_display_name = state.stock_b.name
                else:
                    stock_display_name = stock_letter
                
                feed.append({
                    "day": action.get("day", 0),
                    "session": action.get("session", 0),
                    "agent": a.name,
                    "action": action.get("action"),
                    "stock": stock_display_name,
                    "reasoning": action.get("reasoning", "No reasoning recorded")
                })

        feed = sorted(feed, key=lambda x: (x["day"], x["session"]), reverse=True)[:12]

        if feed:
            for item in feed:
                st.markdown(f"""
                <div class="info-card" style="padding: 14px 16px;">
                    <div style="display:flex; justify-content: space-between; align-items:center;">
                        <div style="font-weight: 700; color: var(--text-primary);">{item['agent']}</div>
                        <div style="font-size: 11px; color: var(--text-dim);">Day {item['day']} · S{item['session']}</div>
                    </div>
                    <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">{item['action']} {item['stock']}</div>
                    <div style="font-size: 12px; color: var(--text-secondary); margin-top: 6px;">{item['reasoning']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="empty-state" style="padding: 36px;">
                <div class="empty-state-icon">🧠</div>
                <div class="empty-state-title">No Reasoning Yet</div>
                <div class="empty-state-description">Run the simulation to generate agent reasoning</div>
            </div>
            """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# COMPARATIVE ANALYSIS TAB
# ═══════════════════════════════════════════════════════════════════════════════

def render_analysis():
    """Render comparative analysis dashboard."""
    state = engine.get_state()
    
    if not state.agents or state.current_day == 0:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📊</div>
            <div class="empty-state-title">No Analysis Data</div>
            <div class="empty-state-description">Run the simulation to see comparative analysis</div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    st.markdown('<p class="section-title">Comparative Analysis</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-subtitle">Compare strategy performance and identify top performers</p>', unsafe_allow_html=True)
    
    # Strategy performance
    strategies = engine.get_strategy_performance()
    
    strategy_data = []
    for name, data in strategies.items():
        strategy_data.append({
            "Strategy": name,
            "Agents": data["count"],
            "Avg P&L %": data["avg_pnl"],
            "Total Value": data.get("total_value", 0)
        })
    
    df = pd.DataFrame(strategy_data)
    
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        st.markdown("#### Strategy Performance Comparison")
        
        colors = {
            "Conservative": "#10b981",
            "Aggressive": "#ef4444",
            "Balanced": "#3b82f6",
            "Growth-Oriented": "#8b5cf6"
        }
        
        fig = go.Figure()
        
        for _, row in df.iterrows():
            color = colors.get(row["Strategy"], "#64748b")
            fig.add_trace(go.Bar(
                x=[row["Strategy"]],
                y=[row["Avg P&L %"]],
                name=row["Strategy"],
                marker_color=color,
                text=f"{row['Avg P&L %']:.2f}%",
                textposition="outside",
                textfont=dict(size=12, color=color),
                hovertemplate=f"{row['Strategy']}<br>Avg P&L: %{{y:.2f}}%<br>Agents: {row['Agents']}<extra></extra>"
            ))
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#a1a1aa', family='Inter'),
            showlegend=False,
            margin=dict(l=0, r=0, t=20, b=0),
            height=350,
            yaxis=dict(
                title="Average P&L %",
                showgrid=True,
                gridcolor='rgba(255,255,255,0.04)',
                zeroline=True,
                zerolinecolor='rgba(255,255,255,0.1)'
            ),
            xaxis=dict(showgrid=False)
        )
        
        st.plotly_chart(fig, width='stretch')
    
    with col2:
        st.markdown("#### Strategy Distribution")
        
        fig = go.Figure(data=[go.Pie(
            labels=df["Strategy"],
            values=df["Agents"],
            hole=0.55,
            marker_colors=[colors.get(s, "#64748b") for s in df["Strategy"]],
            textinfo='percent',
            textfont=dict(size=12, color='white'),
            hovertemplate='%{label}<br>%{value} agents<br>%{percent}<extra></extra>'
        )])
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#a1a1aa', family='Inter'),
            margin=dict(l=0, r=0, t=20, b=0),
            height=350,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5,
                font=dict(size=11)
            ),
            annotations=[dict(
                text=f"<b>{len(state.agents)}</b><br>Agents",
                x=0.5, y=0.5,
                font=dict(size=14, color='#a1a1aa'),
                showarrow=False
            )]
        )
        
        st.plotly_chart(fig, width='stretch')
    
    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
    
    # Top performers
    st.markdown("#### Top 10 Performers")
    
    # Check for custom agent
    custom_agent_name = st.session_state.custom_agent.get("display_name", "")
    custom_agent_enabled = st.session_state.custom_agent.get("enabled", False)
    
    sorted_agents = sorted(state.agents, key=lambda a: a.pnl_percent, reverse=True)[:10]
    
    for i, agent in enumerate(sorted_agents, 1):
        pnl_color = "#10b981" if agent.pnl_percent >= 0 else "#ef4444"
        is_custom = custom_agent_enabled and agent.name == custom_agent_name
        
        if i == 1:
            medal = "🥇"
            bg = "var(--accent-yellow-dim)"
        elif i == 2:
            medal = "🥈"
            bg = "rgba(192, 192, 192, 0.1)"
        elif i == 3:
            medal = "🥉"
            bg = "rgba(205, 127, 50, 0.1)"
        else:
            medal = f"#{i}"
            bg = "transparent"
        
        # Custom agent highlighting
        if is_custom:
            border_style = "border: 2px solid rgba(139,92,246,0.6); box-shadow: 0 0 15px rgba(139,92,246,0.2);"
            badge = '<span style="background: linear-gradient(135deg, #6366f1, #a855f7); color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; margin-left: 8px; font-weight: 600;">YOUR AGENT</span>'
        else:
            border_style = ""
            badge = ""
        
        st.markdown(f"""
        <div class="agent-row" style="background: {bg if i <= 3 else 'var(--bg-card)'}; {border_style}">
            <div class="agent-rank">{medal}</div>
            <div class="agent-info">
                <div class="agent-name">{'⭐ ' if is_custom else ''}{agent.name}{badge}</div>
                <div class="agent-strategy">{agent.character}</div>
            </div>
            <div class="agent-pnl">
                <div class="agent-pnl-value" style="color: {pnl_color};">
                    {format_percent(agent.pnl_percent)}
                </div>
                <div class="agent-pnl-total">{format_currency(agent.total_value)}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Show custom agent position if not in top 10
    if custom_agent_enabled and custom_agent_name:
        all_sorted = sorted(state.agents, key=lambda a: a.pnl_percent, reverse=True)
        custom_idx = next((i for i, a in enumerate(all_sorted) if a.name == custom_agent_name), None)
        if custom_idx is not None and custom_idx >= 10:
            custom_agent = all_sorted[custom_idx]
            pnl_color = "#10b981" if custom_agent.pnl_percent >= 0 else "#ef4444"
            st.markdown(f"""
            <div style="margin-top: 12px; padding: 8px 12px; background: rgba(139,92,246,0.1); border: 1px dashed rgba(139,92,246,0.4); border-radius: 8px; display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 13px; color: var(--text-muted);">Your agent is ranked</span>
                <span style="font-weight: 700; color: var(--accent-purple);">#{custom_idx + 1}</span>
                <span style="color: var(--text-muted);">|</span>
                <span style="font-weight: 600; color: var(--text-primary);">⭐ {custom_agent.name}</span>
                <span style="margin-left: auto; font-weight: 600; color: {pnl_color};">{format_percent(custom_agent.pnl_percent)}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)

    # Behavioral bias distribution
    st.markdown("#### 🧬 Behavioral Bias Distribution")
    bias_levels = ["Low", "Medium", "High"]
    bias_data = {
        "Herding": [0, 0, 0],
        "Loss Aversion": [0, 0, 0],
        "Overconfidence": [0, 0, 0],
        "Anchoring": [0, 0, 0]
    }

    for a in state.agents:
        bias_data["Herding"][bias_levels.index(a.herding_level)] += 1
        bias_data["Loss Aversion"][bias_levels.index(a.loss_aversion_level)] += 1
        bias_data["Overconfidence"][bias_levels.index(a.overconfidence_level)] += 1
        bias_data["Anchoring"][bias_levels.index(a.anchoring_level)] += 1

    bias_df = pd.DataFrame(bias_data, index=bias_levels)

    fig_bias = go.Figure()
    colors = {"Low": "#10b981", "Medium": "#f59e0b", "High": "#ef4444"}
    for level in bias_levels:
        fig_bias.add_trace(go.Bar(
            name=level,
            x=bias_df.columns,
            y=bias_df.loc[level].values,
            marker_color=colors[level]
        ))

    fig_bias.update_layout(
        barmode='stack',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#a1a1aa', family='Inter'),
        margin=dict(l=0, r=0, t=20, b=0),
        height=320,
        legend=dict(orientation="h", y=-0.2)
    )
    fig_bias.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.04)')
    fig_bias.update_xaxes(showgrid=False)
    st.plotly_chart(fig_bias, width='stretch')

    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)

    # Event timeline
    st.markdown("#### Event Timeline")
    if state.events:
        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            type_filter = st.multiselect("Event Type", ["macro", "sentiment", "corporate"], default=["macro", "sentiment", "corporate"])
        with fcol2:
            severity_filter = st.multiselect("Severity", ["LOW", "MEDIUM", "HIGH"], default=["LOW", "MEDIUM", "HIGH"])
        with fcol3:
            show_manual = st.toggle("Show Manual Only", value=False)

        filtered = []
        for e in state.events:
            if e.event_type not in type_filter or e.severity not in severity_filter:
                continue
            if show_manual and e not in state.manual_events:
                continue
            filtered.append(e)

        if filtered:
            timeline = pd.DataFrame([{
                "Day": e.day,
                "Type": e.event_type.title(),
                "Severity": e.severity,
                "Title": e.title,
                "Impact": e.impact
            } for e in filtered])

            fig = px.scatter(
                timeline,
                x="Day",
                y="Type",
                color="Severity",
                hover_data=["Title", "Impact"],
                color_discrete_map={"LOW": "#10b981", "MEDIUM": "#f59e0b", "HIGH": "#ef4444"}
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#a1a1aa', family='Inter'),
                margin=dict(l=0, r=0, t=20, b=0),
                height=320,
                legend=dict(orientation="h", y=-0.2)
            )
            fig.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.04)')
            fig.update_yaxes(showgrid=False)
            st.plotly_chart(fig, width='stretch')
            st.dataframe(timeline.sort_values("Day"), width='stretch')
        else:
            st.info("No events match the current filters.")
    else:
        st.info("No events yet.")

    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)

    # Off-brand stock analytics
    if state.extra_stocks:
        st.markdown("#### 🧪 Off-Brand Stock Analytics")
        price_data = engine.get_price_history_df()
        if price_data and price_data.get("extra_stocks"):
            analytics = []
            for name, series in price_data["extra_stocks"].items():
                clean = [v for v in series if v is not None]
                if len(clean) < 2:
                    continue
                returns = pd.Series(clean).pct_change().dropna()
                vol = returns.std() * 100
                total = (clean[-1] / clean[0] - 1) * 100
                analytics.append({
                    "Stock": name,
                    "Total Return %": total,
                    "Volatility %": vol,
                    "Last Price": clean[-1]
                })

            if analytics:
                df_extra = pd.DataFrame(analytics).sort_values("Total Return %", ascending=False)
                st.dataframe(df_extra, width='stretch')
            else:
                st.info("Not enough data to compute analytics yet.")

            # Correlation heatmap (A, B, and off-brand stocks)
            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
            st.markdown("#### 🔗 Correlation Heatmap")
            series_map = {
                "Stock A": price_data.get("stock_a", []),
                "Stock B": price_data.get("stock_b", [])
            }
            for name, series in price_data["extra_stocks"].items():
                series_map[name] = series

            df_prices = pd.DataFrame(series_map)
            df_returns = df_prices.pct_change().dropna()
            if df_returns.shape[1] >= 2 and len(df_returns) > 2:
                corr = df_returns.corr()
                fig_corr = px.imshow(
                    corr,
                    text_auto=True,
                    color_continuous_scale=[[0, "#ef4444"], [0.5, "#1f2937"], [1, "#10b981"]],
                    aspect="auto"
                )
                fig_corr.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#a1a1aa', family='Inter'),
                    margin=dict(l=0, r=0, t=30, b=0),
                    height=420
                )
                st.plotly_chart(fig_corr, width='stretch')
            else:
                st.info("Not enough data to compute correlations yet.")
    
    # Summary stats
    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
    
    active = [a for a in state.agents if not a.is_bankrupt and not a.quit]
    bankrupt = [a for a in state.agents if a.is_bankrupt]
    avg_pnl = sum(a.pnl_percent for a in active) / len(active) if active else 0
    
    cols = st.columns(4)
    summary_stats = [
        ("👥", str(len(state.agents)), "Total Agents", "metric-blue"),
        ("✅", str(len(active)), "Still Active", "metric-green"),
        ("💸", str(len(bankrupt)), "Bankrupt", "metric-red"),
        ("📊", format_percent(avg_pnl), "Average P&L", "metric-purple"),
    ]
    
    for col, (icon, value, label, color) in zip(cols, summary_stats):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <span class="metric-icon">{icon}</span>
                <div class="metric-value {color}">{value}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Main application entry point."""
    
    # Landing page
    if not st.session_state.app_started:
        if st.session_state.show_guidelines:
            render_guidelines_page()
        elif st.session_state.show_credits:
            render_credits_page()
        else:
            render_landing_page()
        return
    
    # Main application
    render_header()
    
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    
    # Tab navigation (AI Advisor via floating orb, Credits via footer)
    tabs = st.tabs([
        "📊 Overview",
        "⚙️ Controls",
        "📈 Market",
        "🤖 Agents",
        "📉 Analysis",
        "🎭 My Agent"
    ])
    
    with tabs[0]:
        render_overview()
    
    with tabs[1]:
        render_controls()
    
    with tabs[2]:
        render_market()
    
    with tabs[3]:
        render_agents()
    
    with tabs[4]:
        render_analysis()

    with tabs[5]:
        render_personalize()
    
    # Chatbot UI: use the Streamlit-native fallback by default (floating orb disabled)
    try:
        from chatbot.ui.streamlit_chat import render_streamlit_chat
        render_streamlit_chat(app_context=engine.state)
    except Exception:
        pass  # chatbot is non-critical, fail silently
    
    # Footer with Credits link only (Guidelines moved to header)
    st.markdown("""<div style='height: 40px;'></div>""", unsafe_allow_html=True)
    
    footer_cols = st.columns([4, 1])
    with footer_cols[0]:
        st.markdown("""
        <div style="color: #52525b; font-size: 12px;">
            <strong style="color: #a1a1aa;">StockAI Research Laboratory</strong><br>
            © 2026 Final Year Project · Built with Streamlit & Plotly
        </div>
        """, unsafe_allow_html=True)
    with footer_cols[1]:
        if st.button("👥 Credits", key="footer_credits", width='stretch'):
            st.session_state.show_credits = True
            st.session_state.app_started = False
            st.rerun()

if __name__ == "__main__":
    main()
