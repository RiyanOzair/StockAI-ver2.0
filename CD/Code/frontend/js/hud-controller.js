/**
 * StockAI Phase 4: Cognitive HUD Controller
 * Manages the interactive terminal, voice commands, and HUD FX.
 */

class HUDController {
    constructor() {
        this.terminalActive = false;
        this.hudActive = false;
        this.voiceActive = false;
        this.neuralMapActive = true;
        this.commands = {};
        this.pulses = [];
        this.history = [];
        this.historyIndex = -1;
        
        this.init();
    }

    init() {
        this.createTerminalUI();
        this.createNeuralCanvas();
        this.registerDefaultCommands();
        this.setupEventListeners();
        this.initVoice();
        this.startNeuralAnimation();
        console.log("Cognitive HUD Initialized. Press [~] for Terminal | Speak 'StockAI' for Voice.");
    }

    createTerminalUI() {
        const term = document.createElement('div');
        term.id = 'quantumTerminal';
        term.style.cssText = `
            position: fixed; top: -400px; left: 0; width: 100%; height: 350px;
            background: rgba(10, 10, 15, 0.95); border-bottom: 2px solid var(--lime);
            z-index: 10001; font-family: var(--mono); color: var(--lime);
            padding: 20px; transition: top 0.3s cubic-bezier(0.23, 1, 0.32, 1);
            display: flex; flex-direction: column; box-shadow: 0 10px 30px rgba(0,0,0,0.8);
            backdrop-filter: blur(10px);
        `;

        term.innerHTML = `
            <div style="display:flex; justify-content:space-between; margin-bottom:10px; font-size:12px; opacity:0.6;">
                <span>STOCKAI QUANTUM TERMINAL v4.1</span>
                <span>ESC TO CLOSE</span>
            </div>
            <div id="terminalOutput" style="flex:1; overflow-y:auto; margin-bottom:15px; font-size:13px; line-height:1.5;">
                <div style="color:var(--muted)">Type /help to see available commands.</div>
            </div>
            <div style="display:flex; align-items:center;">
                <span style="margin-right:10px;">></span>
                <input type="text" id="terminalInput" autofocus style="
                    flex:1; background:transparent; border:none; color:var(--lime);
                    outline:none; font-family:var(--mono); font-size:14px;
                " spellcheck="false" autocomplete="off">
            </div>
        `;

        document.body.appendChild(term);
        this.terminal = term;
        this.output = term.querySelector('#terminalOutput');
        this.input = term.querySelector('#terminalInput');
    }

    registerDefaultCommands() {
        this.registerCommand('help', 'List all commands', () => {
            const list = Object.keys(this.commands).map(c => `/${c} - ${this.commands[c].desc}`).join('<br>');
            this.print(`Available Commands:<br>${list}`);
        });

        this.registerCommand('mood', 'Get current market sentiment', async () => {
            try {
                const resp = await fetch('/market/sentiment');
                const data = await resp.json();
                this.print(`REGIME: <span style="color:var(--lime)">${data.regime.toUpperCase()}</span> | SCORE: ${data.mood_score}`);
            } catch (e) {
                this.print('Error fetching sentiment.', 'red');
            }
        });

        this.registerCommand('briefing', 'Trigger strategic voice briefing', () => {
            if (window.voiceBriefing) {
                this.print('Initiating strategic briefing...');
                window.voiceBriefing.triggerBriefing();
            } else {
                this.print('Voice system not found.', 'red');
            }
        });

        this.registerCommand('hud', 'Toggle Haptic HUD Overlay (Matrix Mode)', () => {
            this.toggleHUD();
        });

        this.registerCommand('voice', 'Toggle Voice Command Listening', () => {
            this.toggleVoice();
        });

        this.registerCommand('neural', 'Toggle Agent Neural-Map Visualization', () => {
            this.neuralMapActive = !this.neuralMapActive;
            this.neuralCanvas.style.display = this.neuralMapActive ? 'block' : 'none';
            this.print(`Neural-Map: ${this.neuralMapActive ? 'ENABLED' : 'DISABLED'}`);
        });

        this.registerCommand('clear', 'Clear terminal output', () => {
            this.output.innerHTML = '';
        });
    }

    registerCommand(name, desc, callback) {
        this.commands[name] = { desc, callback };
    }

    setupEventListeners() {
        window.addEventListener('keydown', (e) => {
            if (e.key === '`' || e.key === '~') {
                e.preventDefault();
                this.toggleTerminal();
            } else if (e.key === 'Escape' && this.terminalActive) {
                this.toggleTerminal();
            }
        });

        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const val = this.input.value.trim();
                if (val) this.executeCommand(val);
                this.input.value = '';
            }
        });

        window.addEventListener('marketVolatility', (e) => {
            if (e.detail && Math.abs(e.detail.change) > 0.02) {
                this.screenShake();
            }
        });
        
        window.addEventListener('agentThought', (e) => {
            if (this.neuralMapActive && e.detail) {
                this.createThoughtPulse(e.detail.agentId, e.detail.stockSymbol);
            }
        });
    }

    createNeuralCanvas() {
        const canvas = document.createElement('canvas');
        canvas.id = 'neuralMapCanvas';
        canvas.style.cssText = `
            position: fixed; inset: 0; z-index: 8000;
            pointer-events: none; width: 100%; height: 100%;
        `;
        document.body.appendChild(canvas);
        this.neuralCanvas = canvas;
        this.ctx = canvas.getContext('2d');

        const resize = () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        };
        window.addEventListener('resize', resize);
        resize();
    }

    createThoughtPulse(agentId, stockSymbol) {
        // Handle potential ID mismatch (some UIs use index, others use actual ID)
        const agentEl = document.querySelector(`[data-agent-id="${agentId}"]`) || 
                        document.querySelector(`.agent-card:nth-child(${parseInt(agentId) + 1})`);
        
        // Find stock el - usually in the dashboard heatmap or watchlist
        const stockEl = document.querySelector(`[data-stock-symbol="${stockSymbol}"]`) || 
                        document.querySelector(`.stock-card[data-symbol="${stockSymbol}"]`) ||
                        document.getElementById('priceChart');
        
        if (!agentEl || !stockEl) return;

        const aRect = agentEl.getBoundingClientRect();
        const sRect = stockEl.getBoundingClientRect();

        this.pulses.push({
            progress: 0,
            startX: aRect.left + aRect.width / 2,
            startY: aRect.top + aRect.height / 2,
            endX: sRect.left + sRect.width / 2,
            endY: sRect.top + sRect.height / 2,
            color: 'var(--lime)',
            opacity: 0.8
        });
    }

    startNeuralAnimation() {
        const animate = () => {
            if (this.neuralMapActive) {
                this.ctx.clearRect(0, 0, this.neuralCanvas.width, this.neuralCanvas.height);
                
                for (let i = this.pulses.length - 1; i >= 0; i--) {
                    const p = this.pulses[i];
                    p.progress += 0.015;
                    p.opacity -= 0.005;

                    if (p.progress >= 1 || p.opacity <= 0) {
                        this.pulses.splice(i, 1);
                        continue;
                    }

                    this.ctx.beginPath();
                    this.ctx.strokeStyle = p.color;
                    this.ctx.globalAlpha = p.opacity;
                    this.ctx.lineWidth = 1.5;
                    this.ctx.setLineDash([5, 5]);
                    
                    this.ctx.moveTo(p.startX, p.startY);
                    const curX = p.startX + (p.endX - p.startX) * p.progress;
                    const curY = p.startY + (p.endY - p.startY) * p.progress;
                    this.ctx.lineTo(curX, curY);
                    this.ctx.stroke();
                    this.ctx.setLineDash([]);
                    
                    // Draw a small flare at the tip
                    this.ctx.beginPath();
                    this.ctx.arc(curX, curY, 3, 0, Math.PI * 2);
                    this.ctx.fillStyle = p.color;
                    this.ctx.fill();
                }
            }
            requestAnimationFrame(animate);
        };
        animate();
    }

    toggleTerminal() {
        this.terminalActive = !this.terminalActive;
        this.terminal.style.top = this.terminalActive ? '0' : '-400px';
        if (this.terminalActive) {
            setTimeout(() => this.input.focus(), 100);
            this.vibrate(5);
        }
    }

    executeCommand(input) {
        this.print(`<span style="color:var(--muted)">> ${input}</span>`);
        const parts = input.split(' ');
        const cmdName = parts[0].replace('/', '').toLowerCase();
        const args = parts.slice(1);

        if (this.commands[cmdName]) {
            this.commands[cmdName].callback(args);
        } else {
            this.print(`Command not found: /${cmdName}. Type /help for list.`, 'red');
        }
        this.output.scrollTop = this.output.scrollHeight;
    }

    print(msg, color) {
        const div = document.createElement('div');
        div.innerHTML = msg;
        if (color) div.style.color = color;
        this.output.appendChild(div);
        this.output.scrollTop = this.output.scrollHeight;
    }

    toggleHUD() {
        if (!this.hudOverlay) this.createHUDOverlay();
        this.hudActive = !this.hudActive;
        this.hudOverlay.style.display = this.hudActive ? 'block' : 'none';
        this.print(`HUD Overlay: ${this.hudActive ? 'ENABLED' : 'DISABLED'}`);
    }

    createHUDOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'hapticHudOverlay';
        overlay.style.cssText = `
            position: fixed; inset: 0; z-index: 10000;
            pointer-events: none; display: none;
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.1) 50%), 
                        linear-gradient(90deg, rgba(255, 0, 0, 0.03), rgba(0, 255, 0, 0.01), rgba(0, 0, 255, 0.03));
            background-size: 100% 3px, 3px 100%;
            opacity: 0.4;
        `;
        const glow = document.createElement('div');
        glow.style.cssText = `
            position: absolute; inset: 0;
            box-shadow: inset 0 0 100px rgba(200, 240, 74, 0.1);
            animation: hudPulse 4s infinite alternate;
        `;
        overlay.appendChild(glow);
        document.body.appendChild(overlay);
        this.hudOverlay = overlay;

        const style = document.createElement('style');
        style.textContent = `
            @keyframes hudPulse {
                from { box-shadow: inset 0 0 50px rgba(200, 240, 74, 0.05); }
                to { box-shadow: inset 0 0 150px rgba(200, 240, 74, 0.15); }
            }
            .screen-shake { animation: shake 0.4s cubic-bezier(.36,.07,.19,.97) both; }
            @keyframes shake {
                10%, 90% { transform: translate3d(-1px, 0, 0); }
                20%, 80% { transform: translate3d(2px, 0, 0); }
                30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
                40%, 60% { transform: translate3d(4px, 0, 0); }
            }
        `;
        document.head.appendChild(style);
    }

    screenShake() {
        document.body.classList.add('screen-shake');
        this.vibrate([50, 30, 50]);
        setTimeout(() => document.body.classList.remove('screen-shake'), 400);
    }

    toggleVoice() {
        this.voiceActive = !this.voiceActive;
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            this.print("Voice Recognition not supported in this browser.", "red");
            return;
        }

        if (!this.recognition) {
            this.initVoice();
        }

        if (this.voiceActive) {
            try {
                this.recognition.start();
                this.print("VOICE ORCHESTRATOR: <span style='color:var(--cyan)'>LISTENING...</span>");
                this.showVoiceIndicator(true);
            } catch(e) { console.error(e); }
        } else {
            this.recognition.stop();
            this.print("VOICE ORCHESTRATOR: <span style='color:var(--muted)'>OFF</span>");
            this.showVoiceIndicator(false);
        }
    }

    initVoice() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = false;
        this.recognition.onresult = (event) => {
            const last = event.results.length - 1;
            const text = event.results[last][0].transcript.toLowerCase().trim();
            this.handleVoiceCommand(text);
        };
    }

    handleVoiceCommand(text) {
        this.print(`<span style="color:var(--muted)">[Voice] "${text}"</span>`);
        if (text.includes('briefing')) this.executeCommand('briefing');
        else if (text.includes('start')) window.simStart?.();
        else if (text.includes('stop')) window.simPause?.();
        else if (text.includes('reset')) window.simReset?.();
        else if (text.includes('hud')) this.executeCommand('hud');
        else if (text.includes('terminal')) this.toggleTerminal();
    }

    showVoiceIndicator(active) {
        let indicator = document.getElementById('voiceIndicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'voiceIndicator';
            indicator.style.cssText = `position:fixed; bottom:20px; right:20px; width:12px; height:12px; border-radius:50%; background:var(--cyan); z-index:10002; display:none; animation:voicePulse 1s infinite alternate;`;
            document.body.appendChild(indicator);
        }
        indicator.style.display = active ? 'block' : 'none';
    }

    vibrate(pattern) {
        if (navigator.vibrate) navigator.vibrate(pattern);
    }
}

// Global Instance
window.hudController = new HUDController();
