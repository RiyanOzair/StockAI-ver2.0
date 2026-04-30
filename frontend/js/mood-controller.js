/**
 * StockAI Mood Engine - Frontend Controller
 * Dynamically shifts UI colors and animations based on global market sentiment.
 */

class MoodController {
    constructor() {
        this.pollInterval = 60000; // 1 minute
        this.currentMood = 'neutral';
        this.score = 0.0;
        this.audioEnabled = false;
        this.audioContext = null;
        this.oscillator = null;
        this.gainNode = null;
        
        // Base theme colors (from CSS)
        this.themes = {
            neutral: {
                lime: '#b8ff57',
                cyan: '#00f3ff',
                magenta: '#ff00ff',
                bg: '#0a0a0c',
                speed: '25s'
            },
            bullish: {
                lime: '#00ffaa', // Emerald green
                cyan: '#00ffff',
                magenta: '#ff77ff',
                bg: '#050f0a', // Subtle deep green tint
                speed: '15s' // Faster ticker/animations
            },
            bearish: {
                lime: '#ff3e3e', // Crisis red
                cyan: '#ffaa00', // Alert orange
                magenta: '#ff0000',
                bg: '#0f0505', // Subtle deep red tint
                speed: '40s' // Slower, heavier animations
            }
        };

        this.init();
    }

    async init() {
        console.log("Mood Engine Initialized");
        await this.updateMood();
        setInterval(() => this.updateMood(), this.pollInterval);

        // UI for audio toggle
        this.createAudioToggle();
    }

    async updateMood() {
        try {
            const resp = await fetch('/market/sentiment');
            const data = await resp.json();
            
            this.score = data.mood_score;
            this.applyTheme(data.regime);
            this.updateAudio();
        } catch (e) {
            console.error("Mood update failed:", e);
        }
    }

    applyTheme(regime) {
        if (this.currentMood === regime) return;
        this.currentMood = regime;
        const theme = this.themes[regime];

        console.log(`Applying ${regime} theme (Score: ${this.score})`);

        // Update CSS Variables
        document.documentElement.style.setProperty('--lime', theme.lime);
        document.documentElement.style.setProperty('--cyan', theme.cyan);
        document.documentElement.style.setProperty('--magenta', theme.magenta);
        document.documentElement.style.setProperty('--surface', theme.bg);

        // Update animation speeds for tickers
        const ticker = document.querySelector('.ticker-inner');
        if (ticker) {
            ticker.style.animationDuration = theme.speed;
        }

        // Add class to body for specific overrides
        document.body.classList.remove('mood-neutral', 'mood-bullish', 'mood-bearish');
        document.body.classList.add(`mood-${regime}`);

        // Update any mood labels if they exist
        const label = document.getElementById('marketMoodLabel');
        if (label) {
            label.textContent = regime.toUpperCase();
            label.style.color = theme.lime;
        }
    }

    createAudioToggle() {
        const btn = document.createElement('button');
        btn.id = 'moodAudioToggle';
        btn.innerHTML = '🔊';
        btn.style.cssText = `
            position: fixed; bottom: 20px; left: 20px; z-index: 9999;
            background: rgba(0,0,0,0.5); border: 1px solid var(--border);
            color: var(--text); padding: 8px; border-radius: 50%;
            cursor: pointer; font-size: 18px; width: 40px; height: 40px;
            display: flex; align-items: center; justify-content: center;
            transition: all 0.2s;
        `;
        btn.onclick = () => this.toggleAudio();
        document.body.appendChild(btn);
    }

    toggleAudio() {
        this.audioEnabled = !this.audioEnabled;
        const btn = document.getElementById('moodAudioToggle');
        btn.innerHTML = this.audioEnabled ? '🔊' : '🔇';
        btn.style.borderColor = this.audioEnabled ? 'var(--lime)' : 'var(--border)';

        if (this.audioEnabled) {
            this.startAudio();
        } else {
            this.stopAudio();
        }
    }

    startAudio() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        
        // Create a low drone oscillator
        this.oscillator = this.audioContext.createOscillator();
        this.gainNode = this.audioContext.createGain();
        
        this.oscillator.type = 'sine';
        this.oscillator.frequency.setValueAtTime(60, this.audioContext.currentTime); // Base Freq
        
        this.gainNode.gain.setValueAtTime(0, this.audioContext.currentTime);
        this.gainNode.gain.linearRampToValueAtTime(0.05, this.audioContext.currentTime + 2); // Fade in
        
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
        
        // Shift frequency based on mood score
        // Bullish -> Higher, brighter
        // Bearish -> Lower, darker
        const baseFreq = 60;
        const targetFreq = baseFreq + (this.score * 20);
        
        this.oscillator.frequency.exponentialRampToValueAtTime(
            targetFreq, 
            this.audioContext.currentTime + 3
        );
    }
}

// Global instance
window.moodController = new MoodController();
