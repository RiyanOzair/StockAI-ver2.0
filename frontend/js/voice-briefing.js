/**
 * StockAI Voice Briefing Engine
 * Fetches an AI-generated briefing and speaks it using Web Speech Synthesis.
 */

class VoiceBriefing {
    constructor() {
        this.synth = window.speechSynthesis;
        this.isSpeaking = false;
        this.init();
    }

    init() {
        console.log("Voice Briefing Engine Initialized");
        this.createBriefingUI();
    }

    createBriefingUI() {
        const btn = document.createElement('button');
        btn.id = 'briefingToggle';
        btn.innerHTML = '🛡️';
        btn.title = 'Page Briefing';
        btn.style.cssText = `
            position: fixed; bottom: 80px; right: 20px; z-index: 9999;
            background: rgba(0,0,0,0.5); border: 1px solid var(--lime);
            color: var(--lime); padding: 12px; border-radius: 50%;
            cursor: pointer; font-size: 20px; line-height: 1;
            transition: all 0.2s; display: flex; align-items: center; justify-content: center;
        `;
        btn.onclick = () => this.triggerBriefing();
        document.body.appendChild(btn);
    }

    triggerBriefing() {
        if (this.isSpeaking) {
            this.synth.cancel();
            this.isSpeaking = false;
            this.updateUI();
            return;
        }

        const path = window.location.pathname;
        let briefing = "The system is calibrating. ";

        if (path === '/' || path.includes('landing')) {
            briefing += "Welcome to StockAI v2.0. This is the command center for high-fidelity market simulation. From here, you can access the research workspace, the real-time simulator, and the live performance monitor. Explore the features below to understand how our multi-agent systems operate.";
        } else if (path.includes('workspace')) {
            briefing += "You are now in the Research Workspace. This environment is designed for deep-dive analysis. You can configure simulation parameters, manage agent behaviors, and evaluate strategy bots. Use the panels to explore datasets and compare experiment results.";
        } else if (path.includes('app')) {
            briefing += "Welcome to the Simulator Console. This is the live execution environment where you can observe market dynamics in real-time. Monitor agent decision-making, trade executions, and the evolving order book. The system is currently tracking all active market participants.";
        } else if (path.includes('live-market')) {
            briefing += "This is the Live Performance Monitor. It provides a high-level overview of portfolio health and market trends. Track your agent's performance across multiple asset classes including Indian, US, and Crypto markets.";
        } else {
            briefing += "You are exploring the StockAI interface. Systems are standing by for simulation instructions.";
        }

        this.speak(briefing);
    }

    speak(text) {
        this.synth.cancel(); // Stop any current speech
        
        const utterance = new SpeechSynthesisUtterance(text);
        
        // Find a cool robotic/professional voice
        const voices = this.synth.getVoices();
        const preferred = voices.find(v => v.name.includes('Google US English') || v.name.includes('Samantha') || v.lang === 'en-US');
        if (preferred) utterance.voice = preferred;
        
        utterance.rate = 0.95; // Slightly slower for authority
        utterance.pitch = 0.8; // Slightly deeper for "Mission Control" vibe
        
        utterance.onstart = () => {
            this.isSpeaking = true;
            this.updateUI();
            this.pulseUI(true);
        };
        
        utterance.onend = () => {
            this.isSpeaking = false;
            this.updateUI();
            this.pulseUI(false);
        };

        this.synth.speak(utterance);
    }

    updateUI() {
        const btn = document.getElementById('briefingToggle');
        if (this.isSpeaking) {
            btn.style.borderColor = 'var(--magenta)';
            btn.style.color = 'var(--magenta)';
        } else {
            btn.style.borderColor = 'var(--lime)';
            btn.style.color = 'var(--lime)';
        }
    }

    pulseUI(active) {
        const btn = document.getElementById('briefingToggle');
        if (active) {
            btn.animate([
                { boxShadow: '0 0 0px var(--cyan)' },
                { boxShadow: '0 0 15px var(--cyan)' },
                { boxShadow: '0 0 0px var(--cyan)' }
            ], {
                duration: 2000,
                iterations: Infinity
            });
        } else {
            btn.getAnimations().forEach(a => a.cancel());
        }
    }
}

// Global instance
window.voiceBriefing = new VoiceBriefing();
