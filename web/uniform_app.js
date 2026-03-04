/**
 * YOLOv8 Uniform Detection – Frontend Logic
 * Handles camera access, uniform saving via camera scan, and live detection.
 */

const API_BASE = window.location.origin;

class UniformDetector {
    constructor() {
        // Camera
        this.stream = null;
        this.saveVideo = document.getElementById('saveVideo');
        this.saveOverlay = document.getElementById('saveOverlay');
        this.saveCtx = this.saveOverlay.getContext('2d');

        this.detectVideo = document.getElementById('detectVideo');
        this.detectOverlay = document.getElementById('detectOverlay');
        this.detectCtx = this.detectOverlay.getContext('2d');

        // State
        this.isDetecting = false;
        this.detectInterval = null;
        this.totalFrames = 0;
        this.totalCompliant = 0;
        this.totalViolations = 0;

        // UI Elements
        this.serverStatus = document.getElementById('serverStatus');
        this.cameraStatus = document.getElementById('cameraStatus');
        this.yoloStatus = document.getElementById('yoloStatus');
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.loadingText = document.getElementById('loadingText');

        this.initTabs();
        this.initButtons();
        this.init();
    }

    // ─── Init ────────────────────────────────────────────────────────────────

    async init() {
        try {
            this.loadingText.textContent = 'Checking API server...';
            await this.checkServer();
            this.serverStatus.classList.add('active');
            this.yoloStatus.classList.add('active');

            this.loadingText.textContent = 'Starting camera...';
            await this.setupCamera();
            this.cameraStatus.classList.add('active');

            this.loadingOverlay.classList.add('hidden');
            this.loadUniforms();
            this.showToast('System ready! YOLOv8 connected.', 'success');
        } catch (err) {
            console.error('Init error:', err);
            this.loadingText.textContent = `Error: ${err.message}`;
            this.showToast(err.message, 'error');
        }
    }

    async checkServer() {
        try {
            const res = await fetch(`${API_BASE}/api/uniforms`);
            if (!res.ok) throw new Error('Server not responding');
        } catch {
            throw new Error('Cannot connect to API server. Make sure uniform_api.py is running on port 5000.');
        }
    }

    async setupCamera() {
        this.stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480, facingMode: 'user' }
        });

        this.saveVideo.srcObject = this.stream;
        this.detectVideo.srcObject = this.stream;

        return new Promise(resolve => {
            this.saveVideo.onloadedmetadata = () => {
                this.saveVideo.play();
                this.saveOverlay.width = this.saveVideo.videoWidth;
                this.saveOverlay.height = this.saveVideo.videoHeight;
                resolve();
            };
            this.detectVideo.onloadedmetadata = () => {
                this.detectVideo.play();
                this.detectOverlay.width = this.detectVideo.videoWidth;
                this.detectOverlay.height = this.detectVideo.videoHeight;
            };
        });
    }

    // ─── Tabs ────────────────────────────────────────────────────────────────

    initTabs() {
        const tabs = document.querySelectorAll('.tab-btn');
        tabs.forEach(btn => {
            btn.addEventListener('click', () => {
                tabs.forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
            });
        });
    }

    // ─── Buttons ─────────────────────────────────────────────────────────────

    initButtons() {
        document.getElementById('scanBtn').addEventListener('click', () => this.scanAndSave());
        document.getElementById('startDetectBtn').addEventListener('click', () => this.toggleDetection());
        document.getElementById('resetStatsBtn').addEventListener('click', () => this.resetStats());
    }

    // ─── Capture Frame ───────────────────────────────────────────────────────

    captureFrame(video) {
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0);
        return canvas.toDataURL('image/jpeg', 0.85);
    }

    // ─── Save Uniform (Camera Scan) ──────────────────────────────────────────

    async scanAndSave() {
        const name = document.getElementById('uniformName').value.trim();
        const desc = document.getElementById('uniformDesc').value.trim();

        if (!name) {
            this.showToast('Please enter a uniform name.', 'error');
            return;
        }

        const scanBtn = document.getElementById('scanBtn');
        scanBtn.disabled = true;
        scanBtn.textContent = '⏳ Scanning...';

        // Flash effect
        const flash = document.getElementById('scanFlash');
        flash.classList.add('active');
        setTimeout(() => flash.classList.remove('active'), 300);

        const saveBadge = document.getElementById('saveBadge');
        saveBadge.textContent = '🔍 Detecting person with YOLOv8...';

        try {
            const frame = this.captureFrame(this.saveVideo);

            const res = await fetch(`${API_BASE}/api/uniforms`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, description: desc, frame })
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.error || 'Failed to save uniform');
            }

            this.showToast(data.message, 'success');
            saveBadge.textContent = `✅ Saved "${name}" successfully!`;
            document.getElementById('uniformName').value = '';
            document.getElementById('uniformDesc').value = '';
            this.loadUniforms();

            setTimeout(() => {
                saveBadge.textContent = '📸 Position yourself in frame';
            }, 3000);

        } catch (err) {
            console.error('Save error:', err);
            this.showToast(err.message, 'error');
            saveBadge.textContent = '❌ ' + err.message;
            setTimeout(() => {
                saveBadge.textContent = '📸 Position yourself in frame';
            }, 3000);
        } finally {
            scanBtn.disabled = false;
            scanBtn.textContent = '📸 Scan & Save Uniform';
        }
    }

    // ─── Load Uniforms Gallery ───────────────────────────────────────────────

    async loadUniforms() {
        try {
            const res = await fetch(`${API_BASE}/api/uniforms`);
            const data = await res.json();
            this.renderGallery(data.uniforms);
        } catch (err) {
            console.error('Load uniforms error:', err);
        }
    }

    renderGallery(uniforms) {
        const gallery = document.getElementById('uniformGallery');

        if (!uniforms || uniforms.length === 0) {
            gallery.innerHTML = `
                <div class="empty-state" style="grid-column: 1 / -1;">
                    <div class="icon">👕</div>
                    <p>No uniforms saved yet. Go to "Save Uniform" tab to scan one.</p>
                </div>
            `;
            return;
        }

        gallery.innerHTML = uniforms.map(u => {
            const colors = (u.dominant_colors || []).map(c => `
                <div class="color-dot" style="background: rgb(${c.r},${c.g},${c.b});">
                    <span class="tooltip">${c.percentage}%</span>
                </div>
            `).join('');

            const thumbUrl = `${API_BASE}/uniforms/${u.thumb_file}`;
            const createdDate = new Date(u.created_at).toLocaleDateString();

            return `
                <div class="uniform-card">
                    <img class="uniform-card-img" src="${thumbUrl}" alt="${u.name}" onerror="this.style.display='none'" />
                    <div class="uniform-card-body">
                        <h4>${u.name}</h4>
                        <p>${u.description || 'No description'} · ${createdDate}</p>
                        <div class="uniform-card-colors">${colors}</div>
                        <button class="btn btn-danger" style="width: 100%; justify-content: center; padding: 7px 14px; font-size: 0.8rem;" onclick="detector.deleteUniform('${u.id}', '${u.name}')">
                            🗑 Delete
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    // ─── Delete Uniform ──────────────────────────────────────────────────────

    async deleteUniform(id, name) {
        if (!confirm(`Delete uniform "${name}"?`)) return;

        try {
            const res = await fetch(`${API_BASE}/api/uniforms/${id}`, { method: 'DELETE' });
            const data = await res.json();

            if (!res.ok) throw new Error(data.error);

            this.showToast(data.message, 'success');
            this.loadUniforms();
        } catch (err) {
            this.showToast(err.message, 'error');
        }
    }

    // ─── Live Detection ──────────────────────────────────────────────────────

    toggleDetection() {
        if (this.isDetecting) {
            this.stopDetection();
        } else {
            this.startDetection();
        }
    }

    startDetection() {
        this.isDetecting = true;
        const btn = document.getElementById('startDetectBtn');
        btn.textContent = '⏹ Stop Detection';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-danger');

        document.getElementById('detectBadge').textContent = '🔍 Detecting...';
        this.runDetection();
    }

    stopDetection() {
        this.isDetecting = false;
        if (this.detectInterval) {
            clearTimeout(this.detectInterval);
            this.detectInterval = null;
        }
        const btn = document.getElementById('startDetectBtn');
        btn.textContent = '▶ Start Detection';
        btn.classList.remove('btn-danger');
        btn.classList.add('btn-success');

        document.getElementById('detectBadge').textContent = 'Stopped';
        this.detectCtx.clearRect(0, 0, this.detectOverlay.width, this.detectOverlay.height);
    }

    async runDetection() {
        if (!this.isDetecting) return;

        try {
            const frame = this.captureFrame(this.detectVideo);

            const res = await fetch(`${API_BASE}/api/detect`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ frame })
            });

            const data = await res.json();

            if (res.ok) {
                this.drawDetections(data.detections);
                this.updateDetectionUI(data);
            }
        } catch (err) {
            console.error('Detection error:', err);
        }

        // Run again after a short delay (control frame rate)
        this.detectInterval = setTimeout(() => this.runDetection(), 500);
    }

    drawDetections(detections) {
        const ctx = this.detectCtx;
        const canvas = this.detectOverlay;
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        detections.forEach(det => {
            const { x1, y1, x2, y2 } = det.box;
            const w = x2 - x1;
            const h = y2 - y1;

            // Box color based on compliance
            const color = det.is_compliant ? '#00ff88' : '#ff4466';
            ctx.strokeStyle = color;
            ctx.lineWidth = 3;
            ctx.strokeRect(x1, y1, w, h);

            // Background for label
            const label = det.uniform_match
                ? `${det.uniform_match.name} (${det.uniform_match.confidence}%)`
                : 'Unknown Uniform';

            ctx.font = 'bold 14px Inter, sans-serif';
            const textWidth = ctx.measureText(label).width;

            ctx.fillStyle = det.is_compliant ? 'rgba(0,255,136,0.85)' : 'rgba(255,68,102,0.85)';
            ctx.fillRect(x1, y1 - 28, textWidth + 16, 26);

            ctx.fillStyle = det.is_compliant ? '#000' : '#fff';
            ctx.fillText(label, x1 + 8, y1 - 10);

            // Person confidence badge
            ctx.fillStyle = 'rgba(0,0,0,0.6)';
            ctx.fillRect(x1, y2, 100, 22);
            ctx.fillStyle = '#1F3864';
            ctx.font = '12px Inter, sans-serif';
            ctx.fillText(`Person ${det.person_confidence}%`, x1 + 6, y2 + 15);

            // Draw clothing region indicator (torso area)
            const torsoY1 = y1 + h * 0.25;
            const torsoY2 = y1 + h * 0.70;
            const torsoX1 = x1 + w * 0.15;
            const torsoX2 = x2 - w * 0.15;
            ctx.strokeStyle = 'rgba(0,212,255,0.4)';
            ctx.lineWidth = 1;
            ctx.setLineDash([5, 5]);
            ctx.strokeRect(torsoX1, torsoY1, torsoX2 - torsoX1, torsoY2 - torsoY1);
            ctx.setLineDash([]);
        });
    }

    updateDetectionUI(data) {
        const dets = data.detections;
        this.totalFrames++;

        document.getElementById('personCount').textContent = data.total_persons;
        document.getElementById('totalFrames').textContent = this.totalFrames;

        if (dets.length > 0) {
            const primary = dets[0];

            if (primary.uniform_match) {
                document.getElementById('matchName').textContent = primary.uniform_match.name;
                document.getElementById('matchConf').textContent = primary.uniform_match.confidence + '%';
                document.getElementById('matchConf').className = 'info-value ok';
            } else {
                document.getElementById('matchName').textContent = 'No match';
                document.getElementById('matchConf').textContent = '--';
                document.getElementById('matchConf').className = 'info-value warn';
            }

            if (primary.is_compliant) {
                this.totalCompliant++;
                document.getElementById('complianceStatus').textContent = '✅ COMPLIANT';
                document.getElementById('complianceStatus').className = 'info-value ok';
                document.getElementById('detectBadge').textContent = '✅ Uniform Detected';
                document.getElementById('detectBadge').style.background = 'rgba(0,255,136,0.3)';
            } else {
                this.totalViolations++;
                document.getElementById('complianceStatus').textContent = '❌ VIOLATION';
                document.getElementById('complianceStatus').className = 'info-value warn';
                document.getElementById('detectBadge').textContent = '❌ Non-compliant uniform';
                document.getElementById('detectBadge').style.background = 'rgba(255,68,102,0.3)';
            }

            document.getElementById('totalCompliant').textContent = this.totalCompliant;
            document.getElementById('totalViolations').textContent = this.totalViolations;

            // Add to log
            this.addLogEntry(primary);
        } else {
            document.getElementById('matchName').textContent = '--';
            document.getElementById('matchConf').textContent = '--';
            document.getElementById('matchConf').className = 'info-value';
            document.getElementById('complianceStatus').textContent = 'No person';
            document.getElementById('complianceStatus').className = 'info-value';
            document.getElementById('detectBadge').textContent = '🔍 Detecting...';
            document.getElementById('detectBadge').style.background = 'rgba(0,0,0,0.65)';
        }
    }

    addLogEntry(detection) {
        const log = document.getElementById('detectLog');
        if (log.querySelector('.empty-state, p')) {
            log.innerHTML = '';
        }

        const time = new Date().toLocaleTimeString();
        const isOk = detection.is_compliant;
        const matchText = detection.uniform_match
            ? `${detection.uniform_match.name} (${detection.uniform_match.confidence}%)`
            : 'Unknown';

        const entry = document.createElement('div');
        entry.className = `detection-result ${isOk ? 'compliant' : 'violation'}`;
        entry.innerHTML = `
            <span class="badge ${isOk ? 'badge-ok' : 'badge-warn'}">${isOk ? 'OK' : 'VIOLATION'}</span>
            <span style="flex: 1; font-size: 0.82rem;">${matchText}</span>
            <span style="color: #5a6b85; font-size: 0.75rem;">${time}</span>
        `;

        log.insertBefore(entry, log.firstChild);

        while (log.children.length > 30) {
            log.removeChild(log.lastChild);
        }
    }

    resetStats() {
        this.totalFrames = 0;
        this.totalCompliant = 0;
        this.totalViolations = 0;
        document.getElementById('totalFrames').textContent = '0';
        document.getElementById('totalCompliant').textContent = '0';
        document.getElementById('totalViolations').textContent = '0';
        document.getElementById('detectLog').innerHTML = '<p style="color: #5a6b85; font-size: 0.82rem;">No detections yet</p>';
        this.showToast('Stats reset.', 'info');
    }

    // ─── Toast Notifications ─────────────────────────────────────────────────

    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            toast.style.transition = 'all 0.3s';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
}

// ─── Bootstrap ───────────────────────────────────────────────────────────────

const detector = new UniformDetector();
