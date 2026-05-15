class MoodController {
    constructor() {
        this.pollInterval = 10000; // 10 seconds
        this.currentMood = 'neutral';
        this.score = 0.0;
        this.audioEnabled = false;
        this.audioContext = null;
        this.oscillator = null;
        this.gainNode = null;
        
        const savedState = localStorage.getItem('moodEngineEnabled');
        // Default to ENABLED (disabled = false) if no preference or if 'true'
        this.disabled = (savedState === 'false'); 
        
        this.themes = {
            neutral: { lime: '#b8ff57', cyan: '#00f3ff', magenta: '#ff00ff', bg: '#0a0a0c', speed: '25s' },
            bullish: { lime: '#00ffaa', cyan: '#00ffff', magenta: '#ff77ff', bg: '#050f0a', speed: '15s' },
            bearish: { lime: '#ff3e3e', cyan: '#ffaa00', magenta: '#ff0000', bg: '#0f0505', speed: '40s' }
        };

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.injectHud());
        } else {
            this.injectHud();
        }
        this.init();
    }

    injectHud() {
        if (document.getElementById('moodStatusHud')) return;

        const isCredits = window.location.pathname.includes('credits');
        const isLanding = window.location.pathname === '/' || window.location.pathname.endsWith('landing.html');
        const isSim = window.location.pathname.includes('/app') || window.location.pathname.endsWith('index.html');
        
        const isCenteredPage = isCredits || isLanding || isSim;

        const style = document.createElement('style');
        style.textContent = `
            #moodStatusHud {
                position: fixed;
                top: 60px;
                left: 50%;
                transform: translateX(-50%) translateY(-100px);
                padding: 10px 30px;
                background: rgba(10, 10, 12, 0.95);
                border: 1px solid var(--lime);
                color: var(--lime);
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 3px;
                text-transform: uppercase;
                z-index: 200000;
                opacity: 0;
                pointer-events: none;
                transition: all 0.6s cubic-bezier(0.19, 1, 0.22, 1);
                backdrop-filter: blur(15px);
                box-shadow: 0 10px 30px rgba(0,0,0,0.8), 0 0 20px rgba(74, 222, 128, 0.1);
                display: flex;
                align-items: center;
                gap: 12px;
                border-radius: 4px;
            }
            #moodStatusHud.show { opacity: 1; transform: translateX(-50%) translateY(0); }
            #moodStatusHud .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--lime); animation: moodPulse 1.5s infinite; }
            
            @keyframes moodPulse {
                0% { transform: scale(1); opacity: 1; }
                50% { transform: scale(1.2); opacity: 0.7; }
                100% { transform: scale(1); opacity: 1; }
            }

            #moodGlobalIndicator {
                z-index: 150000;
                background: rgba(10, 10, 12, 0.95);
                backdrop-filter: blur(12px);
                border: 1px solid var(--border);
                display: flex;
                align-items: center;
                gap: 12px;
                font-family: var(--mono, monospace);
                font-size: 10px;
                letter-spacing: 1px;
                transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
            }

            /* POSITIONING LOGIC */
            #moodGlobalIndicator.floating {
                position: fixed;
                top: 0;
                z-index: 200000;
                border-top: none;
                border-radius: 0 0 8px 8px;
                padding: 5px 20px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.6);
            }
            
            #moodGlobalIndicator.floating.centered {
                left: 50%;
                transform: translateX(-50%);
            }

            #moodGlobalIndicator.floating.offset-40 {
                left: calc(40% - 3px);
                transform: translateX(-50%);
            }

            #moodGlobalIndicator.floating.offset-workspace {
                left: calc(40% - 8px);
                transform: translateX(-50%);
            }
            
            #moodGlobalIndicator:hover { background: rgba(20, 20, 25, 0.95); border-color: var(--lime); }
            
            .mood-label-box { color: var(--lime); font-weight: 800; }
            .mood-toggle-btn {
                background: transparent;
                border: 1px solid var(--border);
                color: var(--muted);
                cursor: pointer;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 10px;
                transition: all 0.2s;
            }
            .mood-toggle-btn:hover { border-color: var(--lime); color: var(--lime); }
            .mood-toggle-btn.active { border-color: #ef4e63; color: #ef4e63; }
        `;
        document.head.appendChild(style);

        const indicator = document.createElement('div');
        indicator.id = 'moodGlobalIndicator';
        indicator.innerHTML = `
            <span style="color:var(--muted); opacity:0.6; white-space:nowrap;">NEURAL STATUS</span>
            <span id="marketMoodLabel" class="mood-label-box">NEUTRAL</span>
            <button id="moodToggleBtn" class="mood-toggle-btn" title="Toggle Immersive Engine">⏻</button>
        `;

        // Routing Logic
        const isWorkspace = window.location.pathname.includes('workspace');
        if (isCenteredPage) {
            indicator.classList.add('floating', 'centered');
        } else if (isWorkspace) {
            indicator.classList.add('floating', 'offset-workspace');
        } else {
            indicator.classList.add('floating', 'offset-40');
        }
        document.body.appendChild(indicator);

        const hud = document.createElement('div');
        hud.id = 'moodStatusHud';
        hud.innerHTML = `<span class="dot"></span><span id="moodHudText">SYNCING NEURAL NETWORK...</span>`;
        document.body.appendChild(hud);

        document.getElementById('moodToggleBtn').onclick = (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.toggleMoodEngine();
        };
    }


    showStatus(msg, duration = 3000, isGlitch = false) {
        const hud = document.getElementById('moodStatusHud');
        const text = document.getElementById('moodHudText');
        if (!hud || !text) return;

        text.textContent = msg;
        if (isGlitch) text.classList.add('glitch-text');
        else text.classList.remove('glitch-text');

        hud.classList.add('show');
        if (duration > 0) {
            setTimeout(() => {
                hud.classList.remove('show');
            }, duration);
        }
    }

    async init() {
        if (!this.disabled) {
            await this.updateMood();
        } else {
            this.applyTheme('neutral');
            this.updateToggleState();
        }
        
        setInterval(() => this.updateMood(), this.pollInterval);
        this.createAudioToggle();
    }

    async updateMood() {
        if (this.disabled) return;
        try {
            const endpoint = (window.API || '') + '/market/sentiment';
            const resp = await fetch(endpoint);
            if (!resp.ok) throw new Error("Sentiment fetch failed");
            const data = await resp.json();
            
            this.score = data.mood_score;
            const changed = this.applyTheme(data.regime);
            this.updateAudio();
            
            if (changed) {
                this.showStatus(`MARKET REGIME: ${data.regime.toUpperCase()}`, 4000);
            }

            if (window.marketTopology && typeof window.marketTopology.pulse === 'function') {
                window.marketTopology.pulse(this.score);
            }
        } catch (e) {
            console.error("Mood update failed:", e);
        }
    }

    applyTheme(regime) {
        if (this.currentMood === regime) return false;
        this.currentMood = regime;
        const theme = this.themes[regime];

        document.documentElement.style.setProperty('--lime', theme.lime);
        document.documentElement.style.setProperty('--cyan', theme.cyan);
        document.documentElement.style.setProperty('--magenta', theme.magenta);
        document.documentElement.style.setProperty('--surface', theme.bg);

        const ticker = document.querySelector('.ticker-inner');
        if (ticker) ticker.style.animationDuration = theme.speed;

        document.body.classList.remove('mood-neutral', 'mood-bullish', 'mood-bearish');
        document.body.classList.add(`mood-${regime}`);

        const label = document.getElementById('marketMoodLabel');
        if (label) {
            label.textContent = this.disabled ? 'OFF' : regime.toUpperCase();
            label.style.color = theme.lime;
        }
        return true;
    }
    
    toggleMoodEngine() {
        this.disabled = !this.disabled;
        localStorage.setItem('moodEngineEnabled', !this.disabled);
        this.updateToggleState();
        
        if (this.disabled) {
            this.showStatus("DEACTIVATING IMMERSIVE CORE...", 2000, true);
            this.applyTheme('neutral');
            if (this.audioEnabled) this.stopAudio();
        } else {
            this.showStatus("SYNCING NEURAL NETWORK...", 0, true);
            setTimeout(() => {
                this.updateMood();
                if (this.audioEnabled) this.startAudio();
                this.showStatus("CALIBRATION COMPLETE", 2000);
            }, 2500);
        }
        
        return this.disabled;
    }

    updateToggleState() {
        const btn = document.getElementById('moodToggleBtn');
        const label = document.getElementById('marketMoodLabel');
        if (btn) {
            if (this.disabled) btn.classList.add('active');
            else btn.classList.remove('active');
        }
        if (label && this.disabled) {
            label.textContent = 'OFF';
            label.style.color = 'var(--muted)';
        }
    }

    createAudioToggle() {
        if (document.getElementById('moodAudioToggle')) return;
        const btn = document.createElement('button');
        btn.id = 'moodAudioToggle';
        btn.innerHTML = '🔊';
        btn.style.cssText = `
            position: fixed; bottom: 20px; left: 20px; z-index: 9999;
            background: rgba(0,0,0,0.5); border: 1px solid var(--border);
            color: var(--text); padding: 8px; border-radius: 50%;
            cursor: pointer; font-size: 18px; width: 40px; height: 40px;
            display: none; align-items: center; justify-content: center;
            transition: all 0.2s; backdrop-filter: blur(5px);
        `;
        btn.onclick = () => this.toggleAudio();
        document.body.appendChild(btn);
    }

    toggleAudio() {
        this.audioEnabled = !this.audioEnabled;
        const btn = document.getElementById('moodAudioToggle');
        btn.innerHTML = this.audioEnabled ? '🔊' : '🔇';
        btn.style.borderColor = this.audioEnabled ? 'var(--lime)' : 'var(--border)';
        if (this.audioEnabled) this.startAudio();
        else this.stopAudio();
    }

    startAudio() {
        if (!this.audioContext) this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.oscillator = this.audioContext.createOscillator();
        this.gainNode = this.audioContext.createGain();
        this.oscillator.type = 'sine';
        this.oscillator.frequency.setValueAtTime(60, this.audioContext.currentTime);
        this.gainNode.gain.setValueAtTime(0, this.audioContext.currentTime);
        this.gainNode.gain.linearRampToValueAtTime(0.05, this.audioContext.currentTime + 2);
        this.oscillator.connect(this.gainNode);
        this.gainNode.connect(this.audioContext.destination);
        this.oscillator.start();
        this.updateAudio();
    }

    stopAudio() {
        if (this.gainNode) {
            this.gainNode.gain.linearRampToValueAtTime(0, this.audioContext.currentTime + 1);
            setTimeout(() => {
                if (this.oscillator) {
                    this.oscillator.stop();
                    this.oscillator.disconnect();
                }
            }, 1000);
        }
    }

    updateAudio() {
        if (!this.audioEnabled || !this.oscillator) return;
        const targetFreq = 60 + (this.score * 20);
        this.oscillator.frequency.exponentialRampToValueAtTime(targetFreq, this.audioContext.currentTime + 3);
    }
}

window.moodController = new MoodController();
