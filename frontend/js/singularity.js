/**
 * StockAI Phase 6: Project Singularity (The Final Frontier)
 * - The Architect: Autonomous narrative generator
 * - Neural Overdrive: Glitch visual effects for consensus/shocks
 * - Prophecy HUD: Sentiment-based market projections
 * - God Mode: Max visual immersion
 */

class ProjectSingularity {
    constructor() {
        this.active = false;
        this.overdrive = false;
        this.prophecyHUD = document.getElementById('prophecyHUD');
        this.architectInterval = null;
        this.lastPrediction = "";
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        console.log("Project Singularity Active. The simulation is now autonomous.");
    }

    setupEventListeners() {
        // Volatility listener for Overdrive
        window.addEventListener('marketVolatility', (e) => {
            if (!this.active) return;
            const change = Math.abs(e.detail.change);
            if (change > 0.08) this.triggerOverdrive();
        });

        // Agent Consensus for Overdrive
        window.addEventListener('agentThought', (e) => {
            if (!this.active) return;
            this.updateProphecy();
        });

        // Shortcut: Alt + S to toggle Singularity
        window.addEventListener('keydown', (e) => {
            if (e.altKey && e.key.toLowerCase() === 's') {
                this.toggle();
            }
        });
    }

    toggle() {
        this.active = !this.active;
        if (this.active) {
            this.prophecyHUD.style.display = 'block';
            this.startArchitect();
            if (window.toast) window.toast("PROJECT SINGULARITY: ONLINE", "var(--cyan)");
            if (window.oraclePulse) window.oraclePulse.speak("Project Singularity engaged. The Architect is now observing.");
        } else {
            this.prophecyHUD.style.display = 'none';
            this.stopArchitect();
            this.stopOverdrive();
            if (window.toast) window.toast("PROJECT SINGULARITY: OFFLINE", "var(--muted)");
        }
    }

    startArchitect() {
        // The Architect generates autonomous events based on market state
        this.architectInterval = setInterval(() => {
            if (Math.random() > 0.7) this.generateArchitectEvent();
        }, 15000);
    }

    stopArchitect() {
        clearInterval(this.architectInterval);
    }

    async generateArchitectEvent() {
        // We use the existing /data/event endpoint but the Architect decides the parameters
        const sentiment = window.state?.market_sentiment || 'neutral';
        const titles = {
            bullish: ["Technological Renaissance", "Global Liquidity Surge", "AI Breakthrough Momentum"],
            bearish: ["Cascading Liquidity Crunch", "Sector De-leveraging", "Algorithmic Panic Curve"],
            neutral: ["Regime Consolidation", "Equilibrium Shift", "Quiet Accumulation Phase"]
        };
        
        const title = titles[sentiment][Math.floor(Math.random() * 3)];
        const impact = (sentiment === 'bullish' ? 1 : -1) * (Math.random() * 5 + 2);
        
        console.log("Architect generating event:", title);

        // ACTUAL API CALL: Injecting the event into the simulation backend
        try {
            const response = await fetch('/data/event', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: title,
                    description: `Autonomous Narrative Shift: ${title}`,
                    severity: 'HIGH',
                    impact_pct: impact,
                    affected_stocks: [] // Broad market impact
                })
            });
            const data = await response.json();
            console.log("Architect Event Injected:", data);
        } catch (e) {
            console.warn("Architect API failure:", e);
        }
        
        // Internal event dispatch for HUD feedback
        window.dispatchEvent(new CustomEvent('simEvent', { 
            detail: { type: 'ARCHITECT', message: `Narrative Shift: ${title}` } 
        }));
    }

    triggerOverdrive() {
        if (this.overdrive) return;
        this.overdrive = true;
        document.body.classList.add('neural-overdrive');
        
        // Add singularity glow to all cards
        document.querySelectorAll('.card').forEach(c => c.classList.add('singularity-glow'));
        
        setTimeout(() => this.stopOverdrive(), 3000);
    }

    stopOverdrive() {
        this.overdrive = false;
        document.body.classList.remove('neural-overdrive');
        document.querySelectorAll('.card').forEach(c => c.classList.remove('singularity-glow'));
    }

    updateProphecy() {
        if (!this.prophecyHUD) return;
        
        // Advanced heuristic for prophecy based on multi-agent signals
        const activeAgents = window.agents?.filter(a => a.status === 'active') || [];
        if (activeAgents.length === 0) return;

        const totalPnL = activeAgents.reduce((s, a) => s + (a.pnl || 0), 0);
        const avgPnL = totalPnL / activeAgents.length;
        const topPerformer = [...activeAgents].sort((a, b) => b.pnl - a.pnl)[0];
        
        const trend = avgPnL > 0 ? "ALGORITHMIC ASCENSION" : "SYSTEMIC DE-RISKING";
        const confidence = Math.min(99, 40 + Math.abs(Math.round(avgPnL / 500)));
        const signal = avgPnL > 0 ? 'LONG_BIAS' : 'SHORT_BIAS';
        
        const prediction = `PROPHECY: ${trend} DETECTED // CONFIDENCE ${confidence}% // SIGNAL: ${signal} // ALPHA: ${topPerformer?.name || 'Architect'}`;
        
        if (prediction !== this.lastPrediction) {
            this.prophecyHUD.textContent = prediction;
            this.lastPrediction = prediction;
        }
    }
}

// Global Instance
window.projectSingularity = new ProjectSingularity();
