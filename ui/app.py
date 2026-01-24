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

# Import simulation engine
from simulation_engine import (
    get_engine, reset_engine, SimulationEngine, 
    SimulationState, AgentState, MarketEvent
)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="StockAI — Market Simulation Lab",
    page_icon="ui/favicon.svg",
    layout="wide",
    initial_sidebar_state="collapsed"
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
if "auto_run" not in st.session_state:
    st.session_state.auto_run = False

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
    --bg-primary: #06060a;
    --bg-secondary: #0c0c12;
    --bg-tertiary: #12121a;
    --bg-card: rgba(22, 22, 32, 0.8);
    --bg-card-solid: #161620;
    --bg-card-hover: rgba(30, 30, 44, 0.9);
    --bg-glass: rgba(255, 255, 255, 0.03);
    
    /* Text */
    --text-primary: #f8fafc;
    --text-secondary: #a1a1aa;
    --text-muted: #71717a;
    --text-dim: #52525b;
    
    /* Accent Colors */
    --accent-green: #10b981;
    --accent-green-dim: rgba(16, 185, 129, 0.15);
    --accent-red: #ef4444;
    --accent-red-dim: rgba(239, 68, 68, 0.15);
    --accent-blue: #3b82f6;
    --accent-blue-dim: rgba(59, 130, 246, 0.15);
    --accent-purple: #8b5cf6;
    --accent-purple-dim: rgba(139, 92, 246, 0.15);
    --accent-yellow: #f59e0b;
    --accent-yellow-dim: rgba(245, 158, 11, 0.15);
    --accent-cyan: #06b6d4;
    --accent-pink: #ec4899;
    
    /* Gradients */
    --gradient-primary: linear-gradient(135deg, #10b981 0%, #3b82f6 50%, #8b5cf6 100%);
    --gradient-green: linear-gradient(135deg, #10b981 0%, #059669 100%);
    --gradient-blue: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
    --gradient-purple: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%);
    --gradient-warm: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%);
    --gradient-dark: linear-gradient(180deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
    
    /* Borders */
    --border-subtle: rgba(255, 255, 255, 0.06);
    --border-light: rgba(255, 255, 255, 0.1);
    --border-medium: rgba(255, 255, 255, 0.15);
    
    /* Shadows */
    --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3);
    --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.4);
    --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.5);
    --shadow-glow-green: 0 0 40px rgba(16, 185, 129, 0.3);
    --shadow-glow-blue: 0 0 40px rgba(59, 130, 246, 0.3);
    --shadow-glow-purple: 0 0 40px rgba(139, 92, 246, 0.3);
    
    /* Spacing */
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 24px;
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
    background: var(--bg-card);
    backdrop-filter: blur(20px);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 24px;
    text-align: center;
    position: relative;
    overflow: hidden;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.metric-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: var(--gradient-primary);
    opacity: 0;
    transition: opacity 0.3s ease;
}

.metric-card:hover {
    transform: translateY(-4px);
    border-color: var(--border-medium);
    box-shadow: var(--shadow-lg);
}

.metric-card:hover::before {
    opacity: 1;
}

.metric-icon {
    font-size: 28px;
    margin-bottom: 12px;
    display: block;
}

.metric-value {
    font-size: 36px;
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
    background: linear-gradient(135deg, #10b981 0%, #3b82f6 50%, #8b5cf6 100%);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.brand-icon svg {
    width: 28px;
    height: 28px;
}

.brand-text h1 {
    margin: 0;
    font-size: 24px;
    font-weight: 800;
    background: var(--gradient-primary);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.2;
}

.brand-text p {
    margin: 2px 0 0 0;
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
    padding: 14px 28px;
    color: var(--text-secondary);
    font-weight: 600;
    font-size: 14px;
    transition: all 0.2s ease;
}

.stTabs [data-baseweb="tab"]:hover {
    background: var(--bg-glass);
    color: var(--text-primary);
}

.stTabs [aria-selected="true"] {
    background: var(--gradient-primary) !important;
    color: white !important;
    box-shadow: var(--shadow-glow-green);
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
    background: var(--gradient-green);
    color: white;
    border: none;
    border-radius: var(--radius-md);
    padding: 14px 28px;
    font-weight: 600;
    font-size: 14px;
    letter-spacing: 0.3px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: var(--shadow-sm);
}

.stButton > button:hover {
    transform: translateY(-3px);
    box-shadow: var(--shadow-glow-green);
}

.stButton > button:active {
    transform: translateY(-1px);
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
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 6px;
    line-height: 0.85;
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
        "IDLE": "⏸️",
        "CONFIGURED": "⚙️",
        "RUNNING": "▶️",
        "PAUSED": "⏯️",
        "COMPLETED": "✅"
    }
    return emojis.get(status, "⏸️")

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
    <p class="landing-subtitle">Agent-Based Market Simulation Platform</p>
    <p class="landing-description">Explore the intersection of behavioral finance and artificial intelligence. Watch autonomous trading agents with unique personalities compete, collaborate, and shape market dynamics in real-time simulations.</p>
    <div class="feature-grid">
        <div class="feature-badge">50+ AI Agents</div>
        <div class="feature-badge">Real-Time Analytics</div>
        <div class="feature-badge">Behavioral Finance</div>
        <div class="feature-badge">Agent BBS Forum</div>
        <div class="feature-badge">Strategy Analysis</div>
        <div class="feature-badge">Live Simulation</div>
    </div>
</div>"""
    
    st.markdown(landing_html, unsafe_allow_html=True)
    
    # Action buttons - tighter layout
    col1, col2, col3, col4, col5 = st.columns([2, 1, 0.2, 1, 2])
    
    with col2:
        if st.button("View Guidelines", use_container_width=True, type="secondary"):
            st.session_state.show_guidelines = True
            st.rerun()
    
    with col4:
        if st.button("Launch Simulation", use_container_width=True, type="primary"):
            st.session_state.app_started = True
            st.rerun()
    
    # Stats showcase - reduced spacing
    st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)
    
    cols = st.columns(4)
    stats = [
        ("📅", "264", "Trading Days/Year", "metric-green"),
        ("🔄", "3", "Sessions Per Day", "metric-blue"),
        ("🎯", "4", "Strategy Types", "metric-purple"),
        ("📊", "∞", "Possibilities", "metric-yellow"),
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
        <div class="tech-item"><span>🐍</span> Python</div>
        <div class="tech-item"><span>📊</span> Streamlit</div>
        <div class="tech-item"><span>📈</span> Plotly</div>
        <div class="tech-item"><span>🧠</span> Multi-Agent</div>
        <div class="tech-item"><span>💹</span> Behavioral Finance</div>
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
    st.markdown('<p class="guidelines-section-title key-features">Key Features</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    features = [
        ("charts", "📊 Real-Time Charts", "Interactive Plotly charts showing price movements, volume, and technical indicators."),
        ("forum", "💬 BBS Forum", "Agents communicate through a bulletin board system, sharing opinions and sentiment."),
        ("events", "📰 Market Events", "Random economic events that impact stock prices and agent behavior."),
        ("leaderboard", "🏆 Leaderboard", "Track top-performing agents and compare strategy effectiveness."),
        ("analysis", "🔬 Behavioral Analysis", "Visualize how biases affect trading decisions and portfolio performance."),
        ("export", "📤 Export Data", "Download simulation results for further analysis in external tools."),
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
        if st.button("🚀 Start Simulation", use_container_width=True, type="primary"):
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
            <div style="text-align: right; padding-top: 8px;">
                <span class="status-badge {status_class}">{status_emoji} {state.status}</span>
                <div style="font-size: 11px; color: var(--text-dim); margin-top: 6px;">{current_time}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown("<div style='padding-top: 6px;'></div>", unsafe_allow_html=True)
            if st.button("📖 Guidelines", key="header_guidelines", use_container_width=True):
                st.session_state.show_guidelines = True
                st.session_state.app_started = False
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# OVERVIEW TAB
# ═══════════════════════════════════════════════════════════════════════════════

def render_overview():
    """Render the overview dashboard."""
    state = engine.get_state()
    
    # Key Metrics Row
    st.markdown('<p class="section-title">📊 Market Overview</p>', unsafe_allow_html=True)
    
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
        st.markdown('<p class="section-title">📈 Stock Performance</p>', unsafe_allow_html=True)
        
        if state.stock_a and len(state.stock_a.price_history) > 1:
            price_data = engine.get_price_history_df()
            
            fig = go.Figure()
            
            # Stock A
            fig.add_trace(go.Scatter(
                x=price_data["days"],
                y=price_data["stock_a"],
                name="Stock A",
                line=dict(color="#10b981", width=3),
                fill='tozeroy',
                fillcolor='rgba(16,185,129,0.08)',
                hovertemplate='Day %{x}<br>Stock A: $%{y:.2f}<extra></extra>'
            ))
            
            # Stock B
            fig.add_trace(go.Scatter(
                x=price_data["days"],
                y=price_data["stock_b"],
                name="Stock B",
                line=dict(color="#3b82f6", width=3),
                fill='tozeroy',
                fillcolor='rgba(59,130,246,0.08)',
                hovertemplate='Day %{x}<br>Stock B: $%{y:.2f}<extra></extra>'
            ))
            
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
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Stock price cards
            pcol1, pcol2 = st.columns(2)
            
            with pcol1:
                change_a = state.stock_a.change_percent
                color_a = "#10b981" if change_a >= 0 else "#ef4444"
                st.markdown(f"""
                <div class="info-card" style="border-left: 4px solid #10b981;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 4px;">STOCK A</div>
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
                change_b = state.stock_b.change_percent
                color_b = "#10b981" if change_b >= 0 else "#ef4444"
                st.markdown(f"""
                <div class="info-card" style="border-left: 4px solid #3b82f6;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 4px;">STOCK B</div>
                            <div style="font-size: 28px; font-weight: 800; color: var(--text-primary);">${state.stock_b.price:.2f}</div>
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
        st.markdown('<p class="section-title">💬 Agent Forum</p>', unsafe_allow_html=True)
        
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
            st.markdown('<p class="section-title">📰 Today\'s Market Events</p>', unsafe_allow_html=True)
            
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
        st.markdown('<p class="section-title">⚙️ Simulation Configuration</p>', unsafe_allow_html=True)
        st.markdown('<p class="section-subtitle">Set up your simulation parameters</p>', unsafe_allow_html=True)
        
        with st.form("config_form", border=False):
            # Agent settings
            st.markdown("**Agent Settings**")
            fcol1, fcol2 = st.columns(2)
            with fcol1:
                agent_count = st.slider("Number of Agents", 10, 100, 50, 5,
                    help="More agents = more complex market dynamics")
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
            
            submitted = st.form_submit_button("💾 Apply Configuration", use_container_width=True)
            
            if submitted:
                engine.configure(
                    agent_count=agent_count,
                    total_days=total_days,
                    volatility=volatility,
                    event_intensity=event_intensity,
                    loan_market_enabled=loan_enabled,
                    random_seed=random_seed
                )
                st.success("✅ Configuration applied successfully!")
                st.rerun()
    
    with col2:
        st.markdown('<p class="section-title">🎮 Simulation Controls</p>', unsafe_allow_html=True)
        st.markdown('<p class="section-subtitle">Run and manage your simulation</p>', unsafe_allow_html=True)
        
        # Control buttons
        btn_cols = st.columns(3)
        
        with btn_cols[0]:
            run_disabled = state.status not in ["CONFIGURED", "PAUSED", "RUNNING"]
            if st.button("▶️ Run Day", use_container_width=True, disabled=run_disabled):
                engine.run_day()
                st.rerun()
        
        with btn_cols[1]:
            if state.status == "RUNNING":
                if st.button("⏸️ Pause", use_container_width=True):
                    engine.pause()
                    st.rerun()
            else:
                if st.button("⏸️ Pause", use_container_width=True, disabled=True):
                    pass
        
        with btn_cols[2]:
            reset_disabled = state.status == "IDLE"
            if st.button("🔄 Reset", use_container_width=True, disabled=reset_disabled):
                engine.reset()
                st.rerun()
        
        # Auto-run
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        
        if state.status in ["CONFIGURED", "RUNNING", "PAUSED"]:
            auto_run = st.toggle("⚡ Auto-advance simulation", value=st.session_state.auto_run,
                help="Automatically advance simulation every 2 seconds")
            st.session_state.auto_run = auto_run
            
            if auto_run and state.status != "COMPLETED":
                engine.run_day()
                time.sleep(1.5)
                st.rerun()
        
        # Status card
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="info-card">
            <h4>📊 Current Status</h4>
            <p><strong>Status:</strong> <span class="status-badge {get_status_class(state.status)}" style="padding: 4px 12px; font-size: 11px;">
                {get_status_emoji(state.status)} {state.status}
            </span></p>
            <p><strong>Progress:</strong> Day {state.current_day} of {state.total_days}</p>
            <p><strong>Active Agents:</strong> {state.active_agents}</p>
            <p><strong>Volatility:</strong> {state.volatility}</p>
            <p><strong>Loan Market:</strong> {'Enabled' if state.loan_market_enabled else 'Disabled'}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Quick actions
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        
        qcol1, qcol2 = st.columns(2)
        with qcol1:
            if st.button("📖 Guidelines", use_container_width=True, type="secondary"):
                st.session_state.show_guidelines = True
                st.session_state.app_started = False
                st.rerun()
        with qcol2:
            if st.button("🏠 Home", use_container_width=True, type="secondary"):
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
    
    st.markdown('<p class="section-title">📈 Market Analysis</p>', unsafe_allow_html=True)
    
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
        <div class="metric-card" style="text-align: left; padding: 28px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 8px; letter-spacing: 1px;">STOCK A</div>
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
                    <div style="font-size: 11px; color: var(--text-dim);">VOLUME</div>
                    <div style="font-size: 14px; font-weight: 600; color: var(--text-secondary);">—</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        change_b = state.stock_b.change_percent
        color_b = "#10b981" if change_b >= 0 else "#ef4444"
        arrow_b = "↑" if change_b >= 0 else "↓"
        
        st.markdown(f"""
        <div class="metric-card" style="text-align: left; padding: 28px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 8px; letter-spacing: 1px;">STOCK B</div>
                    <div style="font-size: 42px; font-weight: 800; color: var(--text-primary);">${state.stock_b.price:.2f}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 24px; font-weight: 700; color: {color_b};">
                        {arrow_b} {abs(change_b):.2f}%
                    </div>
                    <div style="font-size: 12px; color: var(--text-dim); margin-top: 4px;">
                        Initial: ${state.stock_b.initial_price:.2f}
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
                    <div style="font-size: 11px; color: var(--text-dim);">VOLUME</div>
                    <div style="font-size: 14px; font-weight: 600; color: var(--text-secondary);">—</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
    
    # Detailed chart
    price_data = engine.get_price_history_df()
    
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.75, 0.25],
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=("Price History", "Price Spread (B - A)")
    )
    
    # Price lines
    fig.add_trace(go.Scatter(
        x=price_data["days"],
        y=price_data["stock_a"],
        name="Stock A",
        line=dict(color="#10b981", width=2.5),
        hovertemplate='$%{y:.2f}<extra>Stock A</extra>'
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=price_data["days"],
        y=price_data["stock_b"],
        name="Stock B",
        line=dict(color="#3b82f6", width=2.5),
        hovertemplate='$%{y:.2f}<extra>Stock B</extra>'
    ), row=1, col=1)
    
    # Spread
    if len(price_data["stock_a"]) > 0:
        spread = [b - a for a, b in zip(price_data["stock_a"], price_data["stock_b"])]
        colors = ['#10b981' if s >= 0 else '#ef4444' for s in spread]
        
        fig.add_trace(go.Bar(
            x=price_data["days"],
            y=spread,
            name="Spread",
            marker_color=colors,
            showlegend=False,
            hovertemplate='$%{y:.2f}<extra>Spread</extra>'
        ), row=2, col=1)
    
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
            bgcolor='rgba(0,0,0,0)'
        ),
        margin=dict(l=0, r=0, t=60, b=0),
        height=500,
        hovermode='x unified'
    )
    
    fig.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.04)')
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.04)')
    fig.update_yaxes(tickprefix="$", row=1, col=1)
    fig.update_yaxes(tickprefix="$", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)

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
    
    st.markdown('<p class="section-title">🤖 Agent Intelligence</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-subtitle">Deep dive into individual agent profiles and behavior</p>', unsafe_allow_html=True)
    
    # Agent selector
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        agent_options = [f"{a.name} ({a.character})" for a in state.agents[:30]]
        selected = st.selectbox("Select Agent", agent_options, label_visibility="collapsed")
    
    if selected:
        idx = agent_options.index(selected)
        agent = state.agents[idx]
        
        # Agent overview
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <span class="metric-icon">👤</span>
                <div class="metric-value metric-blue" style="font-size: 18px;">{agent.name}</div>
                <div class="metric-label">{agent.character}</div>
                <div class="metric-change" style="background: {'var(--accent-red-dim)' if agent.is_bankrupt else 'var(--accent-green-dim)'}; color: {'var(--accent-red)' if agent.is_bankrupt else 'var(--accent-green)'};">
                    {'🔴 Bankrupt' if agent.is_bankrupt else '🟢 Active'}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            pnl_color = "metric-green" if agent.pnl_percent >= 0 else "metric-red"
            st.markdown(f"""
            <div class="metric-card">
                <span class="metric-icon">💰</span>
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
                <span class="metric-icon">💵</span>
                <div class="metric-value metric-green">{format_currency(agent.cash)}</div>
                <div class="metric-label">Cash Balance</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <span class="metric-icon">📊</span>
                <div class="metric-value metric-purple">{agent.stock_a_amount + agent.stock_b_amount}</div>
                <div class="metric-label">Total Shares</div>
                <div class="metric-change" style="background: var(--bg-tertiary);">
                    A: {agent.stock_a_amount} | B: {agent.stock_b_amount}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
        
        # Behavioral biases and actions
        col1, col2 = st.columns([1, 1.5])
        
        with col1:
            st.markdown("#### 🧠 Behavioral Profile")
            
            biases = [
                ("🐑", "Herding", agent.herding_level, "#8b5cf6"),
                ("😰", "Loss Aversion", agent.loss_aversion_level, "#ef4444"),
                ("😤", "Overconfidence", agent.overconfidence_level, "#f59e0b"),
                ("⚓", "Anchoring", agent.anchoring_level, "#3b82f6"),
            ]
            
            for icon, name, level, color in biases:
                level_pct = {"LOW": 25, "MEDIUM": 50, "HIGH": 75}.get(level, 50)
                st.markdown(f"""
                <div class="info-card" style="padding: 16px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-weight: 600; color: var(--text-primary);">{icon} {name}</span>
                        <span style="font-size: 12px; font-weight: 600; color: {color};">{level}</span>
                    </div>
                    <div class="progress-container" style="height: 6px;">
                        <div class="progress-bar" style="width: {level_pct}%; background: {color};"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("#### 📋 Recent Trading Activity")
            
            if agent.action_history:
                for action in agent.action_history[-5:][::-1]:
                    action_color = "#10b981" if action["action"] == "BUY" else "#ef4444"
                    action_icon = "📈" if action["action"] == "BUY" else "📉"
                    
                    st.markdown(f"""
                    <div class="info-card" style="border-left: 3px solid {action_color}; padding: 16px; margin-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span style="font-size: 16px; font-weight: 700; color: {action_color};">
                                    {action_icon} {action['action']} {action['stock']}
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
    
    st.markdown('<p class="section-title">📉 Comparative Analysis</p>', unsafe_allow_html=True)
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
        
        st.plotly_chart(fig, use_container_width=True)
    
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
        
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
    
    # Top performers
    st.markdown("#### 🏆 Top 10 Performers")
    
    sorted_agents = sorted(state.agents, key=lambda a: a.pnl_percent, reverse=True)[:10]
    
    for i, agent in enumerate(sorted_agents, 1):
        pnl_color = "#10b981" if agent.pnl_percent >= 0 else "#ef4444"
        
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
        
        st.markdown(f"""
        <div class="agent-row" style="background: {bg if i <= 3 else 'var(--bg-card)'};">
            <div class="agent-rank">{medal}</div>
            <div class="agent-info">
                <div class="agent-name">{agent.name}</div>
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
        else:
            render_landing_page()
        return
    
    # Main application
    render_header()
    
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    
    # Tab navigation
    tabs = st.tabs([
        "📊 Overview",
        "⚙️ Controls",
        "📈 Market",
        "🤖 Agents",
        "📉 Analysis"
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
    
    # Footer
    st.markdown("""
    <div class="app-footer">
        <div class="footer-brand">StockAI Research Laboratory</div>
        <div class="footer-links">
            <a href="#">Documentation</a>
            <a href="#">GitHub</a>
            <a href="#">Contact</a>
        </div>
        <div class="footer-copyright">
            © 2026 Final Year Project · Built with Streamlit & Plotly
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
