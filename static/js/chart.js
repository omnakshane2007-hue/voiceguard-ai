/**
 * VOICEGUARD AI - Telemetry Line Chart Engine (Final Stitch Design System)
 * Lightweight, high-performance Canvas-based real-time confidence telemetry chart.
 */
class TelemetryChart {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        this.history = [];
        this.maxPoints = 28;
        
        // Threshold levels from config
        this.safeThreshold = 0.60;
        this.highRiskThreshold = 0.30;

        this.initCanvasDPI();
        window.addEventListener('resize', () => this.initCanvasDPI());
        this.render();
    }

    initCanvasDPI() {
        if (!this.canvas) return;
        const rect = this.canvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        this.canvas.width = Math.max(100, rect.width * dpr);
        this.canvas.height = Math.max(50, rect.height * dpr);
        this.ctx.scale(dpr, dpr);
        this.width = rect.width;
        this.height = rect.height;
        this.render();
    }

    addPoint(score, smoothedScore) {
        if (score === null || score === undefined || score < 0) return;
        const timestamp = new Date();
        this.history.push({
            time: timestamp,
            score: score,
            smoothed: smoothedScore >= 0 ? smoothedScore : score
        });

        if (this.history.length > this.maxPoints) {
            this.history.shift();
        }
        this.render();
    }

    render() {
        if (!this.ctx || !this.width || !this.height) return;
        const ctx = this.ctx;
        const w = this.width;
        const h = this.height;
        const padLeft = 46;
        const padRight = 16;
        const padTop = 16;
        const padBottom = 22;
        const plotW = w - padLeft - padRight;
        const plotH = h - padTop - padBottom;

        ctx.clearRect(0, 0, w, h);

        // Threshold Background Bands
        // High Risk Band (0.0 to 0.30)
        const yHighRisk = padTop + plotH * (1.0 - this.highRiskThreshold);
        ctx.fillStyle = 'rgba(186, 26, 26, 0.04)';
        ctx.fillRect(padLeft, yHighRisk, plotW, padTop + plotH - yHighRisk);

        // Suspicious Band (0.30 to 0.60)
        const ySafe = padTop + plotH * (1.0 - this.safeThreshold);
        ctx.fillStyle = 'rgba(245, 158, 11, 0.04)';
        ctx.fillRect(padLeft, ySafe, plotW, yHighRisk - ySafe);

        // Safe Band (0.60 to 1.0)
        ctx.fillStyle = 'rgba(16, 185, 129, 0.04)';
        ctx.fillRect(padLeft, padTop, plotW, ySafe - padTop);

        // Grid Lines & Labels
        ctx.strokeStyle = '#e4e2e4';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);

        const gridSteps = [
            { val: 1.0, label: '100%' },
            { val: 0.60, label: '60% (Safe)' },
            { val: 0.30, label: '30% (Risk)' },
            { val: 0.0, label: '0%' }
        ];

        ctx.font = '10px "JetBrains Mono", monospace';
        ctx.fillStyle = '#76777d';
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';

        gridSteps.forEach(step => {
            const y = padTop + plotH * (1.0 - step.val);
            ctx.beginPath();
            ctx.moveTo(padLeft, y);
            ctx.lineTo(padLeft + plotW, y);
            ctx.stroke();
            ctx.fillText(step.label, padLeft - 6, y);
        });

        // Axes Border
        ctx.setLineDash([]);
        ctx.strokeStyle = '#c6c6cd';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padLeft, padTop);
        ctx.lineTo(padLeft, padTop + plotH);
        ctx.lineTo(padLeft + plotW, padTop + plotH);
        ctx.stroke();

        // If no data yet, draw waiting indicator
        if (this.history.length === 0) {
            ctx.fillStyle = '#76777d';
            ctx.textAlign = 'center';
            ctx.font = '11px "Inter", sans-serif';
            ctx.fillText('Awaiting real-time telemetry stream...', padLeft + plotW / 2, padTop + plotH / 2);
            return;
        }

        // Draw Confidence Smoothed Line
        if (this.history.length > 0) {
            ctx.beginPath();
            const stepX = this.maxPoints > 1 ? (plotW / (this.maxPoints - 1)) : plotW;
            const startOffset = (this.maxPoints - this.history.length) * stepX;

            for (let i = 0; i < this.history.length; i++) {
                const pt = this.history[i];
                const x = padLeft + startOffset + i * stepX;
                const y = padTop + plotH * (1.0 - Math.max(0, Math.min(1, pt.smoothed)));
                
                if (i === 0) {
                    ctx.moveTo(x, y);
                } else {
                    const prevPt = this.history[i - 1];
                    const prevX = padLeft + startOffset + (i - 1) * stepX;
                    const prevY = padTop + plotH * (1.0 - Math.max(0, Math.min(1, prevPt.smoothed)));
                    const midX = (prevX + x) / 2;
                    ctx.quadraticCurveTo(prevX, prevY, midX, (prevY + y) / 2);
                }
            }

            const latestScore = this.history[this.history.length - 1].smoothed;
            let strokeColor = '#10b981'; // Safe
            if (latestScore <= this.highRiskThreshold) {
                strokeColor = '#ba1a1a'; // High Risk
            } else if (latestScore <= this.safeThreshold) {
                strokeColor = '#f59e0b'; // Suspicious
            }

            ctx.strokeStyle = strokeColor;
            ctx.lineWidth = 2.5;
            ctx.stroke();

            // Draw point markers
            for (let i = 0; i < this.history.length; i++) {
                const pt = this.history[i];
                const x = padLeft + startOffset + i * stepX;
                const y = padTop + plotH * (1.0 - Math.max(0, Math.min(1, pt.smoothed)));

                ctx.fillStyle = strokeColor;
                ctx.beginPath();
                ctx.arc(x, y, 2.5, 0, Math.PI * 2);
                ctx.fill();
            }

            // Highlight latest point
            const lastIdx = this.history.length - 1;
            const lastX = padLeft + startOffset + lastIdx * stepX;
            const lastY = padTop + plotH * (1.0 - Math.max(0, Math.min(1, latestScore)));

            ctx.fillStyle = strokeColor;
            ctx.beginPath();
            ctx.arc(lastX, lastY, 4.5, 0, Math.PI * 2);
            ctx.fill();

            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 1.5;
            ctx.stroke();
        }
    }
}

window.TelemetryChart = TelemetryChart;
