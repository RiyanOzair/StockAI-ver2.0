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
            position: fixed; bottom: 140px; right: 20px; z-index: 9999;
            background: rgba(0,0,0,0.7); border: 1.5px solid var(--lime);
            color: var(--lime); padding: 10px; border-radius: 12px;
            cursor: pointer; font-size: 18px; line-height: 1;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); 
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            backdrop-filter: blur(4px);
        `;
        btn.onmouseover = () => {
            btn.style.transform = 'scale(1.1)';
            btn.style.borderColor = 'var(--cyan)';
        };
        btn.onmouseout = () => {
            btn.style.transform = 'scale(1)';
            btn.style.borderColor = this.isSpeaking ? 'var(--magenta)' : 'var(--lime)';
        };
        btn.onclick = () => this.triggerBriefing();
        document.body.appendChild(btn);
    }

    async triggerBriefing() {
        if (this.isSpeaking) {
            this.synth.cancel();
            this.isSpeaking = false;
            this.updateUI();
            return;
        }

        // Add a "loading" state
        const btn = document.getElementById('briefingToggle');
        const originalIcon = btn.innerHTML;
        btn.innerHTML = '⏳';

        try {
            // Fetch the tactical briefing from the mood engine
            const response = await fetch('/market/briefing');
            const data = await response.json();
            
            let briefing = data.briefing || "The system is calibrating. ";
            
            // Add page-specific context if it's not already in the AI briefing
            const path = window.location.pathname;
            if (!briefing.includes('Research') && path.includes('workspace')) {
                briefing += " You are in the Research Workspace, currently monitoring agent cognitive layers.";
            } else if (!briefing.includes('Simulator') && path.includes('app')) {
                briefing += " Viewing the Simulator Console. All execution parameters are nominal.";
            }

            this.speak(briefing);
        } catch (err) {
            console.error("Failed to fetch briefing:", err);
            this.speak("Systems are standing by. Market telemetry is incoming.");
        } finally {
            btn.innerHTML = originalIcon;
        }
    }

    speak(text) {
        this.synth.cancel(); // Stop any current speech
        
        const utterance = new SpeechSynthesisUtterance(text);
        
        // Find a smooth, high-quality voice
        const voices = this.synth.getVoices();
        // Priority: Natural-sounding voices, then Samantha/Google, then any US English
        const preferred = voices.find(v => v.name.includes('Natural')) || 
                          voices.find(v => v.name.includes('Samantha')) || 
                          voices.find(v => v.name.includes('Google US English')) ||
                          voices.find(v => v.lang === 'en-US');
                          
        if (preferred) utterance.voice = preferred;
        
        utterance.rate = 1.0;  // Standard pace
        utterance.pitch = 1.0; // Standard pitch for a smooth, natural tone
        
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
