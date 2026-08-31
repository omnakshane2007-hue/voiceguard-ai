/**
 * VOICEGUARD AI - Real-Time Live Audio Visualizer
 * Renders actual microphone frequency spectrum and time-domain waveforms using Web Audio API.
 */
class AudioVisualizer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');

        this.analyser = null;
        this.dataArray = null;
        this.timeArray = null;
        this.isLive = false;
        
        // Activity & status state
        this.speechActivity = 0.0;
        this.statusState = "SAFE";
        this.phase = 0;
        this.animFrameId = null;

        this.initCanvasDPI();
        window.addEventListener('resize', () => this.initCanvasDPI());
        
        // Start render loop
        this.render = this.render.bind(this);
        this.animFrameId = requestAnimationFrame(this.render);
    }

    initCanvasDPI() {
        if (!this.canvas) return;
        const rect = this.canvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        this.canvas.width = Math.max(100, Math.floor(rect.width * dpr));
        this.canvas.height = Math.max(50, Math.floor(rect.height * dpr));
        this.ctx.scale(dpr, dpr);
        this.width = rect.width;
        this.height = rect.height;
    }

    attachAnalyser(analyserNode) {
        if (!analyserNode) return;
        this.analyser = analyserNode;
        this.analyser.fftSize = 256;
        this.analyser.smoothingTimeConstant = 0.8;
        this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
        this.timeArray = new Uint8Array(this.analyser.fftSize);
        this.isLive = true;
    }

    detachAnalyser() {
        this.analyser = null;
        this.dataArray = null;
        this.timeArray = null;
        this.isLive = false;
        this.speechActivity = 0.0;
    }

    setActivity(speechRatio, statusState) {
        this.speechActivity = typeof speechRatio === 'number' ? speechRatio : 0.0;
        if (statusState) this.statusState = statusState;
    }

    render() {
        if (!this.ctx || !this.width || !this.height) {
            this.animFrameId = requestAnimationFrame(this.render);
            return;
        }

        const ctx = this.ctx;
        const w = this.width;
        const h = this.height;
        const cy = h / 2;

        ctx.clearRect(0, 0, w, h);

        // Determine Theme Color based on risk state
        let barColor = '#0058be'; // Secondary blue
        if (this.statusState === "HIGH_RISK") {
            barColor = '#ba1a1a'; // Crimson Red
        } else if (this.statusState === "SUSPICIOUS") {
            barColor = '#f59e0b'; // Amber
        } else if (this.isLive) {
            barColor = '#10b981'; // Emerald
        }

        // Draw Center Reference Zero Line
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, cy);
        ctx.lineTo(w, cy);
        ctx.stroke();

        const numBars = 48;
        const barWidth = Math.max(2, (w / numBars) - 3);
        const barGap = 3;

        if (this.isLive && this.analyser && this.dataArray) {
            // ── Real Microphone FFT Frequency Data ──
            this.analyser.getByteFrequencyData(this.dataArray);
            const step = Math.floor(this.dataArray.length / numBars);

            for (let i = 0; i < numBars; i++) {
                const val = this.dataArray[i * step] || 0;
                const normalized = val / 255.0;
                const barH = Math.max(3, normalized * (h * 0.85));
                const x = i * (barWidth + barGap) + 4;
                const y = cy - (barH / 2);

                ctx.fillStyle = normalized > 0.08 ? barColor : 'rgba(255, 255, 255, 0.18)';
                ctx.fillRect(x, y, barWidth, barH);
            }
        } else {
            // ── Resting / Standby Waveform (Subtle ambient pulse) ──
            this.phase += 0.025;
            const baseAmp = 3;

            for (let i = 0; i < numBars; i++) {
                const normIdx = i / numBars;
                const bell = Math.sin(normIdx * Math.PI);
                const wave1 = Math.sin(this.phase + i * 0.2);
                const combined = Math.abs(wave1);

                const barH = Math.max(3, bell * combined * baseAmp);
                const x = i * (barWidth + barGap) + 4;
                const y = cy - (barH / 2);

                ctx.fillStyle = 'rgba(255, 255, 255, 0.12)';
                ctx.fillRect(x, y, barWidth, barH);
            }
        }

        this.animFrameId = requestAnimationFrame(this.render);
    }
}

window.AudioVisualizer = AudioVisualizer;
