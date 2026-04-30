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
        btn.innerHTML = '🛡️ BRIEFING';
        btn.style.cssText = `
            position: fixed; bottom: 80px; left: 20px; z-index: 9999;
            background: rgba(0,0,0,0.5); border: 1px solid var(--lime);
            color: var(--lime); padding: 8px 16px; border-radius: 4px;
            cursor: pointer; font-size: 11px; font-family: var(--mono);
            letter-spacing: 1px; transition: all 0.2s;
        `;
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

        const btn = document.getElementById('briefingToggle');
        btn.innerHTML = '⏳ GENERATING...';
        btn.style.borderColor = 'var(--cyan)';
        btn.style.color = 'var(--cyan)';

        try {
            const resp = await fetch('/market/briefing');
            const data = await resp.json();
            
            if (data.briefing) {
                this.speak(data.briefing);
            } else {
                this.speak("Strategic intelligence currently unavailable. Maintain your position.");
            }
        } catch (e) {
            console.error("Briefing failed:", e);
            this.speak("Communication link disrupted. Data feed unstable.");
        }
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
            btn.innerHTML = '⏹️ STOP BRIEF';
            btn.style.borderColor = 'var(--magenta)';
            btn.style.color = 'var(--magenta)';
        } else {
            btn.innerHTML = '🛡️ BRIEFING';
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
