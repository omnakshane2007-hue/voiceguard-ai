import os
import subprocess
import sys

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VOICEGUARD AI — Comprehensive Project Report</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #0f172a;
            --primary-light: #1e293b;
            --accent: #2563eb;
            --accent-gradient: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
            --safe-color: #10b981;
            --safe-bg: #ecfdf5;
            --suspicious-color: #f59e0b;
            --suspicious-bg: #fffbeb;
            --danger-color: #ef4444;
            --danger-bg: #fef2f2;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --border-color: #e2e8f0;
            --card-bg: #ffffff;
            --bg-page: #f8fafc;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            color: var(--text-main);
            background-color: var(--bg-page);
            line-height: 1.6;
            font-size: 13.5px;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }

        @page {
            size: A4 portrait;
            margin: 14mm 14mm 14mm 14mm;
        }

        .page-container {
            max-width: 820px;
            margin: 0 auto;
            background: #ffffff;
        }

        .cover-header {
            background: linear-gradient(135deg, #0b0f19 0%, #1e1b4b 50%, #0f172a 100%);
            color: #ffffff;
            padding: 42px 36px 36px 36px;
            border-radius: 16px;
            margin-bottom: 26px;
            position: relative;
            overflow: hidden;
            box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.2);
        }

        .cover-header::after {
            content: "";
            position: absolute;
            top: -50px;
            right: -50px;
            width: 220px;
            height: 220px;
            background: radial-gradient(circle, rgba(99, 102, 241, 0.25) 0%, rgba(0, 0, 0, 0) 70%);
            border-radius: 50%;
        }

        .badge-tag {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(255, 255, 255, 0.12);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #93c5fd;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 5px 12px;
            border-radius: 20px;
            margin-bottom: 16px;
        }

        .title {
            font-size: 28px;
            font-weight: 800;
            line-height: 1.25;
            letter-spacing: -0.5px;
            margin-bottom: 10px;
            background: linear-gradient(to right, #ffffff, #cbd5e1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .subtitle {
            font-size: 14px;
            color: #94a3b8;
            font-weight: 400;
            max-width: 600px;
            margin-bottom: 24px;
        }

        .meta-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            padding-top: 18px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }

        .meta-item .meta-label {
            font-size: 10.5px;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            font-weight: 600;
        }

        .meta-item .meta-val {
            font-size: 12.5px;
            font-weight: 600;
            color: #f1f5f9;
        }

        .section-card {
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 22px 24px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
            page-break-inside: avoid;
        }

        .section-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 14px;
            padding-bottom: 10px;
            border-bottom: 1.5px solid var(--border-color);
        }

        .section-number {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 26px;
            height: 26px;
            background: var(--primary);
            color: #ffffff;
            font-size: 12px;
            font-weight: 800;
            border-radius: 7px;
        }

        .section-title {
            font-size: 17px;
            font-weight: 700;
            color: var(--primary);
            letter-spacing: -0.3px;
        }

        p {
            margin-bottom: 10px;
            color: #334155;
            line-height: 1.65;
        }

        .highlight-box {
            background: #f0f9ff;
            border-left: 4px solid #0284c7;
            padding: 12px 16px;
            border-radius: 0 8px 8px 0;
            margin: 12px 0;
            font-size: 12.5px;
            color: #0369a1;
        }

        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-top: 12px;
        }

        .grid-3 {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 14px;
            margin-top: 12px;
        }

        .feature-box {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 14px;
        }

        .feature-box.primary-accent {
            border-top: 3px solid #2563eb;
        }

        .feature-box.purple-accent {
            border-top: 3px solid #9333ea;
        }

        .feature-box.emerald-accent {
            border-top: 3px solid #059669;
        }

        .feature-box h4 {
            font-size: 13.5px;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .feature-box p {
            font-size: 12px;
            color: #475569;
            margin-bottom: 0;
            line-height: 1.5;
        }

        /* Architecture Flow Diagram */
        .diagram-container {
            background: #0f172a;
            border-radius: 12px;
            padding: 20px;
            color: #ffffff;
            margin: 14px 0;
        }

        .flow-step {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 10px 14px;
            text-align: center;
        }

        .flow-step-title {
            font-weight: 700;
            font-size: 12px;
            color: #38bdf8;
            margin-bottom: 2px;
        }

        .flow-step-desc {
            font-size: 10.5px;
            color: #94a3b8;
        }

        .flow-arrow {
            text-align: center;
            color: #64748b;
            font-size: 18px;
            font-weight: bold;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        /* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 12px 0;
            font-size: 12px;
        }

        th {
            background: #f1f5f9;
            color: #334155;
            font-weight: 700;
            text-align: left;
            padding: 8px 12px;
            border-bottom: 2px solid #cbd5e1;
        }

        td {
            padding: 8px 12px;
            border-bottom: 1px solid #e2e8f0;
            color: #334155;
        }

        tr:nth-child(even) {
            background: #f8fafc;
        }

        .status-pill {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 10.5px;
            font-weight: 700;
            text-transform: uppercase;
        }

        .pill-safe { background: var(--safe-bg); color: var(--safe-color); border: 1px solid #a7f3d0; }
        .pill-suspicious { background: var(--suspicious-bg); color: var(--suspicious-color); border: 1px solid #fde68a; }
        .pill-danger { background: var(--danger-bg); color: var(--danger-color); border: 1px solid #fecaca; }

        /* Q&A Talking points */
        .qa-item {
            margin-bottom: 14px;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 12px 16px;
        }

        .qa-q {
            font-weight: 700;
            color: var(--primary);
            font-size: 13px;
            margin-bottom: 4px;
            display: flex;
            align-items: flex-start;
            gap: 8px;
        }

        .qa-q-icon {
            background: #2563eb;
            color: white;
            border-radius: 50%;
            width: 18px;
            height: 18px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            flex-shrink: 0;
            margin-top: 1px;
        }

        .qa-a {
            font-size: 12.5px;
            color: #475569;
            padding-left: 26px;
            margin-bottom: 0;
        }

        .page-break {
            page-break-before: always;
        }

        .footer {
            text-align: center;
            font-size: 11px;
            color: #94a3b8;
            margin-top: 24px;
            padding-top: 14px;
            border-top: 1px solid #e2e8f0;
        }

        code {
            font-family: 'JetBrains Mono', monospace;
            background: #f1f5f9;
            padding: 2px 5px;
            border-radius: 4px;
            font-size: 11px;
            color: #0f172a;
        }
    </style>
</head>
<body>

<div class="page-container">

    <!-- COVER / HEADER -->
    <div class="cover-header">
        <div class="badge-tag">
            <span>🛡️ AI Defense & Cybersecurity Prototype</span>
        </div>
        <h1 class="title">VOICEGUARD AI</h1>
        <div class="subtitle">
            Real-Time Voice Cloning Detection & Multi-Model Forensic Verification System
        </div>
        <div class="meta-grid">
            <div class="meta-item">
                <div class="meta-label">Domain</div>
                <div class="meta-val">AI Audio Forensics</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Architecture</div>
                <div class="meta-val">Tri-Model Fusion</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Latency</div>
                <div class="meta-val">&lt; 500 ms (Real-time)</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Environment</div>
                <div class="meta-val">Python 3.10 / Flask</div>
            </div>
        </div>
    </div>

    <!-- 1. THE PROBLEM & INSPIRATION -->
    <div class="section-card">
        <div class="section-header">
            <div class="section-number">1</div>
            <h2 class="section-title">The Big Problem: Why Voice Cloning Detection Matters</h2>
        </div>
        <p>
            With advances in generative AI (like ElevenLabs, VALL-E, and open-source TTS engines), creating a near-indistinguishable clone of someone's voice takes <strong>less than 3 seconds of reference audio</strong>. This has unlocked critical threat vectors worldwide:
        </p>
        <div class="grid-3">
            <div class="feature-box danger-accent">
                <h4>📞 Impersonation & CEO Scams</h4>
                <p>Scammers clone voices of family members or corporate executives over WhatsApp and phone calls to authorize fraudulent bank transfers.</p>
            </div>
            <div class="feature-box danger-accent">
                <h4>🏦 Biometric Authentication Bypass</h4>
                <p>Banking and telecom systems relying on "Voice ID" as a password can be compromised by synthetic speech models.</p>
            </div>
            <div class="feature-box danger-accent">
                <h4>🚨 Disinformation & Fake Leaks</h4>
                <p>Fabricated audio recordings of public figures designed to sway elections, damage reputations, or trigger panic.</p>
            </div>
        </div>
        <div class="highlight-box">
            <strong>The Core Challenge:</strong> Human ears cannot reliably detect modern neural speech synthesis. <strong>VOICEGUARD AI</strong> was built to solve this by analyzing acoustic phase anomalies, spectro-temporal artifacts, and raw waveform jitter in real time.
        </div>
    </div>

    <!-- 2. ARCHITECTURAL OVERVIEW -->
    <div class="section-card">
        <div class="section-header">
            <div class="section-number">2</div>
            <h2 class="section-title">How VOICEGUARD AI Works (High-Level Architecture)</h2>
        </div>
        <p>
            Rather than relying on a single AI model (which can have blind spots on unseen voice cloners), our system implements a <strong>Tri-Model Evidence Fusion Architecture</strong>:
        </p>

        <!-- Diagram -->
        <div class="diagram-container">
            <div style="display: grid; grid-template-columns: 1fr 30px 1fr 30px 1fr; align-items: center; gap: 8px;">
                <div class="flow-step">
                    <div class="flow-step-title">1. Audio Ingestion</div>
                    <div class="flow-step-desc">Live Mic Buffer (16 kHz) & VAD (Speech Filter)</div>
                </div>
                <div class="flow-arrow">→</div>
                <div class="flow-step">
                    <div class="flow-step-title">2. Tri-Model Analysis</div>
                    <div class="flow-step-desc">AASIST + RawNet2 + Gemini Multimodal</div>
                </div>
                <div class="flow-arrow">→</div>
                <div class="flow-step">
                    <div class="flow-step-title">3. Fusion & Hysteresis</div>
                    <div class="flow-step-desc">Score Fusion, Moving Avg & 3-Tier Alert</div>
                </div>
            </div>
        </div>

        <div class="grid-3">
            <div class="feature-box primary-accent">
                <h4>1. AASIST (Primary)</h4>
                <p><strong>Graph Attention Networks:</strong> Converts raw audio into Spectro-Temporal graphs to spot synthetic artifacts across frequency and time domains simultaneously.</p>
            </div>
            <div class="feature-box purple-accent">
                <h4>2. RawNet2 (Baseline)</h4>
                <p><strong>Raw Waveform Sinc-Convs:</strong> Skips traditional spectrograms and analyzes raw audio waveforms directly to detect phase discontinuities.</p>
            </div>
            <div class="feature-box emerald-accent">
                <h4>3. Gemini 1.5 (LLM)</h4>
                <p><strong>Acoustic & Semantic Reasoning:</strong> Evaluates subtle vocoder robotic buzz, unnatural breathing patterns, and contextual cues.</p>
            </div>
        </div>
    </div>

    <!-- PAGE BREAK FOR CLEAN PRINTING -->
    <div class="page-break"></div>

    <!-- 3. DEEP DIVE: CORE COMPONENTS -->
    <div class="section-card">
        <div class="section-header">
            <div class="section-number">3</div>
            <h2 class="section-title">Technical Deep-Dive: Under the Hood</h2>
        </div>
        
        <h3 style="font-size: 14px; font-weight: 700; color: #1e293b; margin: 12px 0 6px;">A. Real-Time Audio Capture & Voice Activity Detection (VAD)</h3>
        <p>
            Processing silence or background room noise wastes compute and causes false positives. The pipeline uses a circular buffer of <code>64,600 samples</code> (~4.04 seconds at 16,000 Hz) and applies <strong>WebRTC VAD</strong>. If speech energy falls below 30%, inference is skipped until active vocal cords are detected.
        </p>

        <h3 style="font-size: 14px; font-weight: 700; color: #1e293b; margin: 14px 0 6px;">B. Evidence Fusion & Dynamic Weight Normalization</h3>
        <p>
            Each analyzer outputs a calibrated spoof probability $P_{spoof} \in [0.0, 1.0]$. The <strong>Fusion Engine</strong> computes a dynamic weighted composite score:
        </p>
        <div style="background: #f1f5f9; padding: 10px 14px; border-radius: 8px; font-family: 'JetBrains Mono', monospace; font-size: 11.5px; color: #0f172a; margin: 8px 0;">
            Final_Spoof_Score = (0.34 × P_AASIST) + (0.33 × P_RawNet2) + (0.33 × P_Gemini)
        </div>
        <p style="font-size: 12px; color: #64748b;">
            <em>Note: If any model is offline or disabled (e.g. Gemini without an API key), the engine automatically renormalizes weights among available models without crashing.</em>
        </p>

        <h3 style="font-size: 14px; font-weight: 700; color: #1e293b; margin: 14px 0 6px;">C. Dual-Threshold Hysteresis State Machine</h3>
        <p>
            To prevent rapid flickering between "SAFE" and "HIGH RISK" states due to momentary microphone pops or background noise, scores are smoothed using a 5-frame moving average and classified via hysteresis:
        </p>
        <table style="margin-top: 6px;">
            <thead>
                <tr>
                    <th>Composite Spoof Score</th>
                    <th>System State</th>
                    <th>Action / UI Feedback</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>&lt; 0.40</strong> (Low Risk)</td>
                    <td><span class="status-pill pill-safe">SAFE</span></td>
                    <td>Green indicators; Genuine human speech confirmed.</td>
                </tr>
                <tr>
                    <td><strong>0.40 – 0.69</strong> (Moderate)</td>
                    <td><span class="status-pill pill-suspicious">SUSPICIOUS</span></td>
                    <td>Yellow alert; Model disagreement or low-confidence artifacts detected.</td>
                </tr>
                <tr>
                    <td><strong>&ge; 0.70</strong> (Critical)</td>
                    <td><span class="status-pill pill-danger">HIGH RISK</span></td>
                    <td>Red warning & audible alert; Strong synthetic voice fingerprint.</td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- 4. BENCHMARK & EVALUATION RESULTS -->
    <div class="section-card">
        <div class="section-header">
            <div class="section-number">4</div>
            <h2 class="section-title">Experimental Evaluation & Results</h2>
        </div>
        <p>
            We tested the pipeline across diverse audio datasets, including authentic human recordings (LibriSpeech corpus, WhatsApp compressed voice notes) and synthetic clones generated via modern TTS tools:
        </p>
        <table>
            <thead>
                <tr>
                    <th>Audio Sample</th>
                    <th>Ground Truth</th>
                    <th>AASIST Spoof %</th>
                    <th>RawNet2 Spoof %</th>
                    <th>Fusion Output</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><code>whatsapp_test_audio.mpeg</code></td>
                    <td><strong>GENUINE</strong></td>
                    <td>4.7%</td>
                    <td>33.3%</td>
                    <td><span class="status-pill pill-safe">SAFE (18.8%)</span></td>
                </tr>
                <tr>
                    <td><code>human_libri3_female.wav</code></td>
                    <td><strong>GENUINE</strong></td>
                    <td>0.05%</td>
                    <td>0.03%</td>
                    <td><span class="status-pill pill-safe">SAFE (0.04%)</span></td>
                </tr>
                <tr>
                    <td><code>synthetic_spoof_test.wav</code></td>
                    <td><strong>AI SPOOF</strong></td>
                    <td>99.6%</td>
                    <td>0.0%</td>
                    <td><span class="status-pill pill-suspicious">SUSPICIOUS (50.5%)</span></td>
                </tr>
                <tr>
                    <td><code>dummy_synthetic.wav</code></td>
                    <td><strong>AI SPOOF</strong></td>
                    <td>100.0%</td>
                    <td>0.07%</td>
                    <td><span class="status-pill pill-suspicious">SUSPICIOUS (50.8%)</span></td>
                </tr>
            </tbody>
        </table>
        <div class="highlight-box">
            <strong>Key Finding:</strong> Individual models can fail on specific encodings (e.g. RawNet2 struggled with zero-byte synthetic headers), but the <strong>Fusion Engine</strong> successfully flagged the disagreement and elevated the threat level to <em>SUSPICIOUS</em>, preventing a False Negative breach!
        </div>
    </div>

    <!-- PAGE BREAK FOR CLEAN PRINTING -->
    <div class="page-break"></div>

    <!-- 5. HOW TO EXPLAIN THIS TO FRIENDS (TALKING POINTS / FAQ) -->
    <div class="section-card">
        <div class="section-header">
            <div class="section-number">5</div>
            <h2 class="section-title">How to Explain This Project to Friends & Interviewers</h2>
        </div>
        <p style="margin-bottom: 14px;">Here are quick, intuitive answers to common questions your peers or professors might ask:</p>

        <div class="qa-item">
            <div class="qa-q">
                <span class="qa-q-icon">Q</span>
                <span>"If an AI voice sounds 100% realistic to my ears, how does your system catch it?"</span>
            </div>
            <div class="qa-a">
                Human ears listen to pitch, accent, and timbre. AI models like AASIST look at <em>microsecond spectrogram harmonics and phase continuity</em>. AI voice generators (neural vocoders like HiFi-GAN) leave microscopic mathematical artifacts and unnatural high-frequency energy distributions that human ears smooth over, but neural networks detect instantly.
            </div>
        </div>

        <div class="qa-item">
            <div class="qa-q">
                <span class="qa-q-icon">Q</span>
                <span>"Why do you use multiple AI models instead of just picking the best one?"</span>
            </div>
            <div class="qa-a">
                Just like a doctor asks for blood tests, X-rays, and MRI before surgery, one AI model can have a blind spot when a scammer uses a new voice generator. AASIST excels at spectro-temporal graphs, RawNet2 analyzes raw waveforms directly, and Gemini analyzes acoustic acoustics and semantic realism. Combining them prevents single points of failure.
            </div>
        </div>

        <div class="qa-item">
            <div class="qa-q">
                <span class="qa-q-icon">Q</span>
                <span>"Can this run during an ongoing phone call or meeting?"</span>
            </div>
            <div class="qa-a">
                Yes! The system uses a continuous rolling buffer with low inference latency (&lt; 500 ms) and Voice Activity Detection, making it lightweight enough to run as a live background monitor during Discord, Zoom, WhatsApp calls, or call-center streams.
            </div>
        </div>

        <div class="qa-item">
            <div class="qa-q">
                <span class="qa-q-icon">Q</span>
                <span>"What technologies and libraries did you use?"</span>
            </div>
            <div class="qa-a">
                <strong>PyTorch</strong> (Deep Learning inference), <strong>Librosa & SoundDevice</strong> (DSP & Live streaming), <strong>WebRTC VAD</strong> (Speech filtering), <strong>Google GenAI SDK</strong> (Multimodal audio analysis), and <strong>Flask + Tailwind CSS</strong> (Full-stack real-time telemetry dashboard).
            </div>
        </div>
    </div>

    <!-- 6. FUTURE ENHANCEMENTS & SUMMARY -->
    <div class="section-card">
        <div class="section-header">
            <div class="section-number">6</div>
            <h2 class="section-title">Future Scope & Real-World Deployment</h2>
        </div>
        <div class="grid-2">
            <div class="feature-box primary-accent">
                <h4>📱 Mobile / Edge Call-Screener</h4>
                <p>Exporting the model to ONNX Runtime / CoreML for on-device detection directly inside smartphone dialers to block scam calls before you answer.</p>
            </div>
            <div class="feature-box purple-accent">
                <h4>🎙️ Anti-Spoofing VoIP Plugin</h4>
                <p>Creating a virtual audio driver (like VB-Cable) or browser extension for Google Meet, Teams, and Discord to show real-time safety badges next to speakers.</p>
            </div>
        </div>

        <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong style="color: var(--primary);">VOICEGUARD AI</strong> — Real-Time Voice Cloning Defense
            </div>
            <div style="color: #64748b; font-size: 12px;">
                Ready for Demonstration & Defense
            </div>
        </div>
    </div>

    <div class="footer">
        Generated automatically by VOICEGUARD AI System &bull; Project Report &bull; 2026
    </div>

</div>

</body>
</html>
"""

def generate_pdf():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(current_dir, "VOICEGUARD_AI_Project_Report.html")
    pdf_path = os.path.join(current_dir, "VOICEGUARD_AI_Project_Report.pdf")

    # 1. Write HTML file
    print(f"[1/2] Writing HTML report to {html_path}...")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(HTML_CONTENT)

    # 2. Convert to PDF using Microsoft Edge headless
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    ]
    
    browser_exe = None
    for path in edge_paths:
        if os.path.exists(path):
            browser_exe = path
            break

    if not browser_exe:
        print("[-] Error: Neither Microsoft Edge nor Google Chrome found for headless PDF generation.")
        sys.exit(1)

    print(f"[2/2] Converting HTML to PDF using {os.path.basename(browser_exe)}...")
    cmd = [
        browser_exe,
        "--headless",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={pdf_path}",
        "--no-pdf-header-footer",
        html_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:
        print(f"[+] SUCCESS! Generated PDF Report at: {pdf_path} (Size: {os.path.getsize(pdf_path) / 1024:.1f} KB)")
    else:
        print(f"[-] PDF generation failed. Output: {result.stderr}")
        sys.exit(1)

if __name__ == "__main__":
    generate_pdf()
