/**
 * VOICEGUARD AI - Main Dashboard Controller (Final Stitch Design System)
 * Connects real backend AASIST neural telemetry, handles file inference,
 * manages responsive tab routing, session history logging, and CSV export.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Visualizers & Charts
    const visualizer = new AudioVisualizer('waveformCanvas');
    const liveConsoleVisualizer = new AudioVisualizer('liveConsoleCanvas');
    const chart = new TelemetryChart('scoreChart');

    // 2. Session State Variables
    let currentStatus = "SAFE";
    let lastProcessedChunk = 0;
    let lastTotalChunk = 0;
    let lastStatus = null;
    const sessionLogs = [];
    let activeTelemetryFilter = 'ALL';
    let telemetrySearchQuery = '';
    let selectedAudioFile = null;

    // 3. UI References
    const elements = {
        // Top Nav & Header
        mainNav: document.getElementById('mainNav'),
        navButtons: document.querySelectorAll('.nav-tab-btn'),
        tabContents: document.querySelectorAll('.tab-content'),
        sysDot: document.getElementById('sysDot'),
        sysText: document.getElementById('sysText'),
        // Header & Live Controls
        headerMicBtn: document.getElementById('headerMicBtn'),
        topMicDot: document.getElementById('topMicDot'),
        topMicText: document.getElementById('topMicText'),
        topBackendDot: document.getElementById('topBackendDot'),
        topBackendText: document.getElementById('topBackendText'),
        btnLiveToggleOverview: document.getElementById('btnLiveToggleOverview'),
        btnLiveToggleOverviewText: document.getElementById('btnLiveToggleOverviewText'),
        liveStatusBadgeOverview: document.getElementById('liveStatusBadgeOverview'),
        btnLiveToggleConsole: document.getElementById('btnLiveToggleConsole'),
        btnLiveToggleConsoleText: document.getElementById('btnLiveToggleConsoleText'),
        liveBackendStatusPill: document.getElementById('liveBackendStatusPill'),
        liveLatencyPill: document.getElementById('liveLatencyPill'),
        liveErrorBanner: document.getElementById('liveErrorBanner'),
        liveErrorText: document.getElementById('liveErrorText'),
        liveActivePipelineText: document.getElementById('liveActivePipelineText'),
        liveModelsDetail: document.getElementById('liveModelsDetail'),
        liveConsoleStreamStatus: document.getElementById('liveConsoleStreamStatus'),
        liveWaveformMeta: document.getElementById('liveWaveformMeta'),

        // Overview: Hero Threat Gauge
        heroGaugeCircle: document.getElementById('heroGaugeCircle'),
        heroScoreText: document.getElementById('heroScoreText'),
        heroScoreLabel: document.getElementById('heroScoreLabel'),
        heroRiskBadge: document.getElementById('heroRiskBadge'),
        heroRiskDot: document.getElementById('heroRiskDot'),
        heroRiskText: document.getElementById('heroRiskText'),
        heroSubtext: document.getElementById('heroSubtext'),

        // Overview: Detection Pipeline Nodes
        pipeN1: document.getElementById('pipeN1'),
        pipeN2: document.getElementById('pipeN2'),
        pipeN3: document.getElementById('pipeN3'),
        pipeN4: document.getElementById('pipeN4'),
        pipeN5: document.getElementById('pipeN5'),
        pipeDot1: document.getElementById('pipeDot1'),
        pipeDot2: document.getElementById('pipeDot2'),
        pipeDot3: document.getElementById('pipeDot3'),
        pipeDot4: document.getElementById('pipeDot4'),
        pipeDot5: document.getElementById('pipeDot5'),

        // Overview: Latest Analysis Stream
        telemetryStreamList: document.getElementById('telemetryStreamList'),
        telemetryStartupPrompt: document.getElementById('telemetryStartupPrompt'),

        // Live Detection Tab
        liveVadRatio: document.getElementById('liveVadRatio'),
        liveChunkCount: document.getElementById('liveChunkCount'),
        liveHysteresisState: document.getElementById('liveHysteresisState'),

        // Audio Analysis Tab
        dropZone: document.getElementById('drop-zone'),
        audioFileInput: document.getElementById('audioFileInput'),
        btnBrowseFile: document.getElementById('btnBrowseFile'),
        samplePillBtns: document.querySelectorAll('.sample-pill-btn'),
        fileReadyBar: document.getElementById('fileReadyBar'),
        selectedFileTitle: document.getElementById('selectedFileTitle'),
        selectedFileSize: document.getElementById('selectedFileSize'),
        fileAudioPlayer: document.getElementById('fileAudioPlayer'),
        btnExecuteAnalysis: document.getElementById('btnExecuteAnalysis'),
        emptyState: document.getElementById('empty-state'),
        resultsState: document.getElementById('results-state'),
        analysisViz: document.getElementById('analysis-viz'),
        analysisSpectralCanvas: document.getElementById('analysisSpectralCanvas'),
        spectralDurationLabel: document.getElementById('spectralDurationLabel'),
        statusBar: document.getElementById('status-bar'),
        gaugeFill: document.getElementById('gauge-fill'),
        scoreText: document.getElementById('score-text'),
        scoreSublabel: document.getElementById('score-sublabel'),
        threatState: document.getElementById('threat-state'),
        metaGenuineProb: document.getElementById('metaGenuineProb'),
        metaSpoofProb: document.getElementById('metaSpoofProb'),
        metaDuration: document.getElementById('metaDuration'),
        metaSamples: document.getElementById('metaSamples'),
        recommendationText: document.getElementById('recommendationText'),
        primaryActionBtn: document.getElementById('primary-action-btn'),

        // Session Telemetry Tab
        telemetryFilterBtns: document.querySelectorAll('.telemetry-filter-btn'),
        telemetrySearchInput: document.getElementById('telemetrySearchInput'),
        btnTelemetryExportCsv: document.getElementById('btnTelemetryExportCsv'),
        telemetryTableBody: document.getElementById('telemetryTableBody'),
        telemetryCountLabel: document.getElementById('telemetryCountLabel'),
        bentoTotalInferences: document.getElementById('bentoTotalInferences'),
        bentoRiskTrend: document.getElementById('bentoRiskTrend'),
        bentoTrendMeta: document.getElementById('bentoTrendMeta'),
        bentoRiskIconWrapper: document.getElementById('bentoRiskIconWrapper'),
        bentoRiskIcon: document.getElementById('bentoRiskIcon'),

        // Analytics Tab
        analyticsAvgVal: document.getElementById('analyticsAvgVal'),
        analyticsAvgBar: document.getElementById('analyticsAvgBar'),
        anaSafeCount: document.getElementById('anaSafeCount'),
        anaSuspiciousCount: document.getElementById('anaSuspiciousCount'),
        anaHighRiskCount: document.getElementById('anaHighRiskCount'),
        anaTotalCount: document.getElementById('anaTotalCount'),

        // Settings Tab
        settingsModelLoaded: document.getElementById('settingsModelLoaded'),

        // ── Multi-Model AI Integration (AASIST, Gemini, RawNet2) ──────
        analysisStepsPanel: document.getElementById('analysis-steps-panel'),
        aiAnalysisPanel: document.getElementById('ai-analysis-panel'),
        geminiStatusBadge: document.getElementById('gemini-status-badge'),
        aiAasistScore: document.getElementById('aiAasistScore'),
        aiAasistBar: document.getElementById('aiAasistBar'),
        aiGeminiScore: document.getElementById('aiGeminiScore'),
        aiGeminiBar: document.getElementById('aiGeminiBar'),
        aiGeminiClassification: document.getElementById('aiGeminiClassification'),
        geminiScoreRow: document.getElementById('gemini-score-row'),
        geminiUnavailableRow: document.getElementById('gemini-unavailable-row'),
        aiRawnet2Score: document.getElementById('aiRawnet2Score'),
        aiRawnet2Bar: document.getElementById('aiRawnet2Bar'),
        aiRawnet2Classification: document.getElementById('aiRawnet2Classification'),
        rawnet2ScoreRow: document.getElementById('rawnet2-score-row'),
        rawnet2UnavailableRow: document.getElementById('rawnet2-unavailable-row'),
        aiFusionScore: document.getElementById('aiFusionScore'),
        aiFusionBar: document.getElementById('aiFusionBar'),
        aiFusionModels: document.getElementById('aiFusionModels'),
        evidencePanel: document.getElementById('evidence-panel'),
        evidenceList: document.getElementById('evidence-list'),
        segmentsPanel: document.getElementById('segments-panel'),
        segmentsTimeline: document.getElementById('segments-timeline'),
        segmentsDurationLabel: document.getElementById('segments-duration-label'),
        segmentsList: document.getElementById('segments-list'),
        metaModelCore: document.getElementById('metaModelCore'),
    };

    // =========================================================================
    // 4. TIMESTAMP UTILITIES
    // =========================================================================
    function getFormattedTime() {
        const now = new Date();
        return now.toTimeString().split(' ')[0];
    }

    function getFormattedDateTime() {
        const now = new Date();
        const yyyy = now.getFullYear();
        const mm = String(now.getMonth() + 1).padStart(2, '0');
        const dd = String(now.getDate()).padStart(2, '0');
        const time = now.toTimeString().split(' ')[0];
        const ms = String(now.getMilliseconds()).padStart(3, '0');
        return `${yyyy}-${mm}-${dd} ${time}.${ms}`;
    }

    // =========================================================================
    // 5. NAVIGATION CONTROLLER (FINAL STITCH MULTI-SCREEN ROUTER)
    // =========================================================================
    window.switchTab = function(tabId) {
        elements.navButtons.forEach(btn => {
            if (btn.dataset.tab === tabId) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        elements.tabContents.forEach(content => {
            if (content.id === `tab-${tabId}`) {
                content.classList.add('active');
            } else {
                content.classList.remove('active');
            }
        });

        // Trigger Canvas DPI recalculation after DOM display change
        setTimeout(() => {
            if (visualizer) visualizer.initCanvasDPI();
            if (liveConsoleVisualizer) liveConsoleVisualizer.initCanvasDPI();
            if (chart) chart.initCanvasDPI();
        }, 50);
    };

    elements.navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            window.switchTab(btn.dataset.tab);
        });
    });

    // =========================================================================
    // 6. TELEMETRY EVENT STREAM (LATEST ANALYSIS SIDEBAR)
    // =========================================================================
    function addTelemetryEvent(eventTitle, detail, type = "normal") {
        if (!elements.telemetryStreamList) return;

        // Hide startup prompt once real events start arriving
        if (elements.telemetryStartupPrompt) {
            elements.telemetryStartupPrompt.style.display = 'none';
        }

        const timeStr = getFormattedTime();
        const item = document.createElement('div');
        item.className = "py-2 flex items-start justify-between gap-2";

        let badgeStyle = "text-[#10b981]";
        if (type === "high_risk") badgeStyle = "text-[#ba1a1a] font-bold";
        else if (type === "suspicious") badgeStyle = "text-[#f59e0b] font-bold";
        else if (type === "action") badgeStyle = "text-secondary font-semibold";

        item.innerHTML = `
            <div>
                <span class="text-on-surface font-semibold block">${eventTitle}</span>
                <span class="text-[11px] text-on-surface-variant">${detail}</span>
            </div>
            <span class="text-[11px] ${badgeStyle} whitespace-nowrap">${timeStr}</span>
        `;

        elements.telemetryStreamList.insertBefore(item, elements.telemetryStreamList.firstChild);

        // Keep maximum 30 events in the sidebar feed
        while (elements.telemetryStreamList.children.length > 30) {
            elements.telemetryStreamList.removeChild(elements.telemetryStreamList.lastChild);
        }
    }

    // =========================================================================
    // 7. UNIFIED API URL RESOLVER & LIVE DETECTION MANAGER
    // =========================================================================
    function getApiUrl(path) {
        const normalizedPath = path.startsWith('/') ? path : '/' + path;
        const custom = localStorage.getItem('VOICEGUARD_BACKEND_URL') || '';
        if (custom.trim()) {
            const base = custom.trim().replace(/\/+$/, '');
            return base + normalizedPath;
        }
        // In all production (Vercel, Railway) and local development environments,
        // use clean relative paths so the browser always communicates with the host origin.
        // Vercel server-side rewrites automatically proxy /api/*, /status, /health to Railway backend.
        return normalizedPath;
    }

    // =========================================================================
    // AUTHORITATIVE LIVE STATE & VALIDATION
    // =========================================================================
    const liveState = {
        score: 1.0, // Genuine confidence (0.0 to 1.0)
        smoothedScore: 1.0,
        currentScore: 1.0,
        fusionScore: 0.0,
        state: "SAFE",
        speechRatio: 0.0,
        speechDetected: false,
        totalChunks: 0,
        processedChunks: 0,
        latencyMs: 0,
        models: { aasist: true, rawnet2: true, gemini: false },
        timestamp: Date.now()
    };

    function validateScore(score) {
        if (typeof score !== 'number' || isNaN(score) || !Number.isFinite(score)) {
            return null;
        }
        return Math.max(0.0, Math.min(1.0, score));
    }

    /**
     * UNIFIED AUTHORITATIVE METER RENDERER
     * Both Meter #1 (Hero Threat Gauge on Overview) and Meter #2 (Authenticity / Secondary Gauge)
     * and Session Analytics strictly derive from this same function.
     */
    function renderLiveScore(score, telemetry = {}) {
        const validScore = validateScore(score);
        if (validScore === null) {
            console.warn("[VG-LIVE] Invalid score received; skipping renderLiveScore update:", score);
            return;
        }

        const status = telemetry.status || (validScore < 0.30 ? "HIGH_RISK" : (validScore < 0.60 ? "SUSPICIOUS" : "SAFE"));
        const percentNum = validScore * 100;
        const percentStr = `${percentNum.toFixed(1)}%`;
        const speechRatio = typeof telemetry.speechRatio === 'number' ? telemetry.speechRatio : 0.0;
        const totalChunks = telemetry.totalChunks || liveState.totalChunks;
        const processedChunks = telemetry.processedChunks || liveState.processedChunks;
        const isHighRisk = status === "HIGH_RISK";
        const isSuspicious = status === "SUSPICIOUS";

        // Update shared live state
        liveState.score = validScore;
        liveState.state = status;
        liveState.timestamp = Date.now();

        // ---------------------------------------------------------------------
        // 1. METER #1: HERO THREAT GAUGE (Overview Tab)
        // ---------------------------------------------------------------------
        if (elements.heroScoreText && elements.heroGaugeCircle) {
            elements.heroScoreText.textContent = percentStr;
            elements.heroScoreLabel.textContent = "Genuine Confidence";

            const maxCircumference = 282.7; // 2 * pi * 45
            const offset = maxCircumference * (1.0 - validScore);
            elements.heroGaugeCircle.setAttribute('stroke-dashoffset', offset);

            if (isHighRisk) {
                elements.heroGaugeCircle.setAttribute('stroke', '#ba1a1a');
                if (elements.heroRiskText) elements.heroRiskText.textContent = "HIGH RISK ATTACK";
                if (elements.heroRiskBadge) elements.heroRiskBadge.className = "mt-4 px-4 py-1 bg-[#ffdad6] border border-[#ba1a1a] rounded-full flex items-center gap-2";
                if (elements.heroRiskDot) elements.heroRiskDot.className = "w-2 h-2 rounded-full bg-[#ba1a1a] pulse-dot";
                if (elements.heroSubtext) elements.heroSubtext.textContent = "Voice cloning signature detected. Probability of authentic speech is critically low.";
            } else if (isSuspicious) {
                elements.heroGaugeCircle.setAttribute('stroke', '#f59e0b');
                if (elements.heroRiskText) elements.heroRiskText.textContent = "SUSPICIOUS SPEECH";
                if (elements.heroRiskBadge) elements.heroRiskBadge.className = "mt-4 px-4 py-1 bg-[#fef3c7] border border-[#f59e0b] rounded-full flex items-center gap-2";
                if (elements.heroRiskDot) elements.heroRiskDot.className = "w-2 h-2 rounded-full bg-[#f59e0b]";
                if (elements.heroSubtext) elements.heroSubtext.textContent = "Anomalous frequency distribution. Secondary verification challenge advised.";
            } else {
                elements.heroGaugeCircle.setAttribute('stroke', '#10b981');
                if (elements.heroRiskText) elements.heroRiskText.textContent = "LOW RISK (SAFE)";
                if (elements.heroRiskBadge) elements.heroRiskBadge.className = "mt-4 px-4 py-1 bg-[#d1fae5] border border-[#10b981] rounded-full flex items-center gap-2";
                if (elements.heroRiskDot) elements.heroRiskDot.className = "w-2 h-2 rounded-full bg-[#10b981]";
                if (elements.heroSubtext) elements.heroSubtext.textContent = "Natural glottal and vocal tract characteristics verified.";
            }
            console.log(`[VG-LIVE] meter1 updated (${percentStr})`);
        }

        // ---------------------------------------------------------------------
        // 2. METER #2: SECONDARY / THREAT RESULT GAUGE (Analysis Tab & AI Panel)
        // ---------------------------------------------------------------------
        if (elements.scoreText) {
            elements.scoreText.textContent = percentStr;
            elements.scoreText.className = isHighRisk 
                ? "font-telemetry-mono text-2xl font-bold text-error" 
                : (isSuspicious ? "font-telemetry-mono text-2xl font-bold text-[#f59e0b]" : "font-telemetry-mono text-2xl font-bold text-[#10b981]");
        }
        if (elements.gaugeFill) {
            elements.gaugeFill.setAttribute('stroke-dasharray', `${percentNum.toFixed(1)}, 100`);
            elements.gaugeFill.className = isHighRisk 
                ? "text-error stroke-current" 
                : (isSuspicious ? "text-[#f59e0b] stroke-current" : "text-[#10b981] stroke-current");
        }
        if (elements.threatState) {
            elements.threatState.textContent = status;
            if (isHighRisk) {
                elements.threatState.className = "inline-block border border-error text-error bg-error-container px-3 py-1 font-label-caps text-label-caps rounded-sm uppercase";
            } else if (isSuspicious) {
                elements.threatState.className = "inline-block border border-tertiary-container text-tertiary-container bg-tertiary-fixed px-3 py-1 font-label-caps text-label-caps rounded-sm uppercase";
            } else {
                elements.threatState.className = "inline-block border border-secondary text-secondary bg-secondary-fixed px-3 py-1 font-label-caps text-label-caps rounded-sm uppercase";
            }
        }
        if (elements.metaGenuineProb) elements.metaGenuineProb.textContent = percentStr;
        if (elements.metaSpoofProb) elements.metaSpoofProb.textContent = `${((1 - validScore) * 100).toFixed(1)}%`;
        if (elements.aiFusionScore) {
            elements.aiFusionScore.textContent = percentStr;
            elements.aiFusionScore.className = isHighRisk ? "font-telemetry-mono text-xs font-bold text-error" : (isSuspicious ? "font-telemetry-mono text-xs font-bold text-[#f59e0b]" : "font-telemetry-mono text-xs font-bold text-secondary");
        }
        if (elements.aiFusionBar) {
            elements.aiFusionBar.style.width = `${percentNum.toFixed(1)}%`;
            elements.aiFusionBar.className = isHighRisk ? "h-full transition-all duration-700 bg-error" : (isSuspicious ? "h-full transition-all duration-700 bg-[#f59e0b]" : "h-full transition-all duration-700 bg-secondary");
        }
        console.log(`[VG-LIVE] meter2 updated (${percentStr})`);

        // ---------------------------------------------------------------------
        // 3. STATS & BENTO TELEMETRY
        // ---------------------------------------------------------------------
        if (elements.liveHysteresisState) {
            elements.liveHysteresisState.textContent = status;
            elements.liveHysteresisState.className = isHighRisk ? "font-display-lg text-headline-md text-[#ba1a1a]" : (isSuspicious ? "font-display-lg text-headline-md text-[#f59e0b]" : "font-display-lg text-headline-md text-[#10b981]");
        }
        if (elements.liveVadRatio) elements.liveVadRatio.textContent = speechRatio.toFixed(2);
        if (elements.liveChunkCount) elements.liveChunkCount.textContent = `${processedChunks} / ${totalChunks}`;
        if (elements.liveLatencyPill && telemetry.latencyMs) {
            elements.liveLatencyPill.textContent = `LATENCY: ${telemetry.latencyMs} ms`;
        }

        // ---------------------------------------------------------------------
        // 4. CHART & VISUALIZERS
        // ---------------------------------------------------------------------
        if (chart && telemetry.currentScore !== undefined && validScore >= 0) {
            chart.addPoint(telemetry.currentScore, validScore);
        }
        if (visualizer) visualizer.setActivity(speechRatio, status);
        if (liveConsoleVisualizer) liveConsoleVisualizer.setActivity(speechRatio, status);
        updatePipelineWorkflowNodes(true, speechRatio, processedChunks, status);

        // ---------------------------------------------------------------------
        // 5. SESSION ANALYTICS REFRESH
        // ---------------------------------------------------------------------
        updateAnalyticsScreen();
    }

    class LiveDetectionManager {
        constructor() {
            this.state = 'STOPPED'; // STOPPED, REQUESTING_MIC, MIC_CONNECTED, LISTENING, ANALYZING, SAFE, SUSPICIOUS, HIGH_RISK, ERROR
            this.mediaStream = null;
            this.audioContext = null;
            this.analyser = null;
            this.sourceNode = null;
            this.scriptNode = null;
            this.gainNode = null;

            this.targetSampleRate = 16000;
            this.chunkSamples = 32000; // 2.0s of 16kHz audio buffer
            this.rollingBuffer = new Float32Array(this.chunkSamples);
            this.bufferIndex = 0;
            this.totalSamplesRecorded = 0;

            // Diagnostic Counters for Developer Live HUD
            this.audioProcessEvents = 0;
            this.nonzeroFrames = 0;
            this.currentRms = 0.0;
            this.lastChunkByteSize = 0;
            this.lastChunkSamples = 0;
            this.lastChunkRms = 0.0;
            this.requestsStarted = 0;
            this.requestsCompleted = 0;
            this.requestsFailed = 0;
            this.lastHttpStatus = null;
            this.lastLatencyMs = 0;
            this.lastFusionScore = null;
            this.lastSmoothedScore = null;

            this.inFlight = false;
            this.streamTimer = null;
            this.processedChunks = 0;
            this.totalChunks = 0;
            this.requestSeq = 0;
            this.latestProcessedSeq = 0;

            // Retain on window for GC protection
            window._vgLiveManager = this;

            this.initEvents();
            this.checkBackendHealth();
        }

        ensureAudioContext() {
            if (!this.audioContext || this.audioContext.state === 'closed') {
                const AudioContextClass = window.AudioContext || window.webkitAudioContext;
                this.audioContext = new AudioContextClass();
            }
            if (this.audioContext.state === 'suspended') {
                this.audioContext.resume();
            }
            window._vgAudioContext = this.audioContext;
            return this.audioContext;
        }

        getBackendUrl(path) {
            return getApiUrl(path);
        }

        async checkBackendHealth() {
            try {
                const res = await fetch(getApiUrl(`/health?_ts=${Date.now()}`), {
                    method: 'GET',
                    cache: 'no-store'
                });
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const health = await res.json();
                
                if (elements.liveBackendStatusPill) {
                    elements.liveBackendStatusPill.className = "px-3 py-1 bg-[#d1fae5] text-[#065f46] border border-[#10b981] rounded font-telemetry-mono text-[11px] flex items-center gap-1.5";
                    elements.liveBackendStatusPill.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>BACKEND: CONNECTED`;
                }

                if (elements.liveModelsDetail && health.models) {
                    const active = [];
                    if (health.models.aasist) active.push("AASIST");
                    if (health.models.rawnet2) active.push("RawNet2");
                    if (health.models.gemini) active.push("Gemini");
                    elements.liveModelsDetail.textContent = active.length > 0 ? active.join(" + ") : "AASIST Ready";
                }
                if (elements.topBackendText) elements.topBackendText.textContent = "BACKEND: ONLINE";
                if (elements.topBackendDot) elements.topBackendDot.className = "w-2 h-2 rounded-full bg-[#10b981]";
                return true;
            } catch (err) {
                if (elements.liveBackendStatusPill) {
                    elements.liveBackendStatusPill.className = "px-3 py-1 bg-surface-container-low border border-outline-variant text-on-surface-variant rounded font-telemetry-mono text-[11px] flex items-center gap-1.5";
                    elements.liveBackendStatusPill.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-[#f59e0b]"></span>BACKEND: STANDBY`;
                }
                if (elements.topBackendText) elements.topBackendText.textContent = "BACKEND: OFFLINE";
                if (elements.topBackendDot) elements.topBackendDot.className = "w-2 h-2 rounded-full bg-[#ba1a1a]";
                return false;
            }
        }

        setState(newState, detail = '') {
            this.state = newState;
            const isLive = ['MIC_CONNECTED', 'LISTENING', 'ANALYZING', 'SAFE', 'SUSPICIOUS', 'HIGH_RISK'].includes(newState);

            // Update Header Mic Status
            if (elements.topMicText) {
                if (isLive) {
                    elements.topMicText.textContent = "MIC: CAPTURING";
                    if (elements.topMicDot) elements.topMicDot.className = "w-2 h-2 rounded-full bg-[#10b981] animate-pulse";
                } else if (newState === 'REQUESTING_MIC') {
                    elements.topMicText.textContent = "MIC: PROMPTING";
                    if (elements.topMicDot) elements.topMicDot.className = "w-2 h-2 rounded-full bg-[#f59e0b] animate-bounce";
                } else if (newState === 'ERROR') {
                    elements.topMicText.textContent = "MIC: ERROR";
                    if (elements.topMicDot) elements.topMicDot.className = "w-2 h-2 rounded-full bg-[#ba1a1a]";
                } else {
                    elements.topMicText.textContent = "MIC: STANDBY";
                    if (elements.topMicDot) elements.topMicDot.className = "w-2 h-2 rounded-full bg-[#76777d]";
                }
            }

            // Update System Status Text
            if (elements.sysText) {
                if (newState === 'REQUESTING_MIC') elements.sysText.textContent = "REQUESTING MICROPHONE...";
                else if (newState === 'LISTENING' || newState === 'ANALYZING') elements.sysText.textContent = "AI PIPELINE: ANALYZING";
                else if (newState === 'HIGH_RISK') elements.sysText.textContent = "AI: HIGH RISK DETECTED";
                else if (newState === 'SUSPICIOUS') elements.sysText.textContent = "AI: SUSPICIOUS DETECTED";
                else if (newState === 'SAFE') elements.sysText.textContent = "AI: GENUINE VERIFIED";
                else if (newState === 'ERROR') elements.sysText.textContent = "MIC / BACKEND ERROR";
                else elements.sysText.textContent = "VOICEGUARD AI READY";
            }

            if (elements.sysDot) {
                if (newState === 'HIGH_RISK') elements.sysDot.className = "w-2 h-2 rounded-full bg-[#ba1a1a] animate-ping";
                else if (newState === 'SUSPICIOUS') elements.sysDot.className = "w-2 h-2 rounded-full bg-[#f59e0b] animate-bounce";
                else if (isLive) elements.sysDot.className = "w-2 h-2 rounded-full bg-[#10b981] animate-pulse";
                else elements.sysDot.className = "w-2 h-2 rounded-full bg-[#76777d]";
            }

            // Update Overview Button & Badges
            if (elements.btnLiveToggleOverviewText) {
                elements.btnLiveToggleOverviewText.textContent = isLive ? "STOP LIVE STREAM" : "START LIVE STREAM";
            }
            if (elements.btnLiveToggleOverview) {
                if (isLive) {
                    elements.btnLiveToggleOverview.className = "px-3 py-1 bg-error text-on-error rounded font-label-caps text-xs flex items-center gap-1.5 hover:bg-error-container hover:text-on-error-container transition-all";
                } else {
                    elements.btnLiveToggleOverview.className = "px-3 py-1 bg-secondary text-on-secondary rounded font-label-caps text-xs flex items-center gap-1.5 hover:bg-secondary-container transition-all";
                }
            }
            if (elements.liveStatusBadgeOverview) {
                elements.liveStatusBadgeOverview.textContent = isLive ? "LIVE STREAMING" : "STANDBY";
                elements.liveStatusBadgeOverview.className = isLive 
                    ? "px-2 py-0.5 rounded font-telemetry-mono text-[10px] bg-[#d1fae5] border border-[#10b981] text-[#065f46]"
                    : "px-2 py-0.5 rounded font-telemetry-mono text-[10px] bg-surface border border-outline-variant text-on-surface-variant";
            }

            // Update Live Console Tab Button
            if (elements.btnLiveToggleConsoleText) {
                elements.btnLiveToggleConsoleText.textContent = isLive ? "STOP DETECTION" : "START CONTINUOUS DETECTION";
            }
            if (elements.btnLiveToggleConsole) {
                if (isLive) {
                    elements.btnLiveToggleConsole.className = "px-4 py-2 bg-error text-on-error rounded font-label-caps text-xs flex items-center gap-2 hover:bg-error-container hover:text-on-error-container transition-all";
                } else {
                    elements.btnLiveToggleConsole.className = "px-4 py-2 bg-secondary text-on-secondary rounded font-label-caps text-xs flex items-center gap-2 hover:bg-secondary-container transition-all";
                }
            }
            if (elements.liveConsoleStreamStatus) {
                elements.liveConsoleStreamStatus.textContent = isLive ? "STREAM: ACTIVE (16kHz PCM)" : "STREAM: STANDBY";
            }

            // Header mic icon button animation
            if (elements.headerMicBtn) {
                if (isLive) {
                    elements.headerMicBtn.classList.add('text-error', 'animate-pulse');
                    elements.headerMicBtn.classList.remove('text-primary');
                } else {
                    elements.headerMicBtn.classList.remove('text-error', 'animate-pulse');
                    elements.headerMicBtn.classList.add('text-primary');
                }
            }

            // Error display
            if (newState === 'ERROR') {
                if (elements.liveErrorBanner && elements.liveErrorText) {
                    elements.liveErrorText.textContent = detail || "Microphone initialization or connection failed.";
                    elements.liveErrorBanner.classList.remove('hidden');
                }
            } else if (elements.liveErrorBanner) {
                elements.liveErrorBanner.classList.add('hidden');
            }
        }

        initEvents() {
            const toggleHandler = () => {
                // Ensure AudioContext is synchronously created and resumed inside the user gesture
                this.ensureAudioContext();

                if (['MIC_CONNECTED', 'LISTENING', 'ANALYZING', 'SAFE', 'SUSPICIOUS', 'HIGH_RISK'].includes(this.state)) {
                    this.stop();
                } else {
                    this.start();
                }
            };

            if (elements.headerMicBtn) elements.headerMicBtn.addEventListener('click', toggleHandler);
            if (elements.btnLiveToggleOverview) elements.btnLiveToggleOverview.addEventListener('click', toggleHandler);
            if (elements.btnLiveToggleConsole) elements.btnLiveToggleConsole.addEventListener('click', toggleHandler);

            // Minimize / expand Live Debug HUD
            const btnToggleDbgHUD = document.getElementById('btnToggleDbgHUD');
            const dbgHUDContent = document.getElementById('dbgHUDContent');
            if (btnToggleDbgHUD && dbgHUDContent) {
                btnToggleDbgHUD.addEventListener('click', () => {
                    const isHidden = dbgHUDContent.classList.toggle('hidden');
                    btnToggleDbgHUD.textContent = isHidden ? "EXPAND" : "MINIMIZE";
                });
            }
        }

        async start() {
            try {
                this.setState('REQUESTING_MIC');

                if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                    throw new Error("Your browser does not support microphone capture (navigator.mediaDevices is unavailable).");
                }

                // 1. Synchronously ensure AudioContext is instantiated & running
                this.ensureAudioContext();

                // 2. Request Microphone Access
                this.mediaStream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        channelCount: 1,
                        echoCancellation: true,
                        noiseSuppression: false,
                        autoGainControl: true
                    },
                    video: false
                });

                // 3. Resume AudioContext again if browser suspended it during getUserMedia prompt
                if (this.audioContext.state === 'suspended') {
                    await this.audioContext.resume();
                }

                const nativeSampleRate = this.audioContext.sampleRate;

                // 4. Create AnalyserNode for Real-Time Waveform & FFT
                this.analyser = this.audioContext.createAnalyser();
                this.analyser.fftSize = 256;
                this.analyser.smoothingTimeConstant = 0.75;

                // 5. Connect Source Node directly to Analyser
                this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);
                this.sourceNode.connect(this.analyser);

                // Attach real analyser to visualizers
                if (visualizer) visualizer.attachAnalyser(this.analyser);
                if (liveConsoleVisualizer) liveConsoleVisualizer.attachAnalyser(this.analyser);

                // 6. Silent GainNode to keep audio graph alive without speaker loopback feedback
                this.gainNode = this.audioContext.createGain();
                this.gainNode.gain.value = 0.0;

                // 7. Script Processor for 16 kHz Chunk Ingestion & Resampling
                this.rollingBuffer = new Float32Array(this.chunkSamples);
                this.bufferIndex = 0;
                this.totalSamplesRecorded = 0;
                this.audioProcessEvents = 0;
                this.nonzeroFrames = 0;

                this.scriptNode = this.audioContext.createScriptProcessor(4096, 1, 1);
                const resampleRatio = nativeSampleRate / this.targetSampleRate;

                this.scriptNode.onaudioprocess = (e) => {
                    this.audioProcessEvents++;
                    const inputChannel = e.inputBuffer.getChannelData(0);

                    // Track RMS energy of the raw mic frame
                    let sumSq = 0.0;
                    for (let k = 0; k < inputChannel.length; k++) {
                        const val = inputChannel[k];
                        sumSq += val * val;
                    }
                    const frameRms = Math.sqrt(sumSq / inputChannel.length);
                    this.currentRms = frameRms;
                    if (frameRms > 0.0005) {
                        this.nonzeroFrames++;
                    }

                    // Linear interpolation downsampling to 16kHz
                    const outputLength = Math.floor(inputChannel.length / resampleRatio);
                    for (let i = 0; i < outputLength; i++) {
                        const originalIndex = i * resampleRatio;
                        const indexFloor = Math.floor(originalIndex);
                        const indexCeil = Math.min(inputChannel.length - 1, indexFloor + 1);
                        const fraction = originalIndex - indexFloor;
                        
                        const sample = inputChannel[indexFloor] * (1 - fraction) + inputChannel[indexCeil] * fraction;

                        this.rollingBuffer[this.bufferIndex] = sample;
                        this.bufferIndex = (this.bufferIndex + 1) % this.chunkSamples;
                        this.totalSamplesRecorded++;
                    }

                    // Zero out output buffer to avoid any clicks/pop
                    const outputChannel = e.outputBuffer.getChannelData(0);
                    outputChannel.fill(0);
                };

                this.sourceNode.connect(this.scriptNode);
                this.scriptNode.connect(this.gainNode);
                this.gainNode.connect(this.audioContext.destination);

                // Strong window anchors against V8 GC
                window._vgAudioContext = this.audioContext;
                window._vgSourceNode = this.sourceNode;
                window._vgScriptNode = this.scriptNode;
                window._vgGainNode = this.gainNode;
                window._vgAnalyser = this.analyser;

                this.setState('LISTENING');
                addTelemetryEvent("Live Microphone Connected", `Sample Rate: ${nativeSampleRate}Hz → 16,000Hz PCM`, "action");

                // 8. Send chunks every 1.5 seconds (clear any previous timer first)
                if (this.streamTimer) {
                    clearInterval(this.streamTimer);
                    this.streamTimer = null;
                }
                this.streamTimer = setInterval(() => this.sendLiveChunk(), 1500);

            } catch (err) {
                console.error("[LiveDetectionManager] Mic error:", err);
                let message = err.message || "Microphone access failed.";
                if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
                    message = "Microphone permission was denied. Please allow microphone access in your browser settings.";
                } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
                    message = "No microphone hardware detected on your device.";
                }
                this.stop();
                this.setState('ERROR', message);
            }
        }

        async sendLiveChunk() {
            if (this.inFlight) return;
            if (this.totalSamplesRecorded < 16000) return; // Wait for ~1s initial audio

            this.inFlight = true;
            this.totalChunks++;
            const currentSeq = ++this.requestSeq;
            this.requestsStarted++;

            const orderedSamples = new Float32Array(this.chunkSamples);
            const startIdx = this.bufferIndex;
            let sumSq = 0.0;
            for (let i = 0; i < this.chunkSamples; i++) {
                const s = this.rollingBuffer[(startIdx + i) % this.chunkSamples];
                orderedSamples[i] = s;
                sumSq += s * s;
            }

            const chunkRms = Math.sqrt(sumSq / this.chunkSamples);
            const wavBlob = this.encodeWAV(orderedSamples, this.targetSampleRate);

            this.lastChunkByteSize = wavBlob.size;
            this.lastChunkSamples = this.chunkSamples;
            this.lastChunkRms = chunkRms;

            console.log(`[VG-LIVE] chunk #${currentSeq} generated size=${wavBlob.size} bytes rms=${chunkRms.toFixed(4)} samples=${this.chunkSamples}`);
            console.log(`[VG-LIVE] request #${currentSeq} started`);

            const formData = new FormData();
            formData.append('file', wavBlob, 'live_chunk.wav');

            const sendTimestamp = performance.now();
            const controller = new AbortController();
            const abortTimeout = setTimeout(() => controller.abort(), 12000);

            try {
                const res = await fetch(this.getBackendUrl(`/api/live_chunk?_ts=${Date.now()}`), {
                    method: 'POST',
                    body: formData,
                    signal: controller.signal,
                    cache: 'no-store'
                });

                clearTimeout(abortTimeout);
                const latencyMs = Math.round(performance.now() - sendTimestamp);
                this.lastHttpStatus = res.status;
                this.lastLatencyMs = latencyMs;
                this.requestsCompleted++;

                console.log(`[VG-LIVE] request #${currentSeq} response ${res.status}`);

                if (!res.ok) {
                    throw new Error(`Server returned HTTP ${res.status}`);
                }

                const data = await res.json();
                console.log(`[VG-LIVE] fusionScore=${data.fusionScore} smoothedScore=${data.smoothedScore} state=${data.state}`);

                // Drop out-of-order delayed responses
                if (currentSeq < this.latestProcessedSeq) {
                    console.log(`[VG-LIVE] Dropping stale chunk response #${currentSeq} (latest is #${this.latestProcessedSeq})`);
                    return;
                }
                this.latestProcessedSeq = currentSeq;
                console.log(`[VG-LIVE] accepted response #${currentSeq}`);

                this.handleLiveTelemetry(data, latencyMs);

            } catch (err) {
                clearTimeout(abortTimeout);
                this.requestsFailed++;
                this.lastHttpStatus = 'ERR';
                console.warn(`[VG-LIVE] Chunk #${currentSeq} inference error:`, err);
                if (elements.liveLatencyPill) elements.liveLatencyPill.textContent = `LATENCY: ERR`;
            } finally {
                this.inFlight = false;
            }
        }

        handleLiveTelemetry(data, clientLatencyMs) {
            const isSpeech = Boolean(data.speechDetected);
            const speechRatio = typeof data.speechRatio === 'number' ? data.speechRatio : 0.0;
            const status = data.state || (data.fusion && data.fusion.classification ? data.fusion.classification : "SAFE");
            
            // Single authoritative score:
            let authoritativeScore = validateScore(data.smoothedScore);
            if (authoritativeScore === null) {
                authoritativeScore = validateScore(data.currentScore);
            }
            if (authoritativeScore === null && data.fusion) {
                authoritativeScore = validateScore(data.fusion.finalScore);
            }
            if (authoritativeScore === null) {
                authoritativeScore = liveState.score; // Preserve previous valid score
            }

            const currentScore = (typeof data.currentScore === 'number' && !isNaN(data.currentScore))
                ? data.currentScore
                : authoritativeScore;
            const processingTimeMs = data.processingTimeMs || clientLatencyMs;

            this.lastFusionScore = typeof data.fusionScore === 'number' ? data.fusionScore : (1.0 - authoritativeScore);
            this.lastSmoothedScore = authoritativeScore;

            if (isSpeech) {
                this.processedChunks++;
                this.setState(status);
            }

            liveState.smoothedScore = authoritativeScore;
            liveState.currentScore = currentScore;
            liveState.fusionScore = this.lastFusionScore;
            liveState.state = status;
            liveState.speechRatio = speechRatio;
            liveState.speechDetected = isSpeech;
            liveState.totalChunks = this.totalChunks;
            liveState.processedChunks = this.processedChunks;
            liveState.latencyMs = processingTimeMs;
            liveState.timestamp = Date.now();
            console.log(`[VG-LIVE] liveState updated: score=${(authoritativeScore * 100).toFixed(1)}% status=${status}`);

            // UNIFIED RENDER CALL
            renderLiveScore(authoritativeScore, {
                currentScore: currentScore,
                status: status,
                speechRatio: speechRatio,
                totalChunks: this.totalChunks,
                processedChunks: this.processedChunks,
                latencyMs: processingTimeMs,
                isSpeech: isSpeech,
                models: data.models
            });

            if (isSpeech) {
                const eventType = status === "HIGH_RISK" ? "high_risk" : (status === "SUSPICIOUS" ? "suspicious" : "safe");
                const modelInfo = data.models ? `AASIST: ${data.models.aasist ? 'ON' : 'OFF'} | RawNet2: ${data.models.rawnet2 ? 'ON' : 'OFF'} | Gemini: ${data.models.gemini ? 'ON' : 'OFF'}` : 'Live Stream';
                
                addTelemetryEvent(
                    `Live Speech Inference #${this.processedChunks}`,
                    `Genuine: ${(authoritativeScore * 100).toFixed(1)}% | Spoof: ${((1 - authoritativeScore) * 100).toFixed(1)}% | ${modelInfo}`,
                    eventType
                );

                recordSessionEvent({
                    timestamp: getFormattedDateTime(),
                    eventType: status === "SAFE" ? "Live Human Speech Verified" : (status === "SUSPICIOUS" ? "Anomalous Acoustic Deviation" : "Synthetic Voice Clone Attack"),
                    source: "Live Microphone (Channel 1)",
                    confidencePercent: `${(authoritativeScore * 100).toFixed(1)}%`,
                    confidenceRaw: authoritativeScore,
                    status: status === "SAFE" ? "CLEARED" : (status === "SUSPICIOUS" ? "FLAGGED" : "BLOCKED"),
                    riskLevel: status
                });
            }
        }

        encodeWAV(samples, sampleRate) {
            const buffer = new ArrayBuffer(44 + samples.length * 2);
            const view = new DataView(buffer);

            this.writeString(view, 0, 'RIFF');
            view.setUint32(4, 36 + samples.length * 2, true);
            this.writeString(view, 8, 'WAVE');
            this.writeString(view, 12, 'fmt ');
            view.setUint32(16, 16, true);
            view.setUint16(20, 1, true); // PCM
            view.setUint16(22, 1, true); // Mono
            view.setUint32(24, sampleRate, true);
            view.setUint32(28, sampleRate * 2, true);
            view.setUint16(32, 2, true);
            view.setUint16(34, 16, true);
            this.writeString(view, 36, 'data');
            view.setUint32(40, samples.length * 2, true);

            let offset = 44;
            for (let i = 0; i < samples.length; i++, offset += 2) {
                const s = Math.max(-1, Math.min(1, samples[i]));
                view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
            }

            return new Blob([view], { type: 'audio/wav' });
        }

        writeString(view, offset, string) {
            for (let i = 0; i < string.length; i++) {
                view.setUint8(offset + i, string.charCodeAt(i));
            }
        }

        stop() {
            if (this.streamTimer) {
                clearInterval(this.streamTimer);
                this.streamTimer = null;
            }

            if (this.mediaStream) {
                this.mediaStream.getTracks().forEach(track => {
                    try { track.stop(); } catch (e) {}
                });
                this.mediaStream = null;
            }

            if (this.scriptNode) {
                try {
                    this.scriptNode.disconnect();
                    this.scriptNode.onaudioprocess = null;
                } catch (e) {}
                this.scriptNode = null;
            }

            if (this.gainNode) {
                try { this.gainNode.disconnect(); } catch (e) {}
                this.gainNode = null;
            }

            if (this.sourceNode) {
                try { this.sourceNode.disconnect(); } catch (e) {}
                this.sourceNode = null;
            }

            if (this.audioContext && this.audioContext.state !== 'closed') {
                try { this.audioContext.close(); } catch (e) {}
                this.audioContext = null;
            }

            if (visualizer) visualizer.detachAnalyser();
            if (liveConsoleVisualizer) liveConsoleVisualizer.detachAnalyser();

            this.inFlight = false;
            this.bufferIndex = 0;
            this.totalSamplesRecorded = 0;
            this.rollingBuffer = new Float32Array(this.chunkSamples);
            this.setState('STOPPED');
            addTelemetryEvent("Live Stream Stopped", "Microphone tracks released cleanly.", "normal");
        }
    }

    const liveManager = new LiveDetectionManager();

    // =========================================================================
    // DEVELOPER LIVE DIAGNOSTIC HUD UPDATER
    // =========================================================================
    function updateLiveDebugOverlay() {
        const micState = document.getElementById('dbgMicState');
        if (!micState) return;

        micState.textContent = liveManager.state;
        micState.className = ['MIC_CONNECTED', 'LISTENING', 'ANALYZING', 'SAFE', 'SUSPICIOUS', 'HIGH_RISK'].includes(liveManager.state)
            ? "font-bold text-[#10b981]" : (liveManager.state === 'ERROR' ? "font-bold text-[#ba1a1a]" : "font-bold text-white");

        const audioCtx = liveManager.audioContext;
        const audioCtxState = document.getElementById('dbgAudioCtxState');
        if (audioCtxState) {
            audioCtxState.textContent = audioCtx ? audioCtx.state.toUpperCase() : "N/A";
            audioCtxState.className = audioCtx && audioCtx.state === 'running' ? "font-bold text-[#10b981]" : "font-bold text-[#f59e0b]";
        }

        const sampleRates = document.getElementById('dbgSampleRates');
        if (sampleRates) {
            sampleRates.textContent = audioCtx ? `${audioCtx.sampleRate}Hz → ${liveManager.targetSampleRate}Hz` : "N/A → 16kHz";
        }

        const processEvents = document.getElementById('dbgProcessEvents');
        if (processEvents) processEvents.textContent = `${liveManager.audioProcessEvents}`;

        const nonzeroFrames = document.getElementById('dbgNonzeroFrames');
        if (nonzeroFrames) nonzeroFrames.textContent = `${liveManager.nonzeroFrames} (RMS: ${(liveManager.currentRms || 0).toFixed(4)})`;

        const bufferSamples = document.getElementById('dbgBufferSamples');
        if (bufferSamples) bufferSamples.textContent = `${Math.min(liveManager.chunkSamples, liveManager.totalSamplesRecorded)} / ${liveManager.chunkSamples}`;

        const chunksGen = document.getElementById('dbgChunksGen');
        if (chunksGen) chunksGen.textContent = `${liveManager.totalChunks} (Processed: ${liveManager.processedChunks})`;

        const lastChunkSize = document.getElementById('dbgLastChunkSize');
        if (lastChunkSize) lastChunkSize.textContent = `${liveManager.lastChunkByteSize || 0} B (RMS: ${(liveManager.lastChunkRms || 0).toFixed(4)})`;

        const requestsStat = document.getElementById('dbgRequestsStat');
        if (requestsStat) requestsStat.textContent = `${liveManager.requestSeq} start / ${liveManager.requestsCompleted || 0} done / ${liveManager.requestsFailed || 0} err`;

        const lastHttp = document.getElementById('dbgLastHttp');
        if (lastHttp) lastHttp.textContent = `${liveManager.lastHttpStatus || 'N/A'} (${liveManager.lastLatencyMs || 0}ms)`;

        const lastScores = document.getElementById('dbgLastScores');
        if (lastScores) lastScores.textContent = `Spoof: ${liveManager.lastFusionScore !== null ? (liveManager.lastFusionScore * 100).toFixed(1) + '%' : 'N/A'} | Smooth: ${liveManager.lastSmoothedScore !== null ? (liveManager.lastSmoothedScore * 100).toFixed(1) + '%' : 'N/A'}`;

        const acceptedSeq = document.getElementById('dbgAcceptedSeq');
        if (acceptedSeq) acceptedSeq.textContent = `#${liveManager.latestProcessedSeq}`;

        const metersVal = document.getElementById('dbgMetersVal');
        if (metersVal) {
            const m1 = elements.heroScoreText ? elements.heroScoreText.textContent : 'N/A';
            const m2 = elements.scoreText ? elements.scoreText.textContent : 'N/A';
            metersVal.textContent = `${m1} / ${m2}`;
        }
    }

    setInterval(updateLiveDebugOverlay, 250);

    // =========================================================================
    // 8. REAL-TIME TELEMETRY POLLING (/status)
    // =========================================================================
    async function fetchStatus() {
        if (liveManager && ['REQUESTING_MIC', 'MIC_CONNECTED', 'LISTENING', 'ANALYZING', 'SAFE', 'SUSPICIOUS', 'HIGH_RISK'].includes(liveManager.state)) {
            return; // Live detection active -> Real audio chunks take precedence
        }
        try {
            const response = await fetch(getApiUrl(`/status?_ts=${Date.now()}`), {
                method: 'GET',
                cache: 'no-store'
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            updateDashboardWithRealData(data);
        } catch (err) {
            if (elements.sysText && (!liveManager || liveManager.state === 'STOPPED')) {
                elements.sysText.textContent = "STANDBY";
            }
            if (elements.sysDot && (!liveManager || liveManager.state === 'STOPPED')) {
                elements.sysDot.className = "w-2 h-2 rounded-full bg-[#76777d]";
            }
        }
    }

    function updateDashboardWithRealData(data) {
        if (liveManager && ['REQUESTING_MIC', 'MIC_CONNECTED', 'LISTENING', 'ANALYZING', 'SAFE', 'SUSPICIOUS', 'HIGH_RISK'].includes(liveManager.state)) {
            return; // Never overwrite live inference metrics while active
        }

        const score = typeof data.smoothed_score === 'number' ? data.smoothed_score : -1;
        const currentScore = typeof data.current_score === 'number' ? data.current_score : score;
        const speechRatio = typeof data.speech_ratio === 'number' ? data.speech_ratio : 0.0;
        const status = data.status || "SAFE";
        const isRecording = Boolean(data.is_recording);
        const totalChunks = data.total_chunks || 0;
        const processedChunks = data.processed_chunks || 0;

        currentStatus = status;

        // Top Status Badge
        if (elements.sysText) elements.sysText.textContent = isRecording ? "SYSTEM ONLINE & MONITORING" : "VOICEGUARD AI READY";
        if (elements.sysDot) elements.sysDot.className = isRecording ? "w-2 h-2 rounded-full bg-[#10b981]" : "w-2 h-2 rounded-full bg-[#10b981]";

        // Render live score on dashboard
        if (score >= 0) {
            renderLiveScore(score, {
                currentScore: currentScore,
                status: status,
                speechRatio: speechRatio,
                totalChunks: totalChunks,
                processedChunks: processedChunks,
                isSpeech: true
            });
        }

        // Settings Model Loaded
        if (elements.settingsModelLoaded) {
            elements.settingsModelLoaded.textContent = data.model_loaded ? "LOADED & READY" : "CLOUD RESILIENT";
        }

        if (status !== lastStatus && lastStatus !== null) {
            addTelemetryEvent("Hysteresis State Transition", `${lastStatus} &rarr; ${status}`, status === "SAFE" ? "safe" : "high_risk");
        }
        lastStatus = status;
    }

    // =========================================================================
    // 9. PIPELINE WORKFLOW NODES
    // =========================================================================
    function updatePipelineWorkflowNodes(isRecording, speechRatio, processedChunks, status) {
        // Node 1: MIC INPUT
        if (elements.pipeDot1) {
            elements.pipeDot1.className = isRecording 
                ? "w-4 h-4 rounded-full border-2 border-secondary bg-background flex items-center justify-center" 
                : "w-4 h-4 rounded-full border-2 border-outline-variant bg-background flex items-center justify-center";
        }

        // Node 2: VAD
        if (elements.pipeDot2) {
            elements.pipeDot2.className = speechRatio >= 0.5 
                ? "w-4 h-4 rounded-full border-2 border-secondary bg-background flex items-center justify-center pulse-dot" 
                : "w-4 h-4 rounded-full border-2 border-secondary bg-background flex items-center justify-center";
        }

        // Node 3: AASIST
        if (elements.pipeDot3) {
            elements.pipeDot3.className = speechRatio >= 0.5 
                ? "w-4 h-4 rounded-full border-2 border-secondary bg-background flex items-center justify-center pulse-dot" 
                : "w-4 h-4 rounded-full border-2 border-outline-variant bg-background flex items-center justify-center";
        }

        // Node 4: RISK ENGINE
        if (elements.pipeDot4) {
            elements.pipeDot4.className = processedChunks > 0 
                ? "w-4 h-4 rounded-full border-2 border-secondary bg-background flex items-center justify-center" 
                : "w-4 h-4 rounded-full border-2 border-outline-variant bg-background flex items-center justify-center";
        }

        // Node 5: DECISION
        if (elements.pipeDot5) {
            if (status === "HIGH_RISK") {
                elements.pipeDot5.className = "w-4 h-4 rounded-full border-2 border-[#ba1a1a] bg-[#ba1a1a] flex items-center justify-center";
            } else if (status === "SUSPICIOUS") {
                elements.pipeDot5.className = "w-4 h-4 rounded-full border-2 border-[#f59e0b] bg-[#f59e0b] flex items-center justify-center";
            } else if (processedChunks > 0) {
                elements.pipeDot5.className = "w-4 h-4 rounded-full border-2 border-[#10b981] bg-[#10b981] flex items-center justify-center";
            } else {
                elements.pipeDot5.className = "w-4 h-4 rounded-full border-2 border-outline-variant bg-background flex items-center justify-center";
            }
        }
    }

    // =========================================================================
    // 10. AUDIO ANALYSIS SCREEN CONTROLLER (FINAL STITCH SPEC)
    // =========================================================================
    function handleSelectedFile(file) {
        if (!file) return;
        selectedAudioFile = file;

        if (elements.selectedFileTitle) elements.selectedFileTitle.textContent = file.name;
        if (elements.selectedFileSize) elements.selectedFileSize.textContent = `${(file.size / 1024).toFixed(1)} KB`;
        if (elements.fileReadyBar) elements.fileReadyBar.classList.remove('hidden');

        if (elements.fileAudioPlayer) {
            elements.fileAudioPlayer.src = URL.createObjectURL(file);
        }
    }

    // Dropzone & Browse Events
    if (elements.dropZone && elements.audioFileInput) {
        elements.dropZone.addEventListener('click', (e) => {
            if (e.target !== elements.btnBrowseFile) {
                elements.audioFileInput.click();
            }
        });

        if (elements.btnBrowseFile) {
            elements.btnBrowseFile.addEventListener('click', (e) => {
                e.stopPropagation();
                elements.audioFileInput.click();
            });
        }

        elements.audioFileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files[0]) {
                handleSelectedFile(e.target.files[0]);
            }
        });

        elements.dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            elements.dropZone.classList.add('border-secondary', 'bg-surface-container');
        });

        elements.dropZone.addEventListener('dragleave', () => {
            elements.dropZone.classList.remove('border-secondary', 'bg-surface-container');
        });

        elements.dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            elements.dropZone.classList.remove('border-secondary', 'bg-surface-container');
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                handleSelectedFile(e.dataTransfer.files[0]);
            }
        });
    }

    // Sample Test Pills
    elements.samplePillBtns.forEach(btn => {
        btn.addEventListener('click', async () => {
            const filename = btn.dataset.file;
            try {
                const response = await fetch(getApiUrl(`/api/sample_file/${filename}?_ts=${Date.now()}`), {
                    cache: 'no-store'
                });
                if (!response.ok) throw new Error("Could not fetch sample");
                const blob = await response.blob();
                const file = new File([blob], filename, { type: "audio/wav" });
                handleSelectedFile(file);
                addTelemetryEvent("Sample Injected", filename, "action");
            } catch (err) {
                console.error("Sample fetch error:", err);
            }
        });
    });

    // Execute File Analysis
    if (elements.btnExecuteAnalysis) {
        elements.btnExecuteAnalysis.addEventListener('click', async () => {
            if (!selectedAudioFile) return;

            elements.btnExecuteAnalysis.setAttribute('disabled', 'true');
            elements.btnExecuteAnalysis.textContent = "ANALYZING...";

            // Show step progress panel, hide results
            if (elements.analysisStepsPanel) elements.analysisStepsPanel.classList.remove('hidden');
            if (elements.emptyState) elements.emptyState.classList.add('hidden');
            if (elements.resultsState) {
                elements.resultsState.classList.add('hidden');
                elements.resultsState.classList.remove('flex');
            }

            setStep('upload', 'active');
            setStep('aasist', 'pending');
            setStep('gemini', 'pending');
            setStep('rawnet2', 'pending');
            setStep('fusion', 'pending');
            setStep('complete', 'pending');

            const formData = new FormData();
            formData.append('file', selectedAudioFile);

            // Concurrent pipeline animation
            const stepTimer1 = setTimeout(() => {
                setStep('upload', 'done');
                setStep('aasist', 'active');
                setStep('gemini', 'active');
                setStep('rawnet2', 'active');
            }, 350);
            const stepTimer2 = setTimeout(() => { setStep('fusion', 'active'); }, 1100);

            try {
                const response = await fetch(getApiUrl('/api/predict'), {
                    method: 'POST',
                    body: formData,
                    cache: 'no-store'
                });

                clearTimeout(stepTimer1);
                clearTimeout(stepTimer2);

                const result = await response.json();
                if (!response.ok) throw new Error(result.error || "Inference failed");

                // Mark all steps done
                setStep('upload', 'done');
                setStep('aasist', 'done');
                setStep('gemini', result.gemini && result.gemini.available ? 'done' : 'skip');
                setStep('rawnet2', result.rawnet2 && result.rawnet2.available ? 'done' : 'skip');
                setStep('fusion', 'done');
                setStep('complete', 'done');

                // Brief pause so user sees completion, then render results
                setTimeout(() => {
                    if (elements.analysisStepsPanel) elements.analysisStepsPanel.classList.add('hidden');
                    renderFinalStitchAnalysisResults(result);
                    renderGeminiPanel(result);
                    drawFinalSpectralFingerprint(result.score);
                }, 350);

                // Add to Timeline & Session Telemetry
                const isHighRisk = result.status === "HIGH_RISK";
                const fusionPct = result.fusion ? result.fusion.finalScorePercent : result.genuine_probability_percent;
                addTelemetryEvent(
                    `File Verification Complete: ${result.filename}`,
                    `Genuine: ${result.genuine_probability_percent}% | Spoof: ${result.spoof_probability_percent}% | Fusion: ${fusionPct}%`,
                    isHighRisk ? "high_risk" : "safe"
                );

                recordSessionEvent({
                    timestamp: getFormattedDateTime(),
                    eventType: isHighRisk ? "Deepfake Audio File Detected" : "Human Voice Verification Passed",
                    source: `File: ${result.filename}`,
                    confidencePercent: `${result.genuine_probability_percent}%`,
                    confidenceRaw: result.score,
                    status: isHighRisk ? "BLOCKED" : (result.status === "SUSPICIOUS" ? "FLAGGED" : "CLEARED"),
                    riskLevel: result.status
                });

            } catch (err) {
                clearTimeout(stepTimer1);
                clearTimeout(stepTimer2);
                if (elements.analysisStepsPanel) elements.analysisStepsPanel.classList.add('hidden');
                alert(`Analysis Error: ${err.message}`);
            } finally {
                elements.btnExecuteAnalysis.removeAttribute('disabled');
                elements.btnExecuteAnalysis.textContent = "ANALYZE AUDIO";
            }
        });
    }

    function renderFinalStitchAnalysisResults(data) {
        if (elements.emptyState) elements.emptyState.classList.add('hidden');
        if (elements.resultsState) {
            elements.resultsState.classList.remove('hidden');
            elements.resultsState.classList.add('flex');
        }
        if (elements.analysisViz) {
            elements.analysisViz.classList.remove('hidden');
            elements.analysisViz.classList.add('flex');
        }

        const isHighRisk = data.status === "HIGH_RISK";
        const isSuspicious = data.status === "SUSPICIOUS";

        if (elements.scoreText) {
            elements.scoreText.textContent = `${data.genuine_probability_percent}%`;
            elements.scoreText.className = isHighRisk 
                ? "font-telemetry-mono text-2xl font-bold text-error" 
                : (isSuspicious ? "font-telemetry-mono text-2xl font-bold text-[#f59e0b]" : "font-telemetry-mono text-2xl font-bold text-[#10b981]");
        }

        if (elements.scoreSublabel) {
            elements.scoreSublabel.textContent = "Genuine";
        }

        if (elements.gaugeFill) {
            elements.gaugeFill.setAttribute('stroke-dasharray', `${data.genuine_probability_percent}, 100`);
            elements.gaugeFill.className = isHighRisk 
                ? "text-error stroke-current" 
                : (isSuspicious ? "text-[#f59e0b] stroke-current" : "text-[#10b981] stroke-current");
        }

        if (elements.statusBar) {
            elements.statusBar.className = isHighRisk 
                ? "absolute top-0 left-0 right-0 h-[2px] bg-error" 
                : (isSuspicious ? "absolute top-0 left-0 right-0 h-[2px] bg-[#f59e0b]" : "absolute top-0 left-0 right-0 h-[2px] bg-secondary");
        }

        if (elements.threatState) {
            elements.threatState.textContent = data.status;
            if (isHighRisk) {
                elements.threatState.className = "inline-block border border-error text-error bg-error-container px-3 py-1 font-label-caps text-label-caps rounded-sm uppercase";
            } else if (isSuspicious) {
                elements.threatState.className = "inline-block border border-tertiary-container text-tertiary-container bg-tertiary-fixed px-3 py-1 font-label-caps text-label-caps rounded-sm uppercase";
            } else {
                elements.threatState.className = "inline-block border border-secondary text-secondary bg-secondary-fixed px-3 py-1 font-label-caps text-label-caps rounded-sm uppercase";
            }
        }

        if (elements.metaGenuineProb) elements.metaGenuineProb.textContent = `${data.genuine_probability_percent}%`;
        if (elements.metaSpoofProb) elements.metaSpoofProb.textContent = `${data.spoof_probability_percent}%`;
        if (elements.metaDuration) elements.metaDuration.textContent = `${data.duration_sec}s`;
        if (elements.metaSamples) elements.metaSamples.textContent = data.samples;
        if (elements.spectralDurationLabel) elements.spectralDurationLabel.textContent = `${data.duration_sec}s`;

        if (elements.recommendationText) {
            if (isHighRisk) {
                elements.recommendationText.textContent = "Strong indicators of synthetic generation detected. Deepfake artifacts found in spectral frequency bands. BLOCK authentication request immediately.";
            } else if (isSuspicious) {
                elements.recommendationText.textContent = "Atypical spectral envelope detected. Secondary vocal liveness challenge recommended before proceeding.";
            } else {
                elements.recommendationText.textContent = "Audio profile matches natural human vocal patterns. No synthetic artifacts detected. Proceed with standard verification.";
            }
        }

        if (elements.primaryActionBtn) {
            if (isHighRisk) {
                elements.primaryActionBtn.textContent = "Block";
                elements.primaryActionBtn.className = "flex-1 bg-error text-on-error font-label-caps text-label-caps py-2 rounded-DEFAULT hover:bg-error/80 transition-colors uppercase";
            } else {
                elements.primaryActionBtn.textContent = "Verify";
                elements.primaryActionBtn.className = "flex-1 bg-primary text-on-primary font-label-caps text-label-caps py-2 rounded-DEFAULT hover:bg-surface-tint transition-colors uppercase";
            }
        }
    }

    function drawFinalSpectralFingerprint(score) {
        const canvas = elements.analysisSpectralCanvas;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        canvas.width = Math.max(100, rect.width * dpr);
        canvas.height = Math.max(50, rect.height * dpr);
        ctx.scale(dpr, dpr);

        const w = rect.width;
        const h = rect.height;
        ctx.clearRect(0, 0, w, h);

        const numBars = 80;
        const barWidth = Math.max(2, (w / numBars) - 2);
        const barGap = 2;
        const isHighRisk = score <= 0.3;

        let barColor = isHighRisk ? '#ba1a1a' : '#0058be';

        for (let i = 0; i < numBars; i++) {
            const norm = i / numBars;
            const pseudo = Math.abs(Math.sin(norm * 14 + score * 8) * Math.cos(norm * 7));
            const barH = Math.max(8, pseudo * (h * 0.9));
            const x = i * (barWidth + barGap);
            const y = h - barH;

            ctx.fillStyle = (i % 2 === 0) ? barColor : '#c6c6cd';
            ctx.fillRect(x, y, barWidth, barH);
        }
    }

    // =========================================================================
    // GEMINI PANEL RENDERING
    // =========================================================================

    /**
     * Set analysis step state: 'pending' | 'active' | 'done' | 'skip'
     */
    function setStep(stepId, state) {
        const el = document.getElementById(`step-${stepId}`);
        if (!el) return;
        const icon = el.querySelector('.step-icon');
        if (icon) icon.setAttribute('data-step-state', state);
    }

    /**
     * Get a CSS color string for a spoof percentage (0=safe, 100=spoof)
     */
    function spoofColor(spoofPct) {
        if (spoofPct >= 70) return '#ba1a1a'; // high risk
        if (spoofPct >= 40) return '#f59e0b'; // suspicious
        return '#10b981'; // safe
    }

    /**
     * Render the Gemini AI Analysis panel and all sub-components.
     * Called with the full /api/predict response object.
     */
    function renderGeminiPanel(data) {
        const gemini = data.gemini || {};
        const rawnet2 = data.rawnet2 || {};
        const fusion = data.fusion || {};

        // ── Active models string ──
        const activeModels = (fusion.modelsUsed && fusion.modelsUsed.length > 0)
            ? fusion.modelsUsed.join(' + ')
            : 'AASIST';
        if (elements.geminiStatusBadge) {
            elements.geminiStatusBadge.textContent = activeModels;
        }

        // ═════════════════════════════════════════════
        // LAYER A — INDIVIDUAL MODEL SCORES
        // ═════════════════════════════════════════════

        // ── A1. AASIST score bar (spoof direction) ──
        const aasistSpoofPct = fusion.aasistSpoof != null 
            ? Math.round(fusion.aasistSpoof * 100) 
            : (data.aasist && data.aasist.score != null ? Math.round((1 - data.aasist.score) * 100) : Math.round((1 - (data.score || 0)) * 100));
        const aasistWt = fusion.aasistWeight != null ? Math.round(fusion.aasistWeight * 100) : null;
        const aasistVerdict = fusion.individualVerdicts && fusion.individualVerdicts.AASIST
            ? fusion.individualVerdicts.AASIST : null;

        if (elements.aiAasistScore) elements.aiAasistScore.textContent = `${aasistSpoofPct}% spoof`;
        if (elements.aiAasistBar) {
            elements.aiAasistBar.style.width = `${aasistSpoofPct}%`;
            elements.aiAasistBar.style.backgroundColor = spoofColor(aasistSpoofPct);
        }
        const aiAasistWeight = document.getElementById('aiAasistWeight');
        if (aiAasistWeight) aiAasistWeight.textContent = aasistWt != null ? `wt ${aasistWt}%` : 'wt —';

        const aiAasistVerdict = document.getElementById('aiAasistVerdict');
        if (aiAasistVerdict && aasistVerdict) {
            aiAasistVerdict.textContent = aasistVerdict;
            aiAasistVerdict.className = 'font-telemetry-mono text-[9px] font-bold ' + verdictColor(aasistVerdict);
        }

        // ── A2. Gemini score bar ──
        if (gemini.available) {
            if (elements.geminiScoreRow) elements.geminiScoreRow.classList.remove('hidden');
            if (elements.geminiUnavailableRow) elements.geminiUnavailableRow.classList.add('hidden');

            const geminiSuspicion = gemini.suspicionScore != null ? gemini.suspicionScore : 0;
            const geminiWt = fusion.geminiWeight != null ? Math.round(fusion.geminiWeight * 100) : null;
            const geminiVerdict = fusion.individualVerdicts && fusion.individualVerdicts.Gemini
                ? fusion.individualVerdicts.Gemini : null;

            if (elements.aiGeminiScore) elements.aiGeminiScore.textContent = `${geminiSuspicion}% suspicion`;
            if (elements.aiGeminiBar) {
                elements.aiGeminiBar.style.width = `${geminiSuspicion}%`;
                elements.aiGeminiBar.style.backgroundColor = spoofColor(geminiSuspicion);
            }
            const aiGeminiWeight = document.getElementById('aiGeminiWeight');
            if (aiGeminiWeight) aiGeminiWeight.textContent = geminiWt != null ? `wt ${geminiWt}%` : 'wt —';

            const aiGeminiVerdict = document.getElementById('aiGeminiVerdict');
            if (aiGeminiVerdict && geminiVerdict) {
                aiGeminiVerdict.textContent = geminiVerdict;
                aiGeminiVerdict.className = 'font-telemetry-mono text-[9px] font-bold ' + verdictColor(geminiVerdict);
            }

            if (elements.aiGeminiClassification) {
                const cls = gemini.classification || 'UNCERTAIN';
                elements.aiGeminiClassification.textContent = cls;
                elements.aiGeminiClassification.className =
                    'font-telemetry-mono text-[10px] ' +
                    (cls === 'SYNTHETIC' ? 'text-[#ba1a1a]' :
                     cls === 'AUTHENTIC' ? 'text-[#10b981]' : 'text-on-surface-variant');
            }
        } else {
            if (elements.geminiScoreRow) elements.geminiScoreRow.classList.add('hidden');
            if (elements.geminiUnavailableRow) elements.geminiUnavailableRow.classList.remove('hidden');
        }

        // ── A3. RawNet2 score bar ──
        if (rawnet2.available && rawnet2.spoofScore != null) {
            if (elements.rawnet2ScoreRow) elements.rawnet2ScoreRow.classList.remove('hidden');
            if (elements.rawnet2UnavailableRow) elements.rawnet2UnavailableRow.classList.add('hidden');

            const rawnet2SpoofPct = Math.round(rawnet2.spoofScore * 100);
            const rawnet2Wt = fusion.rawnet2Weight != null ? Math.round(fusion.rawnet2Weight * 100) : null;
            const rawnet2Verdict = fusion.individualVerdicts && fusion.individualVerdicts.RawNet2
                ? fusion.individualVerdicts.RawNet2 : null;

            if (elements.aiRawnet2Score) elements.aiRawnet2Score.textContent = `${rawnet2SpoofPct}% spoof`;
            if (elements.aiRawnet2Bar) {
                elements.aiRawnet2Bar.style.width = `${rawnet2SpoofPct}%`;
                elements.aiRawnet2Bar.style.backgroundColor = spoofColor(rawnet2SpoofPct);
            }
            const aiRawnet2Weight = document.getElementById('aiRawnet2Weight');
            if (aiRawnet2Weight) aiRawnet2Weight.textContent = rawnet2Wt != null ? `wt ${rawnet2Wt}%` : 'wt —';

            const aiRawnet2Verdict = document.getElementById('aiRawnet2Verdict');
            if (aiRawnet2Verdict && rawnet2Verdict) {
                aiRawnet2Verdict.textContent = rawnet2Verdict;
                aiRawnet2Verdict.className = 'font-telemetry-mono text-[9px] font-bold ' + verdictColor(rawnet2Verdict);
            }

            if (elements.aiRawnet2Classification) {
                const cls = rawnet2.classification || 'UNCERTAIN';
                elements.aiRawnet2Classification.textContent = cls;
                elements.aiRawnet2Classification.className =
                    'font-telemetry-mono text-[10px] ' +
                    (cls === 'SYNTHETIC' ? 'text-[#ba1a1a]' :
                     cls === 'AUTHENTIC' ? 'text-[#10b981]' : 'text-on-surface-variant');
            }
        } else {
            if (elements.rawnet2ScoreRow) elements.rawnet2ScoreRow.classList.add('hidden');
            if (elements.rawnet2UnavailableRow) elements.rawnet2UnavailableRow.classList.remove('hidden');
        }

        // ═════════════════════════════════════════════
        // LAYER B — FUSION SCORE + DISAGREEMENT
        // ═════════════════════════════════════════════
        if (fusion.finalScore != null) {
            const fusionSpoofPct = Math.round((1 - (fusion.finalScore || 0)) * 100);

            if (elements.aiFusionScore) {
                elements.aiFusionScore.textContent = `${fusionSpoofPct}% spoof`;
                elements.aiFusionScore.className =
                    'font-telemetry-mono text-xs font-bold ' + (
                        fusionSpoofPct >= 70 ? 'text-[#ba1a1a]' :
                        fusionSpoofPct >= 40 ? 'text-[#f59e0b]' : 'text-[#10b981]'
                    );
            }
            if (elements.aiFusionBar) {
                elements.aiFusionBar.style.width = `${fusionSpoofPct}%`;
                elements.aiFusionBar.style.backgroundColor = spoofColor(fusionSpoofPct);
            }

            // Build weights string
            let weightsStr = '';
            if (fusion.modelsUsed && fusion.modelsUsed.length > 1) {
                const parts = [];
                if (fusion.modelsUsed.includes('AASIST')) parts.push(`A:${Math.round((fusion.aasistWeight || 0) * 100)}%`);
                if (fusion.modelsUsed.includes('Gemini')) parts.push(`G:${Math.round((fusion.geminiWeight || 0) * 100)}%`);
                if (fusion.modelsUsed.includes('RawNet2')) parts.push(`R:${Math.round((fusion.rawnet2Weight || 0) * 100)}%`);
                weightsStr = parts.join(' | ');
            } else {
                weightsStr = '100%';
            }
            if (elements.aiFusionModels) {
                elements.aiFusionModels.textContent = `${activeModels} (${weightsStr})`;
            }

            // Disagreement badge
            const disagreementBadge = document.getElementById('disagreementBadge');
            const disagreementDetail = document.getElementById('disagreementDetail');
            const disagreementVerdicts = document.getElementById('disagreementVerdicts');

            if (fusion.modelDisagreement) {
                if (disagreementBadge) disagreementBadge.classList.remove('hidden');
                if (disagreementDetail) disagreementDetail.classList.remove('hidden');
                if (disagreementVerdicts && fusion.individualVerdicts) {
                    const verdictParts = Object.entries(fusion.individualVerdicts)
                        .map(([model, verdict]) => `${model}: ${verdict}`)
                        .join(' | ');
                    disagreementVerdicts.textContent = verdictParts;
                }
            } else {
                if (disagreementBadge) disagreementBadge.classList.add('hidden');
                if (disagreementDetail) disagreementDetail.classList.add('hidden');
            }
        }

        // ═════════════════════════════════════════════
        // LAYER C — FINAL RISK CLASSIFICATION
        // ═════════════════════════════════════════════
        const finalClassification = fusion.classification || 'UNKNOWN';
        const aiFinalRiskPill = document.getElementById('aiFinalRiskPill');
        if (aiFinalRiskPill) {
            aiFinalRiskPill.textContent = finalClassification === 'HIGH_RISK' ? 'HIGH RISK'
                : finalClassification === 'SUSPICIOUS' ? 'UNCERTAIN'
                : finalClassification === 'SAFE' ? 'LOW RISK' : 'UNKNOWN';
            aiFinalRiskPill.className = 'font-label-caps text-[10px] font-bold px-3 py-1.5 rounded border ' + (
                finalClassification === 'HIGH_RISK'
                    ? 'border-error text-error bg-error-container'
                    : finalClassification === 'SUSPICIOUS'
                        ? 'border-[#f59e0b] text-[#92400e] bg-[#fef3c7]'
                        : 'border-secondary text-secondary bg-secondary-fixed'
            );
        }

        // Threshold display
        const aiThresholdDisplay = document.getElementById('aiThresholdDisplay');
        if (aiThresholdDisplay) {
            const lowT = fusion.lowRiskThreshold != null ? fusion.lowRiskThreshold : 0.40;
            const highT = fusion.highRiskThreshold != null ? fusion.highRiskThreshold : 0.70;
            aiThresholdDisplay.textContent = `low=${lowT.toFixed(2)} | high=${highT.toFixed(2)}`;
        }

        // Confidence
        const aiFusionConfidence = document.getElementById('aiFusionConfidence');
        if (aiFusionConfidence && fusion.confidence != null) {
            aiFusionConfidence.textContent = `Confidence: ${fusion.confidence}%`;
        }

        // ── MODEL_CORE metadata cell ──
        if (elements.metaModelCore) {
            elements.metaModelCore.textContent = activeModels;
        }

        // ── Detection Evidence ──
        const evidence = gemini.available ? (gemini.evidence || []) : [];
        if (evidence.length > 0 && elements.evidencePanel && elements.evidenceList) {
            elements.evidencePanel.classList.remove('hidden');
            elements.evidenceList.innerHTML = evidence.map(e =>
                `<li class="flex items-start gap-2 font-telemetry-mono text-[11px] text-on-surface">
                    <span class="material-symbols-outlined text-[14px] text-[#10b981] flex-shrink-0 mt-0.5">check_circle</span>
                    <span>${escapeHtml(e)}</span>
                 </li>`
            ).join('');

            const limits = gemini.limitations || [];
            if (limits.length > 0) {
                elements.evidenceList.innerHTML += limits.map(l =>
                    `<li class="flex items-start gap-2 font-telemetry-mono text-[11px] text-on-surface-variant mt-2">
                        <span class="material-symbols-outlined text-[14px] text-outline flex-shrink-0 mt-0.5">info</span>
                        <span>${escapeHtml(l)}</span>
                     </li>`
                ).join('');
            }
        } else if (elements.evidencePanel) {
            elements.evidencePanel.classList.add('hidden');
        }

        // ── Suspicious Segments ──
        const segments = gemini.available ? (gemini.suspiciousSegments || []) : [];
        renderSuspiciousSegments(segments, data.duration_sec || 0);
    }

    /**
     * Map a verdict string to a Tailwind text-color class.
     */
    function verdictColor(verdict) {
        if (verdict === 'HIGH_RISK') return 'text-[#ba1a1a]';
        if (verdict === 'SUSPICIOUS') return 'text-[#f59e0b]';
        return 'text-[#10b981]';
    }

    /**
     * Render suspicious segment markers on the timeline.
     */
    function renderSuspiciousSegments(segments, durationSec) {
        if (!elements.segmentsPanel || !elements.segmentsTimeline || !elements.segmentsList) return;

        if (!segments || segments.length === 0) {
            elements.segmentsPanel.classList.add('hidden');
            return;
        }

        elements.segmentsPanel.classList.remove('hidden');

        const totalDur = Math.max(durationSec, 1);
        if (elements.segmentsDurationLabel) {
            elements.segmentsDurationLabel.textContent = `${totalDur.toFixed(1)}s`;
        }

        // Render timeline markers
        elements.segmentsTimeline.innerHTML = segments.map(seg => {
            const leftPct = Math.max(0, Math.min(100, (seg.start / totalDur) * 100));
            const widthPct = Math.max(1, Math.min(100 - leftPct, ((seg.end - seg.start) / totalDur) * 100));
            return `<div class="segment-marker" style="left:${leftPct}%;width:${widthPct}%" title="${escapeHtml(seg.reason)} (${seg.start.toFixed(1)}s–${seg.end.toFixed(1)}s)"></div>`;
        }).join('');

        // Render text list
        elements.segmentsList.innerHTML = segments.map(seg =>
            `<li class="font-telemetry-mono text-[10px] text-on-surface-variant flex items-center gap-1">
                <span class="text-[#ba1a1a]">▐</span>
                <span class="font-bold text-on-surface">${seg.start.toFixed(1)}s–${seg.end.toFixed(1)}s</span>
                — ${escapeHtml(seg.reason)}
             </li>`
        ).join('');
    }

    /**
     * Basic HTML escape to prevent XSS from Gemini string fields.
     */
    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    // =========================================================================
    // 11. SESSION TELEMETRY (ATTACK HISTORY) CONTROLLER
    // =========================================================================
    function recordSessionEvent(eventData) {
        sessionLogs.unshift(eventData);
        renderSessionTelemetryTable();
        updateAnalyticsScreen();
    }

    function renderSessionTelemetryTable() {
        if (!elements.telemetryTableBody) return;

        let filtered = sessionLogs.filter(item => {
            const matchesFilter = activeTelemetryFilter === 'ALL' || item.riskLevel === activeTelemetryFilter;
            const matchesSearch = !telemetrySearchQuery || 
                                  item.eventType.toLowerCase().includes(telemetrySearchQuery) ||
                                  item.source.toLowerCase().includes(telemetrySearchQuery);
            return matchesFilter && matchesSearch;
        });

        if (filtered.length === 0) {
            elements.telemetryTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="p-6 text-center text-on-surface-variant">
                        No session telemetry records match the current filter.
                    </td>
                </tr>
            `;
            if (elements.telemetryCountLabel) {
                elements.telemetryCountLabel.textContent = `Showing 0 of ${sessionLogs.length} session records`;
            }
            return;
        }

        elements.telemetryTableBody.innerHTML = filtered.map(item => {
            let statusBadge = `<span class="inline-flex items-center gap-1 px-2 py-0.5 bg-surface-container-high text-on-surface-variant font-label-caps text-label-caps rounded-DEFAULT border border-outline-variant"><span class="w-1.5 h-1.5 rounded-full bg-outline"></span>CLEARED</span>`;
            let barColor = "bg-secondary";
            let scoreTextColor = "text-on-surface";

            if (item.status === "BLOCKED") {
                statusBadge = `<span class="inline-flex items-center gap-1 px-2 py-0.5 bg-error-container text-on-error-container font-label-caps text-label-caps rounded-DEFAULT border border-error/20"><span class="w-1.5 h-1.5 rounded-full bg-error"></span>BLOCKED</span>`;
                barColor = "bg-error";
                scoreTextColor = "text-error";
            } else if (item.status === "FLAGGED") {
                statusBadge = `<span class="inline-flex items-center gap-1 px-2 py-0.5 bg-tertiary-fixed text-on-tertiary-fixed font-label-caps text-label-caps rounded-DEFAULT border border-tertiary-container/20"><span class="w-1.5 h-1.5 rounded-full bg-tertiary-container"></span>FLAGGED</span>`;
                barColor = "bg-tertiary-container";
                scoreTextColor = "text-tertiary-container";
            }

            const rawVal = typeof item.confidenceRaw === 'number' ? Math.round(item.confidenceRaw * 100) : 90;

            return `
                <tr class="border-b border-outline-variant hover:bg-surface-container-low transition-colors group">
                    <td class="py-3 px-4 text-on-surface-variant">${item.timestamp}</td>
                    <td class="py-3 px-4 font-body-base text-body-base text-on-surface">${item.eventType}</td>
                    <td class="py-3 px-4">${item.source}</td>
                    <td class="py-3 px-4">
                        <div class="flex items-center gap-2">
                            <div class="w-16 h-1 bg-surface-variant rounded-full overflow-hidden">
                                <div class="h-full ${barColor}" style="width: ${rawVal}%"></div>
                            </div>
                            <span class="${scoreTextColor}">${item.confidencePercent}</span>
                        </div>
                    </td>
                    <td class="py-3 px-4">${statusBadge}</td>
                    <td class="py-3 px-4 text-right">
                        <button type="button" class="text-secondary hover:text-on-secondary-fixed-variant font-label-caps text-label-caps opacity-0 group-hover:opacity-100 transition-opacity" onclick="window.showPrototypeNotice('Telemetry Trace: ${item.eventType}')">VIEW TRACE</button>
                    </td>
                </tr>
            `;
        }).join('');

        if (elements.telemetryCountLabel) {
            elements.telemetryCountLabel.textContent = `Showing 1-${filtered.length} of ${sessionLogs.length} events`;
        }

        if (elements.bentoTotalInferences) {
            elements.bentoTotalInferences.textContent = sessionLogs.length;
        }

        // Update Risk Trend
        const hasRecentAttack = sessionLogs.slice(0, 5).some(e => e.riskLevel === "HIGH_RISK");
        if (elements.bentoRiskTrend && elements.bentoTrendMeta && elements.bentoRiskIconWrapper) {
            if (hasRecentAttack) {
                elements.bentoRiskTrend.textContent = "ELEVATED";
                elements.bentoRiskTrend.className = "font-display-lg text-headline-md text-error tracking-tight";
                elements.bentoTrendMeta.textContent = "High-risk spoofing active";
                elements.bentoRiskIconWrapper.className = "w-12 h-12 bg-error-container rounded-full flex items-center justify-center border border-error/20";
                if (elements.bentoRiskIcon) {
                    elements.bentoRiskIcon.textContent = "warning";
                    elements.bentoRiskIcon.className = "material-symbols-outlined text-error";
                }
            } else {
                elements.bentoRiskTrend.textContent = "STABLE";
                elements.bentoRiskTrend.className = "font-display-lg text-headline-md text-[#10b981] tracking-tight";
                elements.bentoTrendMeta.textContent = "No active spoof threat";
                elements.bentoRiskIconWrapper.className = "w-12 h-12 bg-surface-container-low rounded-full flex items-center justify-center border border-outline-variant";
                if (elements.bentoRiskIcon) {
                    elements.bentoRiskIcon.textContent = "security";
                    elements.bentoRiskIcon.className = "material-symbols-outlined text-secondary";
                }
            }
        }
    }

    // Telemetry Filter Buttons
    elements.telemetryFilterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            elements.telemetryFilterBtns.forEach(b => {
                b.classList.remove('bg-primary', 'text-on-primary', 'border-primary', 'active');
                b.classList.add('bg-surface', 'text-on-surface-variant', 'border-outline-variant');
            });
            btn.classList.add('bg-primary', 'text-on-primary', 'border-primary', 'active');
            btn.classList.remove('bg-surface', 'text-on-surface-variant', 'border-outline-variant');
            activeTelemetryFilter = btn.dataset.filter;
            renderSessionTelemetryTable();
        });
    });

    if (elements.telemetrySearchInput) {
        elements.telemetrySearchInput.addEventListener('input', (e) => {
            telemetrySearchQuery = e.target.value.toLowerCase().trim();
            renderSessionTelemetryTable();
        });
    }

    // CSV Export
    if (elements.btnTelemetryExportCsv) {
        elements.btnTelemetryExportCsv.addEventListener('click', () => {
            if (sessionLogs.length === 0) {
                alert("No session telemetry records to export yet.");
                return;
            }

            const headers = ["Timestamp (UTC)", "Event / Detection Result", "Source", "Confidence", "Status", "Risk Level"];
            const rows = sessionLogs.map(l => [
                `"${l.timestamp}"`,
                `"${l.eventType.replace(/"/g, '""')}"`,
                `"${l.source}"`,
                `"${l.confidencePercent}"`,
                `"${l.status}"`,
                `"${l.riskLevel}"`
            ]);

            const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", `voiceguard_session_telemetry_${Date.now()}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            addTelemetryEvent("Telemetry Exported", "voiceguard_session_telemetry.csv", "action");
        });
    }

    // =========================================================================
    // 12. ANALYTICS AGGREGATES
    // =========================================================================
    function updateAnalyticsScreen() {
        if (sessionLogs.length === 0) return;

        let safe = 0, suspicious = 0, highRisk = 0, totalScore = 0, validScores = 0;

        sessionLogs.forEach(item => {
            if (item.riskLevel === "SAFE") safe++;
            else if (item.riskLevel === "SUSPICIOUS") suspicious++;
            else if (item.riskLevel === "HIGH_RISK") highRisk++;

            const num = parseFloat(item.confidencePercent);
            if (!isNaN(num)) {
                totalScore += num;
                validScores++;
            }
        });

        if (elements.anaSafeCount) elements.anaSafeCount.textContent = safe;
        if (elements.anaSuspiciousCount) elements.anaSuspiciousCount.textContent = suspicious;
        if (elements.anaHighRiskCount) elements.anaHighRiskCount.textContent = highRisk;
        if (elements.anaTotalCount) elements.anaTotalCount.textContent = sessionLogs.length;

        if (validScores > 0 && elements.analyticsAvgVal && elements.analyticsAvgBar) {
            const avg = (totalScore / validScores).toFixed(1);
            elements.analyticsAvgVal.textContent = `${avg}%`;
            elements.analyticsAvgBar.style.width = `${avg}%`;
        }
    }

    // =========================================================================
    // 13. PROTOTYPE NOTICE MODAL
    // =========================================================================
    window.showPrototypeNotice = function(featureName) {
        const modal = document.getElementById('prototypeModal');
        const title = document.getElementById('modalTitle');
        const body = document.getElementById('modalBody');
        if (modal && title && body) {
            title.textContent = featureName || "Enterprise Security Feature";
            body.textContent = `The "${featureName}" capability is designed as a planned enterprise mitigation tier in the Stitch specifications. In this prototype, real-time AASIST detection is fully operational, while downstream interception rules are marked as PLANNED.`;
            modal.classList.remove('hidden');
        }
    };

    // =========================================================================
    // 14. SETTINGS CUSTOM BACKEND HANDLER
    // =========================================================================
    const settingsBackendUrlInput = document.getElementById('settingsBackendUrlInput');
    const btnSaveBackendUrl = document.getElementById('btnSaveBackendUrl');
    const settingsCurrentEndpointLabel = document.getElementById('settingsCurrentEndpointLabel');

    if (settingsBackendUrlInput && btnSaveBackendUrl) {
        const savedUrl = localStorage.getItem('VOICEGUARD_BACKEND_URL') || '';
        settingsBackendUrlInput.value = savedUrl;
        if (settingsCurrentEndpointLabel) {
            settingsCurrentEndpointLabel.textContent = savedUrl.trim() ? savedUrl.trim() : "Default (Same Origin)";
        }

        btnSaveBackendUrl.addEventListener('click', () => {
            const val = settingsBackendUrlInput.value.trim();
            if (val) {
                localStorage.setItem('VOICEGUARD_BACKEND_URL', val);
                if (settingsCurrentEndpointLabel) settingsCurrentEndpointLabel.textContent = val;
                alert(`Live Backend Endpoint updated to: ${val}`);
            } else {
                localStorage.removeItem('VOICEGUARD_BACKEND_URL');
                if (settingsCurrentEndpointLabel) settingsCurrentEndpointLabel.textContent = "Default (Same Origin)";
                alert("Live Backend Endpoint reset to Default (Same Origin).");
            }
            if (liveManager) liveManager.checkBackendHealth();
        });
    }

    // =========================================================================
    // 15. INITIALIZE POLLING
    // =========================================================================
    fetchStatus();
    setInterval(fetchStatus, 1000);
});

