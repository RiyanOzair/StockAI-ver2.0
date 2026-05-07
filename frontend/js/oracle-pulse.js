/**
 * StockAI Phase 5: Oracle Pulse (The Next Next Level)
 * - Neural Soundscape (Web Audio Procedural Ambient)
 * - Oracle Voice (Native Speech Synthesis Alerts)
 * - Inner Monologue (Matrix-style raw logic stream)
 * - ZERO COST | FULL COMPATIBILITY
 */

class OraclePulse {
    constructor() {
        this.enabled = false;
        this.audioCtx = null;
        this.oscillator = null;
        this.gainNode = null;
        this.volatility = 0;
        this.voices = [];
        
        this.init();
    }

    init() {
        this.createMonologueUI();
        this.setupSpeech();
        this.setupEventListeners();
        console.log("Oracle Pulse Module v2.5 Initialized.");
    }

    createMonologueUI() {
        if (document.getElementById('oracleMonologue')) return;
        
        const container = document.createElement('div');
        container.id = 'oracleMonologue';
        // Premium styling: Glassmorphism, neon accents
        container.style.cssText = `
            position: fixed; right: -320px; top: 100px; width: 300px; height: 65vh;
            background: rgba(10, 10, 15, 0.7); border-left: 2px solid var(--magenta, #ff00ff);
            z-index: 9000; font-family: 'JetBrains Mono', monospace; font-size: 11px;
            color: #fff; padding: 0; overflow: hidden;
            display: flex; flex-direction: column; transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
            backdrop-filter: blur(12px) saturate(180%);
            box-shadow: -20px 0 50px rgba(0,0,0,0.8), inset 0 0 20px rgba(255,0,255,0.05);
            pointer-events: none; border-radius: 12px 0 0 12px;
        `;
        container.innerHTML = `
            <div style="background: rgba(255,0,255,0.1); border-bottom: 1px solid rgba(255,0,255,0.2); padding: 12px 15px; font-weight: 800; letter-spacing: 2px; color: var(--magenta, #ff00ff); text-shadow: 0 0 8px rgba(255,0,255,0.5); display:flex; justify-content:space-between; align-items:center;">
                <span>INNER MONOLOGUE // v2.5</span>
                <span style="font-size:8px; opacity:0.6;">DECODING...</span>
            </div>
            <div id="monologueStream" style="flex:1; overflow-y: auto; padding: 15px; scroll-behavior: smooth;"></div>
            <div style="padding:8px 15px; font-size:8px; color:rgba(255,255,255,0.3); border-top:1px solid rgba(255,255,255,0.05); background: rgba(0,0,0,0.2);">
                ORACLE PULSE // ACTIVE_SYNC_MODE
            </div>
        `;
        document.body.appendChild(container);
        this.monologueUI = container;
        this.stream = container.querySelector('#monologueStream');
    }

    setupSpeech() {
        const loadVoices = () => {
            this.voices = window.speechSynthesis.getVoices();
        };
        loadVoices();
        if (window.speechSynthesis.onvoiceschanged !== undefined) {
            window.speechSynthesis.onvoiceschanged = loadVoices;
        }
    }

    setupEventListeners() {
        window.addEventListener('marketVolatility', (e) => {
            if (!this.enabled) return;
            this.volatility = Math.abs(e.detail.change);
            this.updateAudio();
            
            if (this.volatility > 0.08) {
                this.speak(`Warning. Market instability detected. Volatility delta at ${Math.round(this.volatility * 100)} percent.`);
            }
        });

        window.addEventListener('agentThought', (e) => {
            if (!this.enabled) return;
            this.appendToMonologue(e.detail.agentName, e.detail.thought);
        });

        window.addEventListener('simEvent', (e) => {
            if (!this.enabled) return;
            const type = String(e.detail.type || '').toUpperCase();
            if (['HIGH', 'CRITICAL', 'HALT', 'CRASH'].some(k => type.includes(k) || String(e.detail.message || '').toUpperCase().includes(k))) {
                this.speak(`Oracle Alert: ${e.detail.message}`);
                this.flashMonologue();
            }
        });
    }

    flashMonologue() {
        this.monologueUI.style.borderColor = "#fff";
        setTimeout(() => this.monologueUI.style.borderColor = "var(--magenta, #ff00ff)", 200);
        setTimeout(() => this.monologueUI.style.borderColor = "#fff", 400);
        setTimeout(() => this.monologueUI.style.borderColor = "var(--magenta, #ff00ff)", 600);
    }

    toggle(forceState = null) {
        const newState = forceState !== null ? forceState : !this.enabled;
        if (newState === this.enabled) return this.enabled;
        
        this.enabled = newState;
        if (this.enabled) {
            this.startAudio();
            this.monologueUI.style.right = '0';
            this.monologueUI.style.pointerEvents = 'auto';
            this.speak("Oracle Pulse Synchronization Established.");
            this.toast("ORACLE PULSE: SYNCHRONIZED", "var(--magenta)");
        } else {
            this.stopAudio();
            this.monologueUI.style.right = '-320px';
            this.monologueUI.style.pointerEvents = 'none';
            this.speak("Oracle Pulse Offline.");
            this.toast("ORACLE PULSE: OFFLINE", "var(--muted)");
        }
        return this.enabled;
    }

    startAudio() {
        try {
            if (!this.audioCtx) {
                this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            }
            if (this.audioCtx.state === 'suspended') {
                this.audioCtx.resume();
            }
            this.oscillator = this.audioCtx.createOscillator();
            this.gainNode = this.audioCtx.createGain();

            this.oscillator.type = 'sine';
            this.oscillator.frequency.setValueAtTime(55, this.audioCtx.currentTime); // Low A hum
            
            this.gainNode.gain.setValueAtTime(0, this.audioCtx.currentTime);
            this.gainNode.gain.linearRampToValueAtTime(0.04, this.audioCtx.currentTime + 1.5);

            this.oscillator.connect(this.gainNode);
            this.gainNode.connect(this.audioCtx.destination);
            this.oscillator.start();
        } catch (e) { console.error("Audio Engine Init Failed", e); }
    }

    updateAudio() {
        if (!this.audioCtx || !this.oscillator) return;
        const freq = 55 + (this.volatility * 800);
        this.oscillator.frequency.exponentialRampToValueAtTime(Math.min(freq, 350), this.audioCtx.currentTime + 0.4);
        this.gainNode.gain.linearRampToValueAtTime(0.04 + (this.volatility * 0.15), this.audioCtx.currentTime + 0.4);

        // --- VOLUMETRIC HUD PULSE ---
        if (this.volatility > 0.05) {
            const intensity = Math.min(this.volatility * 150, 200);
            document.body.style.boxShadow = `inset 0 0 ${intensity}px rgba(232, 121, 160, ${this.volatility * 0.4})`;
            setTimeout(() => { document.body.style.boxShadow = 'none'; }, 200);
        }
    }

    stopAudio() {
        if (this.gainNode) {
            this.gainNode.gain.linearRampToValueAtTime(0, this.audioCtx.currentTime + 0.8);
            setTimeout(() => {
                if (this.oscillator) {
                    try { this.oscillator.stop(); } catch(e){}
                }
            }, 800);
        }
    }

    speak(text) {
        if (!window.speechSynthesis || !this.enabled) return;
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.05;
        utterance.pitch = 0.75; 
        
        const voice = this.voices.find(v => ['Google UK English Male', 'David', 'Alex'].some(p => v.name.includes(p))) || this.voices[0];
        if (voice) utterance.voice = voice;

        window.speechSynthesis.speak(utterance);
    }

    appendToMonologue(agent, thought) {
        const entry = document.createElement('div');
        entry.style.cssText = `
            margin-bottom: 15px; opacity: 0; transform: translateY(10px); 
            transition: all 0.5s cubic-bezier(0.23, 1, 0.32, 1); 
            border-left: 1px solid rgba(255, 255, 255, 0.1); padding-left: 10px;
        `;
        entry.innerHTML = `
            <div style="color: var(--magenta, #ff00ff); font-weight: 800; font-size: 9px; margin-bottom: 4px; text-transform: uppercase;">[ ${agent} ]</div>
            <div style="line-height: 1.5; color: rgba(255,255,255,0.85);">${thought}</div>
        `;
        this.stream.appendChild(entry);
        
        setTimeout(() => {
            entry.style.opacity = '1';
            entry.style.transform = 'translateY(0)';
        }, 50);

        this.stream.scrollTop = this.stream.scrollHeight;

        if (this.stream.children.length > 25) {
            this.stream.removeChild(this.stream.firstChild);
        }
    }

    toast(msg, color) {
        if (window.toast) window.toast(msg, color);
    }
}

window.oraclePulse = new OraclePulse();
