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
        const container = document.createElement('div');
        container.id = 'briefingContainer';
        container.style.cssText = `
            position: fixed; bottom: 140px; right: 20px; z-index: 9999;
            width: 56px; height: 56px; display: flex; align-items: center; justify-content: center;
        `;

        const pulse = document.createElement('div');
        pulse.style.cssText = `
            position: absolute; width: 100%; height: 100%;
            border-radius: 50%; background: var(--lime); opacity: 0.2;
            animation: core-pulse 3s infinite ease-in-out; pointer-events: none;
        `;

        const ring = document.createElement('div');
        ring.style.cssText = `
            position: absolute; width: 110%; height: 110%;
            border: 1px dashed var(--cyan); border-radius: 50%;
            animation: core-spin 10s linear infinite; opacity: 0.4; pointer-events: none;
        `;

        const btn = document.createElement('button');
        btn.id = 'briefingToggle';
        btn.innerHTML = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L4 5V11C4 16.1 7.4 20.8 12 22C16.6 20.8 20 16.1 20 11V5L12 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M12 8V12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <circle cx="12" cy="15" r="1" fill="currentColor"/>
            </svg>
        `;
        btn.title = 'AI TACTICAL BRIEFING';
        btn.style.cssText = `
            position: relative; width: 48px; height: 48px;
            background: rgba(10, 10, 10, 0.85); border: 2px solid var(--lime);
            color: var(--lime); border-radius: 50%;
            cursor: pointer; display: flex; align-items: center; justify-content: center;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            box-shadow: 0 0 20px rgba(200, 240, 74, 0.2);
            backdrop-filter: blur(8px);
            outline: none;
        `;

        // Add Animations to document if not present
        if (!document.getElementById('briefingStyles')) {
            const styles = document.createElement('style');
            styles.id = 'briefingStyles';
            styles.textContent = `
                @keyframes core-pulse {
                    0%, 100% { transform: scale(1); opacity: 0.2; }
                    50% { transform: scale(1.3); opacity: 0.4; }
                }
                @keyframes core-spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
                @keyframes core-thinking {
                    0% { filter: hue-rotate(0deg) brightness(1); }
                    50% { filter: hue-rotate(90deg) brightness(1.5); }
                    100% { filter: hue-rotate(0deg) brightness(1); }
                }
            `;
            document.head.appendChild(styles);
        }

        btn.onmouseover = () => {
            btn.style.transform = 'scale(1.15) rotate(5deg)';
            btn.style.boxShadow = '0 0 30px var(--lime)';
            ring.style.opacity = '1';
            ring.style.animationDuration = '3s';
        };
        btn.onmouseout = () => {
            btn.style.transform = 'scale(1) rotate(0deg)';
            btn.style.boxShadow = `0 0 20px ${this.isSpeaking ? 'var(--magenta)' : 'var(--lime)'}`;
            ring.style.opacity = '0.4';
            ring.style.animationDuration = '10s';
        };
        
        btn.onclick = () => this.triggerBriefing();
        
        container.appendChild(pulse);
        container.appendChild(ring);
        container.appendChild(btn);
        this.ui = { container, btn, pulse, ring };
        document.body.appendChild(container);
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
        btn.style.animation = 'core-thinking 2s infinite ease-in-out';
        this.ui.ring.style.animationDuration = '1s';
        this.ui.ring.style.borderColor = 'var(--cyan)';

        try {
            const isMoodEnabled = window.moodController && !window.moodController.disabled;
            let briefing = "";

            if (isMoodEnabled) {
                // Fetch the tactical briefing from the mood engine
                const response = await fetch('/market/briefing');
                const data = await response.json();
                briefing = data.briefing || "The system is calibrating. ";
            } else {
                // Explain the current page architecture
                briefing = this.getPageExplanation();
            }
            
            // Add extra context if it's brief
            if (briefing.length < 50) {
                briefing += " All systems are currently nominal.";
            }

            this.speak(briefing);
        } catch (err) {
            console.error("Failed to fetch briefing:", err);
            this.speak("Systems are standing by. Market telemetry is incoming.");
        } finally {
            btn.style.animation = '';
            this.ui.ring.style.animationDuration = '10s';
            this.ui.ring.style.borderColor = 'var(--cyan)';
        }
    }

    getPageExplanation() {
        const path = window.location.pathname;
        if (path.includes('workspace')) {
            return "Architecture Overview: You are in the Research Workspace. This is the orchestration layer where market datasets are calibrated and agent cognitive populations are stress-tested before deployment.";
        } else if (path.includes('app')) {
            return "Simulator Console Active: This environment manages real-time WebSocket streams, order book matching, and agent trade execution cycles in a high-fidelity synthetic market.";
        } else if (path.includes('live-market')) {
            return "Live Monitor Synced: This surface tracks real-world equity data across U.S. and Indian markets, providing a direct comparison between live conditions and simulator benchmarks.";
        } else if (path === '/' || path.includes('landing')) {
            return "StockAI v2.0 Platform: You are viewing the global research ecosystem interface. This platform studies the interplay between autonomous LLM agents and multi-market financial telemetry.";
        }
        return "StockAI is standing by. All systems are operating within nominal research parameters.";
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
        if (!this.ui) return;
        const { btn, pulse } = this.ui;
        const moodToggle = document.getElementById('moodAudioToggle');

        if (this.isSpeaking) {
            btn.style.borderColor = 'var(--magenta)';
            btn.style.color = 'var(--magenta)';
            btn.style.boxShadow = '0 0 25px var(--magenta)';
            pulse.style.background = 'var(--magenta)';
            if (moodToggle) moodToggle.style.display = 'flex';
        } else {
            btn.style.borderColor = 'var(--lime)';
            btn.style.color = 'var(--lime)';
            btn.style.boxShadow = '0 0 20px rgba(200, 240, 74, 0.2)';
            pulse.style.background = 'var(--lime)';
            if (moodToggle) moodToggle.style.display = 'none';
        }
    }

    pulseUI(active) {
        if (!this.ui) return;
        const { btn } = this.ui;
        if (active) {
            btn.animate([
                { transform: 'scale(1)', boxShadow: '0 0 10px var(--magenta)' },
                { transform: 'scale(1.1)', boxShadow: '0 0 30px var(--magenta)' },
                { transform: 'scale(1)', boxShadow: '0 0 10px var(--magenta)' }
            ], {
                duration: 1000,
                iterations: Infinity
            });
        } else {
            btn.getAnimations().forEach(a => a.cancel());
        }
    }
}

// Global instance
window.voiceBriefing = new VoiceBriefing();
