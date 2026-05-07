# Project Upgrade Plan: "Mind-Blowing Mode"

## Verification Summary
I have verified the existing architecture to ensure these features are 100% compatible and cost exactly $0.
- **Audio API**: `frontend/js/voice-briefing.js` already successfully utilizes the browser's native `window.speechSynthesis` API. We can easily hook this into the WebSocket event stream.
- **3D Topology**: `frontend/js/topology-3d.js` is fully initialized with Three.js. It has a `pulse(sentimentScore)` method that is ready to be hooked into the simulation engine.
- **Event Injection**: The backend expects an `EventInjection` model (`title`, `description`, `severity`, `impact_pct`, `affected_stocks`). We can seamlessly map LLM output directly into this schema.
- **LLM Integration**: `backend/app/core/llm_provider.py` already supports Groq/Gemini calls. We can use this for the "War Room" and "News URL" parsing without any new dependencies.

---

## Detailed Implementation Plan

### 1. The "Reality-to-Simulation" Engine (News Injection)
**Goal:** Allow users to paste a real-world news snippet or headline and instantly generate a formatted market shock.
- **Backend:**
  - Create a new endpoint `POST /simulation/inject/news`.
  - The endpoint takes a text snippet (e.g., *"Tech giants report massive AI chip shortage"*).
  - It uses `llm_provider.py` to prompt the LLM: "Extract this news into a JSON object matching `EventInjection` schema (severity: HIGH, impact_pct: -5.0, affected_stocks: ['AAPL', 'NVDA'])."
  - The endpoint immediately fires this event into the live simulation.
- **Frontend:**
  - Update the Event Injection panel in `workspace.html` to include a "News AI" tab.
  - Add a text area for pasting news. When submitted, show a "Parsing News..." animation, then inject it.

### 2. Immersive Live Play-by-Play (Voice Briefing)
**Goal:** Generate synthetic audio commentary describing the simulation's live events.
- **Frontend:**
  - In the WebSocket message handler (e.g., where `events` are received), detect major events (Regime Shifts, Circuit Breakers, massive market moves).
  - If a major event occurs, pass a short string to `window.voiceBriefing.speak()`.
  - Example: *If the WebSocket receives an event `liquidity_crisis`, the JS triggers: `voiceBriefing.speak("Alert: A severe liquidity crisis has been detected in the market. Agents are expected to deleverage.")`*
  - This requires zero backend changes and costs $0.

### 3. "War Room" (Multi-Agent Debate UI)
**Goal:** Expose the internal "thought process" of the agents as a real-time debate.
- **Backend:**
  - Create a new endpoint `GET /simulation/debate`.
  - When called, it uses `llm_provider` to generate 3 parallel responses given the current market regime:
    1. A "Bull" argument.
    2. A "Bear" argument.
    3. A "Risk Manager" argument.
  - Return the 3 arguments as a JSON list.
- **Frontend:**
  - Add a floating UI panel titled "Agent War Room" next to the Event Tape.
  - When toggled, fetch the debate every 10 seconds and display it like a group chat:
    - **Bull-Bot:** *"Momentum is strong. We need to allocate to Tech."*
    - **Bear-Bot:** *"Volatility is spiking. I'm shorting the bounce."*
    - **Risk-Manager:** *"Reducing overall leverage to 1.5x until VIX stabilizes."*

### 4. 3D WebGL Constellation Activity
**Goal:** Make the platform visually stunning by visualizing trades as 3D lasers.
- **Frontend:**
  - Ensure `topology-3d.js` canvas is visible or accessible via a new "Matrix View" tab in the Simulation Console.
  - Hook into the WebSocket `analytics` and `market_event` payloads.
  - Map specific stocks to 3D nodes. When a massive trade happens, draw an active beam connecting the nodes, or flash the entire WebGL canvas red/green based on the `pulse()` method.
