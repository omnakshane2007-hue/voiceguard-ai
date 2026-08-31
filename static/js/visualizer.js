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
        this.analyser.smoothingTimeConstant = 0.75;
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
        let barColor = '#10b981'; // Emerald (Default Live)
        let barGlow = 'rgba(16, 185, 129, 0.4)';
        if (this.statusState === "HIGH_RISK") {
            barColor = '#ba1a1a'; // Crimson Red
            barGlow = 'rgba(186, 26, 26, 0.4)';
        } else if (this.statusState === "SUSPICIOUS") {
            barColor = '#f59e0b'; // Amber
            barGlow = 'rgba(245, 158, 11, 0.4)';
        }

        // Draw Center Reference Zero Line
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, cy);
        ctx.lineTo(w, cy);
        ctx.stroke();

        const numBars = 48;
        const barWidth = Math.max(2, (w / numBars) - 2.5);
        const barGap = 2.5;

        if (this.isLive && this.analyser && this.dataArray && this.timeArray) {
            // ── Real Microphone FFT Frequency Data & Waveform ──
            this.analyser.getByteFrequencyData(this.dataArray);
            this.analyser.getByteTimeDomainData(this.timeArray);

            // Compute current frame RMS energy
            let sumSq = 0;
            for (let i = 0; i < this.timeArray.length; i++) {
                const norm = (this.timeArray[i] - 128) / 128.0;
                sumSq += norm * norm;
            }
            const rms = Math.sqrt(sumSq / this.timeArray.length);

            // Frequency spectrum bars with speech frequency enhancement (bins 1-60)
            const binCount = this.dataArray.length;
            for (let i = 0; i < numBars; i++) {
                // Focus more resolution on human vocal range (80Hz - 3400Hz)
                const binIndex = Math.min(binCount - 1, Math.floor(Math.pow(i / numBars, 1.4) * (binCount * 0.85)));
                const val = this.dataArray[binIndex] || 0;
                let normalized = val / 255.0;

                // Boost low-level human speech signals dynamically
                if (rms > 0.002) {
                    normalized = Math.min(1.0, normalized * 1.5 + rms * 0.5);
                }

                const minHeight = 4;
                const barH = Math.max(minHeight, normalized * (h * 0.88));
                const x = i * (barWidth + barGap) + 4;
                const y = cy - (barH / 2);

                if (normalized > 0.06) {
                    ctx.fillStyle = barColor;
                    ctx.shadowColor = barGlow;
                    ctx.shadowBlur = 4;
                } else {
                    ctx.fillStyle = 'rgba(255, 255, 255, 0.16)';
                    ctx.shadowBlur = 0;
                }

                ctx.fillRect(x, y, barWidth, barH);
            }
            ctx.shadowBlur = 0;

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

