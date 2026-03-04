const MODEL_URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.12/model/';
const UNIFORM_API = window.location.origin + '/api';

const UNNATURAL_HAIR_COLORS = [
    { name: 'Blonde/Light', h: [40, 60], s: [30, 100], l: [50, 85] },
    { name: 'Red/Orange', h: [0, 30], s: [50, 100], l: [30, 60] },
    { name: 'Purple', h: [270, 310], s: [30, 100], l: [20, 60] },
    { name: 'Blue', h: [200, 250], s: [40, 100], l: [20, 60] },
    { name: 'Green', h: [90, 150], s: [40, 100], l: [20, 60] },
    { name: 'Pink', h: [320, 360], s: [30, 100], l: [40, 70] }
];

class FaceDetector {
    constructor() {
        this.currentPage = 'dashboard';
        this.studentInfo = null;

        // Initialize UI elements
        this.initPageNavigation();
        this.initStudentForm();
        this.initDashboard();
        this.initDetectionPage();

        // Check for hash navigation
        const hash = window.location.hash.slice(1);
        const pageName = hash || 'dashboard';

        // Show initial page
        this.showPage(pageName);
        this.updateNavActive(pageName);

        // Listen for hash changes
        window.addEventListener('hashchange', () => {
            const newHash = window.location.hash.slice(1);
            if (newHash) {
                this.showPage(newHash);
                this.updateNavActive(newHash);
            }
        });
    }

    initPageNavigation() {
        // Page elements
        this.studentFormPage = document.getElementById('studentFormPage');
        this.dashboardPage = document.getElementById('dashboardPage');
        this.studentDetailPage = document.getElementById('studentDetailPage');
        this.methodSelectionPage = document.getElementById('methodSelectionPage');
        this.manualViolationPage = document.getElementById('manualViolationPage');
        this.detectionPage = document.getElementById('detectionPage');

        this.initMethodSelection();
        this.initManualViolationPage();
        this.initPrintViolations();
    }

    showPage(pageName) {
        this.currentPage = pageName;

        // Hide all pages
        this.studentFormPage.classList.remove('active');
        this.dashboardPage.classList.remove('active');
        this.studentDetailPage.classList.remove('active');
        this.methodSelectionPage.classList.remove('active');
        this.manualViolationPage.classList.remove('active');
        this.detectionPage.classList.remove('active');

        // Show selected page
        switch (pageName) {
            case 'studentForm':
                this.studentFormPage.classList.add('active');
                break;
            case 'dashboard':
                this.dashboardPage.classList.add('active');
                this.updateStudentInfoDisplay();
                this.loadDashboardData();
                break;
            case 'studentDetail':
                this.studentDetailPage.classList.add('active');
                this.loadStudentDetail();
                break;
            case 'methodSelection':
            case 'detectionMethodsPage':
                this.methodSelectionPage.classList.add('active');
                this.updateMethodSelectionDisplay();
                break;
            case 'manualViolation':
                this.manualViolationPage.classList.add('active');
                this.updateManualViolationDisplay();
                break;
            case 'detection':
                this.detectionPage.classList.add('active');
                this.updateStudentInfoDisplay();
                this.initDetection();
                break;
        }
    }

    updateNavActive(page) {
        // Update active state for navbar items
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => item.classList.remove('active'));

        switch (page) {
            case 'dashboard':
            case 'records':
                navItems.forEach(item => (item.textContent.includes('Records')) && item.classList.add('active'));
                break;
            case 'studentForm':
                navItems.forEach(item => (item.textContent.includes('Add Students')) && item.classList.add('active'));
                break;
            case 'detection':
            case 'methodSelection':
                navItems.forEach(item => (item.textContent.includes('Detection')) && item.classList.add('active'));
                break;
        }
    }

    initStudentForm() {
        this.studentForm = document.getElementById('studentForm');
        this.saveStudentBtn = document.getElementById('saveStudentBtn');
        this.studentHistorySelect = document.getElementById('studentHistorySelect');

        // Load student history
        this.loadStudentHistory();

        // Handle student selection from history
        this.studentHistorySelect.addEventListener('change', (e) => {
            if (e.target.value) {
                const studentData = JSON.parse(e.target.value);
                this.fillFormWithStudent(studentData);
            } else {
                this.clearForm();
            }
        });

        this.studentForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveStudentInfo();
        });

        // Real-time validation
        const inputs = this.studentForm.querySelectorAll('input, select');
        inputs.forEach(input => {
            input.addEventListener('input', () => this.validateForm());
            input.addEventListener('change', () => this.validateForm());
        });
    }

    loadStudentHistory() {
        const history = JSON.parse(localStorage.getItem('studentHistory') || '[]');
        this.studentHistorySelect.innerHTML = '<option value="">+ Add New Student</option>';

        history.forEach((student, index) => {
            const option = document.createElement('option');
            option.value = JSON.stringify(student);
            option.textContent = `${student.name} (${student.section})`;
            this.studentHistorySelect.appendChild(option);
        });
    }

    fillFormWithStudent(student) {
        document.getElementById('studentName').value = student.name;
        document.getElementById('studentSex').value = student.sex;
        document.getElementById('studentLrn').value = student.lrn;
        document.getElementById('studentGrade').value = student.grade;
        document.getElementById('studentSection').value = student.section;
        document.getElementById('studentPhone').value = student.phone || '';
        document.getElementById('studentEmail').value = student.email || '';
        document.getElementById('studentMotherName').value = student.mother_name || '';
        document.getElementById('studentMotherContact').value = student.mother_contact || '';
        document.getElementById('studentFatherName').value = student.father_name || '';
        document.getElementById('studentFatherContact').value = student.father_contact || '';
        this.validateForm();
    }

    clearForm() {
        this.studentForm.reset();
        this.validateForm();
    }

    validateForm() {
        const inputs = this.studentForm.querySelectorAll('input[required], select[required]');
        const allValid = Array.from(inputs).every(input => input.value.trim() !== '');
        this.saveStudentBtn.disabled = !allValid;
    }

    saveStudentInfo() {
        const formData = new FormData(this.studentForm);
        this.studentInfo = {
            name: formData.get('studentName').trim(),
            sex: formData.get('studentSex'),
            lrn: formData.get('studentLrn').trim(),
            grade: formData.get('studentGrade'),
            section: formData.get('studentSection').trim(),
            phone: formData.get('studentPhone')?.trim() || '',
            email: formData.get('studentEmail')?.trim() || '',
            mother_name: formData.get('studentMotherName')?.trim() || '',
            mother_contact: formData.get('studentMotherContact')?.trim() || '',
            father_name: formData.get('studentFatherName')?.trim() || '',
            father_contact: formData.get('studentFatherContact')?.trim() || ''
        };

        // Save to localStorage for persistence
        localStorage.setItem('studentInfo', JSON.stringify(this.studentInfo));

        // Add to student history
        this.addToStudentHistory(this.studentInfo);

        this.showPage('methodSelection');
    }

    async addToStudentHistory(student) {
        const history = JSON.parse(localStorage.getItem('studentHistory') || '[]');
        const now = new Date().toISOString();

        // Check if student already exists (by LRN or name)
        const existingIndex = history.findIndex(s => s.lrn === student.lrn || (s.name === student.name && s.section === student.section));

        if (existingIndex === -1) {
            // New student
            const newStudent = {
                ...student,
                first_log_date: now,
                last_log_date: now
            };
            history.push(newStudent);
        } else {
            // Existing student - update last log date
            history[existingIndex].last_log_date = now;
        }

        localStorage.setItem('studentHistory', JSON.stringify(history));
        this.loadStudentHistory();

        // Also save to Supabase students table
        try {
            if (window._supabase) {
                // Try to upsert: insert if new, update last_log_date if exists
                const { data: existing } = await window._supabase
                    .from('students')
                    .select('id')
                    .eq('lrn', student.lrn)
                    .single();

                if (existing) {
                    // Update existing student
                    await window._supabase
                        .from('students')
                        .update({ last_log_date: now })
                        .eq('lrn', student.lrn);
                } else {
                    // Insert new student
                    await window._supabase
                        .from('students')
                        .insert({
                            name: student.name,
                            lrn: student.lrn,
                            sex: student.sex,
                            grade: student.grade,
                            section: student.section,
                            phone: student.phone || '',
                            email: student.email || '',
                            mother_name: student.mother_name || '',
                            mother_contact: student.mother_contact || '',
                            father_name: student.father_name || '',
                            father_contact: student.father_contact || '',
                            first_log_date: now,
                            last_log_date: now
                        });
                }
            }
        } catch (err) {
            console.error('Supabase save error:', err);
        }
    }

    initDashboard() {
        this.dashboardProceedBtn = document.getElementById('dashboardProceedBtn');
        this.exportCsvBtn = document.getElementById('exportCsvBtn');
        this.addStudentBtn = document.getElementById('addStudentBtn');
        this.studentSearchInput = document.getElementById('studentSearchInput');

        this.dashboardProceedBtn.addEventListener('click', () => this.showPage('methodSelection'));
        this.exportCsvBtn.addEventListener('click', () => this.exportStudentsCSV());
        this.addStudentBtn.addEventListener('click', () => this.showPage('studentForm'));

        if (this.studentSearchInput) {
            this.studentSearchInput.addEventListener('input', (e) => this.searchStudents(e.target.value));
        }
    }

    initMethodSelection() {
        const methodCameraBtn = document.getElementById('methodCameraBtn');
        const methodUniformBtn = document.getElementById('methodUniformBtn');
        const methodManualBtn = document.getElementById('methodManualBtn');
        const methodBackBtn = document.getElementById('methodBackBtn');

        if (methodCameraBtn) {
            methodCameraBtn.addEventListener('click', () => {
                this.showPage('detection');
                setTimeout(() => this.startDetection(), 100);
            });
        }

        if (methodUniformBtn) {
            methodUniformBtn.addEventListener('click', () => {
                window.location.href = 'uniform.html';
            });
        }

        if (methodManualBtn) {
            methodManualBtn.addEventListener('click', () => {
                this.showPage('manualViolation');
            });
        }

        if (methodBackBtn) {
            methodBackBtn.addEventListener('click', () => {
                this.showPage('dashboard');
            });
        }
    }

    updateMethodSelectionDisplay() {
        if (this.studentInfo) {
            document.getElementById('methodStudentName').textContent = this.studentInfo.name;
        }
    }

    initManualViolationPage() {
        const manualViolationForm = document.getElementById('manualViolationForm');
        const manualBackBtn = document.getElementById('manualBackBtn');

        if (manualViolationForm) {
            manualViolationForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveManualViolation();
            });
        }

        if (manualBackBtn) {
            manualBackBtn.addEventListener('click', () => {
                this.showPage('methodSelection');
            });
        }
    }

    updateManualViolationDisplay() {
        if (this.studentInfo) {
            document.getElementById('manualStudentName').textContent = this.studentInfo.name;
        }
    }

    saveManualViolation() {
        const violation = document.getElementById('violationSelect').value;
        const description = document.getElementById('violationDescription').value.trim();
        const severity = document.querySelector('input[name="severity"]:checked')?.value;

        if (!violation || !description || !severity) {
            alert('Please fill in all fields');
            return;
        }

        // Create violation record and save directly to localStorage
        const violationRecord = {
            student_name: this.studentInfo.name,
            student_lrn: this.studentInfo.lrn,
            student_grade: this.studentInfo.grade,
            student_section: this.studentInfo.section,
            student_sex: this.studentInfo.sex,
            violations: [`${severity} - ${violation}: ${description}`],
            timestamp: new Date().toISOString(),
            method: 'manual'
        };

        const records = JSON.parse(localStorage.getItem('violationRecords') || '[]');
        records.push(violationRecord);
        localStorage.setItem('violationRecords', JSON.stringify(records));

        // Reset form
        document.getElementById('manualViolationForm').reset();

        // Show success message
        alert(`✓ Violation recorded for ${this.studentInfo.name}`);

        // Go straight to records
        this.showPage('dashboard');
        this.updateNavActive('dashboard');
    }

    updateStudentInfoDisplay() {
        if (!this.studentInfo) {
            // Load from localStorage if available
            const saved = localStorage.getItem('studentInfo');
            if (saved) {
                this.studentInfo = JSON.parse(saved);
            }
        }

        if (this.studentInfo) {
            document.getElementById('displayName').textContent = this.studentInfo.name;
            document.getElementById('displaySex').textContent = this.studentInfo.sex;
            document.getElementById('displayLrn').textContent = this.studentInfo.lrn;
            document.getElementById('displayGrade').textContent = this.studentInfo.grade;
            document.getElementById('displaySection').textContent = this.studentInfo.section;
        }
    }

    initDetectionPage() {
        this.backToDashboardBtn = document.getElementById('backToDashboardBtn');
        this.editStudentBtn = document.getElementById('editStudentBtn');
        this.proceedDashboardBtn = document.getElementById('proceedDashboardBtn');

        this.backToDashboardBtn.addEventListener('click', () => {
            this.stopDetection();
            this.showPage('dashboard');
        });
        this.editStudentBtn.addEventListener('click', () => {
            this.stopDetection();
            this.showPage('studentForm');
        });
        this.proceedDashboardBtn.addEventListener('click', () => {
            this.stopDetection();
            this.showPage('dashboard');
        });
    }

    initDetection() {
        // Initialize detection components only when needed
        if (!this.video) {
            this.video = document.getElementById('video');
            this.overlay = document.getElementById('overlay');
            this.ctx = this.overlay.getContext('2d');
            this.isRunning = false;
            this.lastFrameTime = 0;
            this.fps = 0;
            this.frameCount = 0;
            this.currentViolations = [];
            this.violationLogs = [];
            this.totalScans = 0;
            this.totalViolations = 0;
            this.savedUniforms = [];
            this.lastUniformResult = null;
            this.uniformCheckInterval = 0;
            this.apiAvailable = false;
            this.personCooldowns = new Map();
            this.autoCaptureCooldown = 30000;
            this.isSavingViolation = false;

            this.initDetectionUI();
            this.init();
        }
    }

    initDetectionUI() {
        this.loadingEl = document.getElementById('loading');
        this.loadingText = document.getElementById('loadingText');
        this.modelStatus = document.getElementById('modelStatus');
        this.cameraStatus = document.getElementById('cameraStatus');
        this.detectionStatus = document.getElementById('detectionStatus');
        this.modeIndicator = document.getElementById('modeIndicator');
        this.fpsCounter = document.getElementById('fpsCounter');
        this.violationAlert = document.getElementById('violationAlert');
        this.startBtn = document.getElementById('startBtn');
        this.captureBtn = document.getElementById('captureBtn');
        this.clearLogsBtn = document.getElementById('clearLogsBtn');

        this.faceCountEl = document.getElementById('faceCount');
        this.faceAngleEl = document.getElementById('faceAngle');
        this.hairModStatusEl = document.getElementById('hairModStatus');
        this.foreheadStatusEl = document.getElementById('foreheadStatus');
        this.uniformStatusEl = document.getElementById('uniformStatus');
        this.overallStatusEl = document.getElementById('overallStatus');
        this.violationListEl = document.getElementById('violationList');
        this.logPanelEl = document.getElementById('logPanel');

        this.totalScansEl = document.getElementById('totalScans');
        this.totalViolationsEl = document.getElementById('totalViolations');
        this.complianceRateEl = document.getElementById('complianceRate');

        this.startBtn.addEventListener('click', () => this.toggleDetection());
        this.captureBtn.addEventListener('click', () => this.logViolation());
        this.clearLogsBtn.addEventListener('click', () => this.clearLogs());
    }



    async init() {
        try {
            this.loadingText.textContent = 'Loading face detection models...';

            await faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL);
            this.loadingText.textContent = 'Loading landmark model...';
            await faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL);

            this.modelStatus.classList.add('active');
            this.loadingText.textContent = 'Starting camera...';

            await this.setupCamera();

            // Try to connect to uniform API
            this.loadingText.textContent = 'Connecting to uniform API...';
            await this.loadSavedUniforms();

            this.loadingEl.classList.add('hidden');
            this.startBtn.disabled = false;
            this.startDetection();

        } catch (error) {
            this.loadingText.textContent = `Error: Unable to initialize`;
        }
    }

    async loadSavedUniforms() {
        try {
            const res = await fetch(`${UNIFORM_API}/uniforms`);
            if (res.ok) {
                const data = await res.json();
                this.savedUniforms = data.uniforms || [];
                this.apiAvailable = true;
            }
        } catch (e) {
            this.apiAvailable = false;
        }
    }

    async setupCamera() {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480, facingMode: 'user' }
        });
        this.video.srcObject = stream;

        return new Promise((resolve) => {
            this.video.onloadedmetadata = () => {
                this.video.play();
                this.overlay.width = this.video.videoWidth;
                this.overlay.height = this.video.videoHeight;
                this.cameraStatus.classList.add('active');
                resolve();
            };
        });
    }

    toggleDetection() {
        if (this.isRunning) {
            this.stopDetection();
        } else {
            this.startDetection();
        }
    }

    startDetection() {
        this.isRunning = true;
        this.startBtn.textContent = 'Stop Detection';
        this.captureBtn.disabled = false;
        this.detectionStatus.classList.add('active');
        this.modeIndicator.textContent = 'Detecting...';
        this.detect();
    }

    stopDetection() {
        this.isRunning = false;
        this.startBtn.textContent = 'Start Detection';
        this.captureBtn.disabled = true;
        this.detectionStatus.classList.remove('active');
        this.modeIndicator.textContent = 'Stopped';
    }

    async detect() {
        if (!this.isRunning) return;

        const startTime = performance.now();

        try {
            const detections = await faceapi.detectAllFaces(
                this.video,
                new faceapi.TinyFaceDetectorOptions({ inputSize: 320, scoreThreshold: 0.3 })
            ).withFaceLandmarks();

            this.ctx.clearRect(0, 0, this.overlay.width, this.overlay.height);

            this.faceCountEl.textContent = detections.length;

            if (detections.length > 0) {
                // Run YOLOv8 API uniform check every ~15 frames
                this.uniformCheckInterval++;
                if (this.apiAvailable && this.savedUniforms.length > 0 && this.uniformCheckInterval >= 15) {
                    this.uniformCheckInterval = 0;
                    this.checkUniformViaAPI();
                }

                // Process EVERY detected face
                for (let i = 0; i < detections.length; i++) {
                    const detection = detections[i];
                    const landmarks = detection.landmarks;
                    const box = detection.detection.box;

                    this.drawDetection(box, landmarks);

                    const analysis = this.analyzeFace(landmarks, box);

                    // Show sidebar UI for the first face only
                    if (i === 0) {
                        this.updateUI(analysis);
                    }

                    this.totalScans++;
                    if (analysis.hasViolation) {
                        this.totalViolations++;
                        // Auto-capture this specific person with per-person cooldown
                        this.autoLogViolation(analysis.violations, box);
                    }
                }
                this.updateStats();
            } else {
                this.resetUI();
            }

        } catch (error) {
            // Detection error handled silently
        }

        const endTime = performance.now();
        this.frameCount++;

        if (this.frameCount % 10 === 0) {
            this.fps = Math.round(1000 / (endTime - startTime));
            this.fpsCounter.textContent = `FPS: ${this.fps}`;
        }
        this.lastFrameTime = endTime;

        // Reload saved uniforms every 200 frames
        if (this.frameCount % 200 === 0) {
            this.loadSavedUniforms();
        }

        // Clean up old person cooldowns every 500 frames
        if (this.frameCount % 500 === 0) {
            const now = Date.now();
            for (const [key, ts] of this.personCooldowns) {
                if (now - ts > this.autoCaptureCooldown * 2) this.personCooldowns.delete(key);
            }
        }

        requestAnimationFrame(() => this.detect());
    }

    async checkUniformViaAPI() {
        try {
            const canvas = document.createElement('canvas');
            canvas.width = this.video.videoWidth;
            canvas.height = this.video.videoHeight;
            canvas.getContext('2d').drawImage(this.video, 0, 0);
            const frame = canvas.toDataURL('image/jpeg', 0.7);

            const res = await fetch(`${UNIFORM_API}/detect`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ frame })
            });

            if (res.ok) {
                const data = await res.json();
                if (data.detections && data.detections.length > 0) {
                    this.lastUniformResult = data.detections[0];
                } else {
                    this.lastUniformResult = null;
                }
            }
        } catch (e) {
            // Silently fail — will use fallback color check
        }
    }

    drawDetection(box, landmarks) {
        this.ctx.strokeStyle = '#0A0980';
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(box.x, box.y, box.width, box.height);

        const leftEyebrow = landmarks.getLeftEyeBrow();
        const rightEyebrow = landmarks.getRightEyeBrow();
        const leftEye = landmarks.getLeftEye();
        const rightEye = landmarks.getRightEye();
        const nose = landmarks.getNose();
        const jaw = landmarks.getJawOutline();

        this.ctx.fillStyle = '#00ff88';
        [...leftEyebrow, ...rightEyebrow].forEach(pt => {
            this.ctx.beginPath();
            this.ctx.arc(pt.x, pt.y, 3, 0, Math.PI * 2);
            this.ctx.fill();
        });

        this.ctx.fillStyle = '#ffff00';
        [...leftEye, ...rightEye].forEach(pt => {
            this.ctx.beginPath();
            this.ctx.arc(pt.x, pt.y, 2, 0, Math.PI * 2);
            this.ctx.fill();
        });

        this.ctx.fillStyle = '#ff00ff';
        nose.forEach(pt => {
            this.ctx.beginPath();
            this.ctx.arc(pt.x, pt.y, 2, 0, Math.PI * 2);
            this.ctx.fill();
        });

        this.ctx.strokeStyle = 'rgba(83, 103, 148, 0.5)';
        this.ctx.beginPath();
        jaw.forEach((pt, i) => {
            if (i === 0) this.ctx.moveTo(pt.x, pt.y);
            else this.ctx.lineTo(pt.x, pt.y);
        });
        this.ctx.stroke();

        const hairRegionY = Math.max(0, box.y - 20);
        const hairRegionHeight = Math.min(40, box.y);
        if (hairRegionHeight > 5) {
            this.ctx.strokeStyle = 'rgba(255, 165, 0, 0.5)';
            this.ctx.setLineDash([5, 5]);
            this.ctx.strokeRect(box.x, hairRegionY, box.width, hairRegionHeight);
            this.ctx.setLineDash([]);
        }
    }

    analyzeFace(landmarks, box) {
        const violations = [];

        const leftEye = landmarks.getLeftEye();
        const rightEye = landmarks.getRightEye();
        const leftEyebrow = landmarks.getLeftEyeBrow();
        const rightEyebrow = landmarks.getRightEyeBrow();
        const nose = landmarks.getNose();
        const jaw = landmarks.getJawOutline();

        const leftEyeCenter = this.getCenter(leftEye);
        const rightEyeCenter = this.getCenter(rightEye);
        const noseTip = nose[3];

        const eyeDistance = Math.abs(rightEyeCenter.x - leftEyeCenter.x);
        const eyeMidX = (leftEyeCenter.x + rightEyeCenter.x) / 2;
        const noseOffset = noseTip.x - eyeMidX;
        const yawAngle = Math.atan2(noseOffset, eyeDistance) * (180 / Math.PI);

        let faceOrientation = 'Front';
        if (Math.abs(yawAngle) > 25) {
            faceOrientation = yawAngle > 0 ? 'Left Profile' : 'Right Profile';
        } else if (Math.abs(yawAngle) > 10) {
            faceOrientation = yawAngle > 0 ? 'Slight Left' : 'Slight Right';
        }

        const isFrontFacing = Math.abs(yawAngle) < 20;

        const leftEyebrowTop = Math.min(...leftEyebrow.map(p => p.y));
        const rightEyebrowTop = Math.min(...rightEyebrow.map(p => p.y));
        const eyebrowTop = Math.min(leftEyebrowTop, rightEyebrowTop);

        const foreheadY = box.y;
        const foreheadToEyebrow = eyebrowTop - foreheadY;

        const expectedForeheadHeight = eyeDistance * 0.6;
        const isFemale = this.studentInfo && this.studentInfo.sex === 'Female';

        // Forehead clear check only for males
        const foreheadClear = isFemale ? true : foreheadToEyebrow > expectedForeheadHeight * 0.3;
        const hasBangs = foreheadToEyebrow < expectedForeheadHeight * 0.15;

        // Allow bangs for female students - only flag for males
        // Very strict threshold: only flag when hair truly covers most of the forehead
        const significantBangs = !isFemale && foreheadToEyebrow < expectedForeheadHeight * 0.08;

        if (significantBangs) {
            violations.push('Bangs significantly covering eyebrows');
        }

        const hairColorAnalysis = this.analyzeHairColor(box);
        const hasHairModification = hairColorAnalysis.isUnnatural;

        if (hasHairModification) {
            violations.push(`Hair modification detected (${hairColorAnalysis.detectedColor})`);
        }

        // Earring detection — only flag for male students
        if (!isFemale && isFrontFacing) {
            const earringDetection = this.detectEarrings(jaw, box);
            if (earringDetection.detected) {
                violations.push(`Earring/accessory detected (${earringDetection.side})`);
            }
        }

        const uniformAnalysis = this.analyzeUniform(box, jaw);
        const uniformCompliant = uniformAnalysis.isCompliant;

        if (!uniformCompliant) {
            violations.push(uniformAnalysis.reason);
        }

        return {
            faceOrientation,
            yawAngle: yawAngle.toFixed(1),
            isFrontFacing,
            foreheadClear,
            isFemale,
            hasBangs,
            hasHairModification,
            hairColorInfo: hairColorAnalysis,
            uniformCompliant,
            uniformInfo: uniformAnalysis,
            violations,
            hasViolation: violations.length > 0
        };
    }

    analyzeHairColor(box) {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = this.video.videoWidth;
        canvas.height = this.video.videoHeight;
        ctx.drawImage(this.video, 0, 0);

        const hairY = Math.max(0, box.y - 30);
        const hairHeight = Math.min(40, box.y);
        const hairX = box.x + box.width * 0.2;
        const hairWidth = box.width * 0.6;

        if (hairHeight < 10) {
            return { isUnnatural: false, detectedColor: 'Unknown' };
        }

        try {
            const imageData = ctx.getImageData(hairX, hairY, hairWidth, hairHeight);
            const pixels = imageData.data;

            let totalH = 0, totalS = 0, totalL = 0;
            let pixelCount = 0;

            for (let i = 0; i < pixels.length; i += 4) {
                const r = pixels[i];
                const g = pixels[i + 1];
                const b = pixels[i + 2];

                const hsl = this.rgbToHsl(r, g, b);
                totalH += hsl.h;
                totalS += hsl.s;
                totalL += hsl.l;
                pixelCount++;
            }

            const avgH = totalH / pixelCount;
            const avgS = totalS / pixelCount;
            const avgL = totalL / pixelCount;

            for (const color of UNNATURAL_HAIR_COLORS) {
                const hInRange = (avgH >= color.h[0] && avgH <= color.h[1]) ||
                    (color.h[0] > color.h[1] && (avgH >= color.h[0] || avgH <= color.h[1]));
                const sInRange = avgS >= color.s[0] && avgS <= color.s[1];
                const lInRange = avgL >= color.l[0] && avgL <= color.l[1];

                if (hInRange && sInRange && lInRange) {
                    return { isUnnatural: true, detectedColor: color.name, h: avgH, s: avgS, l: avgL };
                }
            }

            return { isUnnatural: false, detectedColor: 'Natural', h: avgH, s: avgS, l: avgL };
        } catch (e) {
            return { isUnnatural: false, detectedColor: 'Unknown' };
        }
    }

    // Detect earrings by analyzing earlobe regions for metallic/shiny highlights
    detectEarrings(jaw, box) {
        try {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            canvas.width = this.video.videoWidth;
            canvas.height = this.video.videoHeight;
            ctx.drawImage(this.video, 0, 0);

            // Jaw outline: points 0-1 are near the left ear, points 15-16 near the right ear
            const leftEarPoint = jaw[0];
            const rightEarPoint = jaw[16] || jaw[jaw.length - 1];

            let leftDetected = false;
            let rightDetected = false;

            // Check both ear regions
            const earRegions = [
                { point: leftEarPoint, name: 'left' },
                { point: rightEarPoint, name: 'right' }
            ];

            for (const ear of earRegions) {
                // Sample area below and slightly outside the earlobe
                const sampleX = Math.max(0, Math.round(ear.point.x) - (ear.name === 'left' ? 15 : -5));
                const sampleY = Math.round(ear.point.y);
                const sampleW = 20;
                const sampleH = 25;

                if (sampleX < 0 || sampleY < 0 ||
                    sampleX + sampleW > canvas.width ||
                    sampleY + sampleH > canvas.height) continue;

                const imageData = ctx.getImageData(sampleX, sampleY, sampleW, sampleH);
                const pixels = imageData.data;

                let brightPixels = 0;
                let metallicPixels = 0;
                let totalPixels = 0;
                let totalR = 0, totalG = 0, totalB = 0;

                for (let i = 0; i < pixels.length; i += 4) {
                    const r = pixels[i], g = pixels[i + 1], b = pixels[i + 2];
                    totalR += r; totalG += g; totalB += b;
                    totalPixels++;

                    const luminance = 0.299 * r + 0.587 * g + 0.114 * b;
                    const max = Math.max(r, g, b);
                    const min = Math.min(r, g, b);
                    const saturation = max > 0 ? (max - min) / max : 0;

                    // Metallic/shiny detection: very bright spots or high-saturation colored spots
                    if (luminance > 200 && (max - min) < 40) {
                        brightPixels++; // White/silver shine
                    }
                    if (saturation > 0.5 && luminance > 100 && luminance < 220) {
                        metallicPixels++; // Colored metal (gold, colored studs)
                    }
                }

                if (totalPixels === 0) continue;

                // Also get skin reference from cheek area (middle of jaw)
                const cheekPoint = jaw[Math.floor(jaw.length / 2)];
                const cheekX = Math.max(0, Math.round(cheekPoint.x) - 10);
                const cheekY = Math.max(0, Math.round(cheekPoint.y) - 15);

                let skinR = 180, skinG = 150, skinB = 130; // Default skin tone fallback
                if (cheekX + 20 <= canvas.width && cheekY + 20 <= canvas.height) {
                    const skinData = ctx.getImageData(cheekX, cheekY, 20, 20);
                    const sp = skinData.data;
                    let sTotal = 0;
                    skinR = 0; skinG = 0; skinB = 0;
                    for (let i = 0; i < sp.length; i += 4) {
                        skinR += sp[i]; skinG += sp[i + 1]; skinB += sp[i + 2];
                        sTotal++;
                    }
                    skinR /= sTotal; skinG /= sTotal; skinB /= sTotal;
                }

                const avgR = totalR / totalPixels;
                const avgG = totalG / totalPixels;
                const avgB = totalB / totalPixels;

                // Color distance from skin
                const skinDist = Math.sqrt(
                    Math.pow(avgR - skinR, 2) +
                    Math.pow(avgG - skinG, 2) +
                    Math.pow(avgB - skinB, 2)
                );

                const brightRatio = brightPixels / totalPixels;
                const metallicRatio = metallicPixels / totalPixels;

                // Flag only if very strong bright/metallic signal — raised thresholds to reduce false positives
                if ((brightRatio > 0.35 && metallicRatio > 0.1) || metallicRatio > 0.25 || (skinDist > 120 && brightRatio > 0.2 && metallicRatio > 0.15)) {
                    if (ear.name === 'left') leftDetected = true;
                    else rightDetected = true;
                }
            }

            if (leftDetected && rightDetected) {
                return { detected: true, side: 'both ears' };
            } else if (leftDetected) {
                return { detected: true, side: 'left ear' };
            } else if (rightDetected) {
                return { detected: true, side: 'right ear' };
            }

            return { detected: false, side: '' };
        } catch (e) {
            return { detected: false, side: '' };
        }
    }

    analyzeUniform(faceBox, jaw) {
        // Use the cached YOLOv8 API result from periodic frame detection
        if (this.lastUniformResult) {
            const result = this.lastUniformResult;
            if (result.uniform_match && result.is_compliant) {
                return {
                    isCompliant: true,
                    reason: `✅ ${result.uniform_match.name} (${result.uniform_match.confidence}% match)`,
                    source: 'yolov8'
                };
            } else if (result.uniform_match) {
                return {
                    isCompliant: false,
                    reason: `Low match: ${result.uniform_match.name} (${result.uniform_match.confidence}%)`,
                    source: 'yolov8'
                };
            } else {
                return {
                    isCompliant: false,
                    reason: 'No matching uniform found',
                    source: 'yolov8'
                };
            }
        }

        // Fallback: Basic color-based uniform detection when no API result or saved uniforms
        return this.analyzeUniformColorBasic(faceBox, jaw);
    }

    analyzeUniformColorBasic(faceBox, jaw) {
        try {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            canvas.width = this.video.videoWidth;
            canvas.height = this.video.videoHeight;
            ctx.drawImage(this.video, 0, 0);

            // Sample uniform area (below face, above waist level)
            const uniformY = faceBox.y + faceBox.height;
            const uniformHeight = Math.min(faceBox.height * 1.5, this.video.videoHeight - uniformY);
            const uniformX = faceBox.x;
            const uniformWidth = faceBox.width;

            if (uniformHeight < 20) {
                return { isCompliant: true, reason: 'Uniform area too small to analyze' };
            }

            const imageData = ctx.getImageData(uniformX, uniformY, uniformWidth, uniformHeight);
            const pixels = imageData.data;

            let totalR = 0, totalG = 0, totalB = 0;
            let pixelCount = 0;

            // Sample pixels in a grid pattern for performance
            for (let y = 0; y < uniformHeight; y += 5) {
                for (let x = 0; x < uniformWidth; x += 5) {
                    const index = (y * uniformWidth + x) * 4;
                    if (index < pixels.length - 2) {
                        totalR += pixels[index];
                        totalG += pixels[index + 1];
                        totalB += pixels[index + 2];
                        pixelCount++;
                    }
                }
            }

            if (pixelCount === 0) {
                return { isCompliant: true, reason: 'No uniform pixels sampled' };
            }

            const avgR = totalR / pixelCount;
            const avgG = totalG / pixelCount;
            const avgB = totalB / pixelCount;

            // Basic uniform color checks (common school uniform colors)
            const isWhite = avgR > 200 && avgG > 200 && avgB > 200;
            const isLightBlue = avgB > avgR && avgB > avgG && avgB > 150;
            const isDarkBlue = avgB > 100 && avgR < 80 && avgG < 80;
            const isGray = Math.abs(avgR - avgG) < 20 && Math.abs(avgG - avgB) < 20 && avgR > 100 && avgR < 180;
            const isBlack = avgR < 50 && avgG < 50 && avgB < 50;

            if (isWhite || isLightBlue || isDarkBlue || isGray || isBlack) {
                return { isCompliant: true, reason: 'Standard uniform color detected' };
            } else {
                // Check for bright or unnatural colors that might indicate non-uniform clothing
                const isBright = (avgR + avgG + avgB) / 3 > 180;
                const isColorful = Math.max(avgR, avgG, avgB) - Math.min(avgR, avgG, avgB) > 100;

                if (isBright || isColorful) {
                    return { isCompliant: false, reason: 'Non-uniform colors detected' };
                } else {
                    return { isCompliant: true, reason: 'Neutral colors (checking further)' };
                }
            }
        } catch (e) {
            return { isCompliant: true, reason: 'Analysis unavailable' };
        }
    }



    colorDistance(r1, g1, b1, r2, g2, b2) {
        return Math.sqrt(Math.pow(r1 - r2, 2) + Math.pow(g1 - g2, 2) + Math.pow(b1 - b2, 2));
    }

    rgbToHsl(r, g, b) {
        r /= 255; g /= 255; b /= 255;
        const max = Math.max(r, g, b), min = Math.min(r, g, b);
        let h, s, l = (max + min) / 2;

        if (max === min) {
            h = s = 0;
        } else {
            const d = max - min;
            s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
            switch (max) {
                case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
                case g: h = ((b - r) / d + 2) / 6; break;
                case b: h = ((r - g) / d + 4) / 6; break;
            }
        }

        return { h: h * 360, s: s * 100, l: l * 100 };
    }

    getCenter(points) {
        const sumX = points.reduce((sum, p) => sum + p.x, 0);
        const sumY = points.reduce((sum, p) => sum + p.y, 0);
        return { x: sumX / points.length, y: sumY / points.length };
    }

    updateStats() {
        this.totalScansEl.textContent = this.totalScans;
        this.totalViolationsEl.textContent = this.totalViolations;

        if (this.totalScans > 0) {
            const compliance = ((this.totalScans - this.totalViolations) / this.totalScans * 100).toFixed(0);
            this.complianceRateEl.textContent = compliance + '%';
        }
    }

    updateUI(analysis) {
        this.faceAngleEl.textContent = `${analysis.faceOrientation} (${analysis.yawAngle}°)`;

        this.hairModStatusEl.textContent = analysis.hasHairModification ? 'Modified' : 'Natural';
        this.hairModStatusEl.className = `info-value ${analysis.hasHairModification ? 'violation' : 'ok'}`;

        // Only show forehead clear check for male students
        if (!analysis.isFemale) {
            this.foreheadStatusEl.textContent = analysis.foreheadClear ? 'Yes' : 'No';
            this.foreheadStatusEl.className = `info-value ${analysis.foreheadClear ? 'ok' : 'violation'}`;
            this.foreheadStatusEl.parentElement.style.display = '';
        } else {
            this.foreheadStatusEl.parentElement.style.display = 'none';
        }

        this.uniformStatusEl.textContent = analysis.uniformCompliant ? 'Compliant' : 'Violation';
        this.uniformStatusEl.className = `info-value ${analysis.uniformCompliant ? 'ok' : 'violation'}`;

        if (analysis.hasViolation) {
            this.overallStatusEl.textContent = 'VIOLATION';
            this.overallStatusEl.className = 'info-value violation';
            this.violationAlert.classList.add('show');
            this.modeIndicator.textContent = 'VIOLATION DETECTED';
            this.modeIndicator.style.background = 'rgba(255, 68, 68, 0.8)';
        } else {
            this.overallStatusEl.textContent = 'COMPLIANT';
            this.overallStatusEl.className = 'info-value ok';
            this.violationAlert.classList.remove('show');
            this.modeIndicator.textContent = analysis.faceOrientation + ' Face';
            this.modeIndicator.style.background = 'rgba(0, 0, 0, 0.7)';
        }

        const logBtn = document.getElementById('logViolationBtn');
        if (analysis.violations.length > 0) {
            this.violationListEl.innerHTML = analysis.violations.map(v =>
                `<div class="violation-item">${v}</div>`
            ).join('');
            this.currentViolations = analysis.violations;
            if (logBtn) logBtn.disabled = false;
        } else {
            this.violationListEl.innerHTML = '<p style="color: #888; font-size: 0.9rem;">No violations detected</p>';
            this.currentViolations = [];
            if (logBtn) logBtn.disabled = true;
        }
    }

    resetUI() {
        this.faceAngleEl.textContent = '--';
        this.hairModStatusEl.textContent = '--';
        this.hairModStatusEl.className = 'info-value';
        this.foreheadStatusEl.textContent = '--';
        this.foreheadStatusEl.className = 'info-value';
        this.uniformStatusEl.textContent = '--';
        this.uniformStatusEl.className = 'info-value';
        this.overallStatusEl.textContent = '--';
        this.overallStatusEl.className = 'info-value';
        this.violationAlert.classList.remove('show');
        this.modeIndicator.textContent = 'No face detected';
        this.modeIndicator.style.background = 'rgba(0, 0, 0, 0.7)';
        this.violationListEl.innerHTML = '<p style="color: #888; font-size: 0.9rem;">No face in frame</p>';
    }

    // Auto-capture violation with per-person 30s cooldown
    // Uses face position zone as a person identifier
    async autoLogViolation(violations, faceBox) {
        if (!violations || violations.length === 0) return;

        // Create a zone key from face position (bucketed to nearest 80px to handle movement)
        const zoneX = Math.round(faceBox.x / 80);
        const zoneY = Math.round(faceBox.y / 80);
        const personKey = `${zoneX}_${zoneY}`;

        const now = Date.now();
        const lastCapture = this.personCooldowns.get(personKey) || 0;
        if (now - lastCapture < this.autoCaptureCooldown) return;

        // Mark this person's cooldown immediately
        this.personCooldowns.set(personKey, now);

        try {
            const canvas = document.createElement('canvas');
            canvas.width = this.video.videoWidth;
            canvas.height = this.video.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(this.video, 0, 0);
            ctx.drawImage(this.overlay, 0, 0);
            const frame = canvas.toDataURL('image/jpeg', 0.85);

            const res = await fetch(`${UNIFORM_API}/violation-log`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    frame,
                    violations,
                    studentInfo: this.studentInfo || { name: 'Unknown', id: 'Unknown', class: 'Unknown', gender: 'Unknown', section: 'Unknown' }
                })
            });

            try {
                const data = await res.json();
                this.addLog(`📸 Auto-saved: ${data.filename}`, true);
                this.saveViolationRecord(violations);
            } catch (e) {
                // Violation logging failed silently
            }
        } catch (e) {
            // Violation logging failed silently
        }
    }

    // Manual "Log Violation" button — also sends to API
    logViolation() {
        const canvas = document.createElement('canvas');
        canvas.width = this.video.videoWidth;
        canvas.height = this.video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(this.video, 0, 0);
        ctx.drawImage(this.overlay, 0, 0);
        const frame = canvas.toDataURL('image/jpeg', 0.85);

        (async () => {
            const res = await fetch(`${UNIFORM_API}/violation-log`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    frame,
                    violations: this.currentViolations || [],
                    studentInfo: this.studentInfo
                })
            });

            if (res.ok) {
                const data = await res.json();
                this.addLog(`📸 Manual log saved: ${data.filename}`, true);
            }
        })();

        const logEntry = {
            id: Date.now(),
            timestamp: new Date().toISOString(),
            timeStr: new Date().toLocaleTimeString(),
            dateStr: new Date().toLocaleDateString(),
            violations: this.currentViolations || [],
        };
        this.violationLogs.unshift(logEntry);
        if (this.violationLogs.length > 50) this.violationLogs.pop();
        this.updateLogPanel();
        const violationMsg = (this.currentViolations && this.currentViolations.length > 0)
            ? `Logged: ${this.currentViolations.join(', ')}`
            : 'No violations - logged with clean record';
        this.addLog(violationMsg, true);
    }

    logAndSaveViolation() {
        if (!this.currentViolations || this.currentViolations.length === 0) return;

        // Save to violation records in localStorage
        const record = {
            student_name: this.studentInfo ? this.studentInfo.name : 'Unknown',
            student_lrn: this.studentInfo ? this.studentInfo.lrn : 'Unknown',
            student_grade: this.studentInfo ? this.studentInfo.grade : 'Unknown',
            student_section: this.studentInfo ? this.studentInfo.section : 'Unknown',
            student_sex: this.studentInfo ? this.studentInfo.sex : 'Unknown',
            violations: [...this.currentViolations],
            timestamp: new Date().toISOString(),
            method: 'camera'
        };

        const records = JSON.parse(localStorage.getItem('violationRecords') || '[]');
        records.push(record);
        localStorage.setItem('violationRecords', JSON.stringify(records));

        // Also call the existing logViolation for API + log panel
        this.logViolation();

        // Visual feedback on the button
        const btn = document.getElementById('logViolationBtn');
        if (btn) {
            btn.textContent = '✓ Violation Logged!';
            btn.style.background = 'linear-gradient(135deg, #28a745, #20c997)';
            btn.style.pointerEvents = 'none';
            setTimeout(() => {
                if (btn) {
                    btn.textContent = '📋 Log Violation';
                    btn.style.background = 'linear-gradient(135deg, #ff4466, #ff2244)';
                    btn.style.pointerEvents = 'auto';
                }
            }, 2000);
        }

        this.addLog(`📋 Violation logged for ${record.student_name}: ${this.currentViolations.join(', ')}`, true);
    }

    addLog(message, isViolation = false) {
        const timestamp = new Date().toLocaleTimeString();
        const logItem = document.createElement('div');
        logItem.className = `log-item ${isViolation ? 'violation-log' : ''}`;
        logItem.innerHTML = `
            <div class="log-time">${timestamp}</div>
            <div class="log-text">${message}</div>
        `;

        if (this.logPanelEl.querySelector('p')) {
            this.logPanelEl.innerHTML = '';
        }

        this.logPanelEl.insertBefore(logItem, this.logPanelEl.firstChild);

        while (this.logPanelEl.children.length > 20) {
            this.logPanelEl.removeChild(this.logPanelEl.lastChild);
        }
    }

    updateLogPanel() {
        if (this.violationLogs.length === 0) {
            this.logPanelEl.innerHTML = '<p style="color: #888; font-size: 0.85rem;">No logs yet</p>';
            return;
        }
    }

    clearLogs() {
        this.violationLogs = [];
        this.totalScans = 0;
        this.totalViolations = 0;
        this.logPanelEl.innerHTML = '<p style="color: #888; font-size: 0.85rem;">No logs yet</p>';
        this.updateStats();
        this.addLog('Logs cleared');
    }



    loadDashboardData() {
        const history = JSON.parse(localStorage.getItem('studentHistory') || '[]');
        history.sort(function (a, b) { return a.name.localeCompare(b.name); });
        const violations = JSON.parse(localStorage.getItem('violationRecords') || '[]');
        const dashboardTotalStudents = document.getElementById('dashboardTotalStudents');
        const dashboardTotalViolations = document.getElementById('dashboardTotalViolations');
        const studentListTable = document.getElementById('studentListTable');

        if (dashboardTotalStudents) {
            dashboardTotalStudents.textContent = history.length;
        }

        if (dashboardTotalViolations) {
            dashboardTotalViolations.textContent = violations.length;
        }

        if (studentListTable) {
            if (history.length > 0) {
                studentListTable.innerHTML = `
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: rgba(10, 9, 128, 0.1); border-bottom: 2px solid rgba(83, 103, 148, 0.3);">
                                <th style="padding: 10px; text-align: left; color: #0A0980; font-size: 0.85rem;">ID</th>
                                <th style="padding: 10px; text-align: left; color: #0A0980; font-size: 0.85rem;">Name</th>
                                <th style="padding: 10px; text-align: left; color: #0A0980; font-size: 0.85rem;">LRN</th>
                                <th style="padding: 10px; text-align: left; color: #0A0980; font-size: 0.85rem;">Grade</th>
                                <th style="padding: 10px; text-align: left; color: #0A0980; font-size: 0.85rem;">Section</th>
                                <th style="padding: 10px; text-align: left; color: #0A0980; font-size: 0.85rem;">Gender</th>
                                <th style="padding: 10px; text-align: left; color: #0A0980; font-size: 0.85rem;">First Log</th>
                                <th style="padding: 10px; text-align: left; color: #0A0980; font-size: 0.85rem;">Last Log</th>
                                <th style="padding: 10px; text-align: left; color: #0A0980; font-size: 0.85rem;">Phone</th>
                                <th style="padding: 10px; text-align: left; color: #0A0980; font-size: 0.85rem;">Email</th>
                                <th style="padding: 10px; text-align: center; color: #FFD361; font-size: 0.85rem;">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${history.map((student, idx) => {
                    const firstLog = student.first_log_date ? new Date(student.first_log_date).toLocaleDateString() : 'N/A';
                    const lastLog = student.last_log_date ? new Date(student.last_log_date).toLocaleDateString() : 'N/A';
                    return `
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.1);" class="student-row" data-name="${student.name.toLowerCase()}" data-lrn="${student.lrn}" data-student="${JSON.stringify(student).replace(/"/g, '&quot;')}">
                                        <td style="padding: 10px; color: #888; font-size: 0.9rem;">${idx + 1}</td>
                                        <td style="padding: 10px; font-size: 0.9rem; cursor: pointer; color: #0A0980; text-decoration: underline;" class="student-name-link">${student.name}</td>
                                        <td style="padding: 10px; color: #0A0980; font-size: 0.9rem;">${student.lrn}</td>
                                        <td style="padding: 10px; font-size: 0.9rem;">${student.grade}</td>
                                        <td style="padding: 10px; font-size: 0.9rem;">${student.section}</td>
                                        <td style="padding: 10px; color: ${student.sex === 'Male' ? '#00ff88' : '#ff6fd8'}; font-size: 0.9rem;">${student.sex}</td>
                                        <td style="padding: 10px; color: #888; font-size: 0.85rem;">${firstLog}</td>
                                        <td style="padding: 10px; color: #888; font-size: 0.85rem;">${lastLog}</td>
                                        <td style="padding: 10px; font-size: 0.9rem;">${student.phone || 'N/A'}</td>
                                        <td style="padding: 10px; font-size: 0.9rem;">${student.email || 'N/A'}</td>
                                        <td style="padding: 10px; text-align: center;">
                                            <button class="delete-student-btn" data-lrn="${student.lrn}" style="background: linear-gradient(135deg, #ff4466, #ff2244); border: none; color: #fff; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 600; transition: all 0.3s;">🗑️ Delete</button>
                                        </td>
                                    </tr>
                                `;
                }).join('')}
                        </tbody>
                    </table>
                `;
            } else {
                studentListTable.innerHTML = '<p style="color: #888;">No students recorded yet</p>';
            }

            // Add click handlers to student names
            const studentNameLinks = studentListTable.querySelectorAll('.student-name-link');
            studentNameLinks.forEach(link => {
                link.addEventListener('click', (e) => {
                    const row = e.target.closest('tr');
                    const studentData = JSON.parse(row.getAttribute('data-student').replace(/&quot;/g, '"'));
                    this.selectedStudentForDetail = studentData;
                    this.showPage('studentDetail');
                });
            });

            // Add delete handlers to delete buttons
            const deleteButtons = studentListTable.querySelectorAll('.delete-student-btn');
            deleteButtons.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const lrn = btn.getAttribute('data-lrn');
                    if (confirm('Are you sure you want to delete this student? All their violation records will also be deleted.')) {
                        this.deleteStudent(lrn);
                    }
                });
                // Add hover effect
                btn.addEventListener('mouseover', () => {
                    btn.style.background = 'linear-gradient(135deg, #ff6b7b, #ff4455)';
                    btn.style.transform = 'scale(1.05)';
                });
                btn.addEventListener('mouseout', () => {
                    btn.style.background = 'linear-gradient(135deg, #ff4466, #ff2244)';
                    btn.style.transform = 'scale(1)';
                });
            });
        }
    }

    deleteStudent(lrn) {
        // Remove from history
        let history = JSON.parse(localStorage.getItem('studentHistory') || '[]');
        history = history.filter(s => s.lrn !== lrn);
        localStorage.setItem('studentHistory', JSON.stringify(history));

        // Remove all violations for this student
        let violations = JSON.parse(localStorage.getItem('violationRecords') || '[]');
        violations = violations.filter(v => v.student_lrn !== lrn);
        localStorage.setItem('violationRecords', JSON.stringify(violations));

        // Reload dashboard
        this.loadDashboardData();
    }

    deleteViolation(studentLrn, timestamp) {
        // Remove the specific violation record
        let violations = JSON.parse(localStorage.getItem('violationRecords') || '[]');
        violations = violations.filter(v => !(v.student_lrn === studentLrn && v.timestamp === timestamp));
        localStorage.setItem('violationRecords', JSON.stringify(violations));

        // Reload the student detail page
        this.loadStudentDetail();
    }

    searchStudents(query) {
        const rows = document.querySelectorAll('.student-row');
        rows.forEach(row => {
            const name = row.getAttribute('data-name');
            if (name.includes(query.toLowerCase())) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    exportStudentsCSV() {
        const history = JSON.parse(localStorage.getItem('studentHistory') || '[]');

        if (history.length === 0) {
            alert('No students to export');
            return;
        }

        let csv = 'Student ID,Name,LRN,Grade,Section,Gender\n';
        history.forEach((student, idx) => {
            csv += `${idx + 1},"${student.name}","${student.lrn}","${student.grade}","${student.section}","${student.sex}"\n`;
        });

        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `students_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }

    saveViolationRecord(violations) {
        const record = {
            student_name: this.studentInfo ? this.studentInfo.name : 'Unknown',
            student_lrn: this.studentInfo ? this.studentInfo.lrn : 'Unknown',
            student_grade: this.studentInfo ? this.studentInfo.grade : 'Unknown',
            student_section: this.studentInfo ? this.studentInfo.section : 'Unknown',
            student_sex: this.studentInfo ? this.studentInfo.sex : 'Unknown',
            violations: violations || [],
            timestamp: new Date().toISOString()
        };

        const records = JSON.parse(localStorage.getItem('violationRecords') || '[]');
        records.push(record);
        localStorage.setItem('violationRecords', JSON.stringify(records));
    }

    loadStudentDetail() {
        if (!this.selectedStudentForDetail) {
            this.showPage('dashboard');
            return;
        }

        const student = this.selectedStudentForDetail;
        const violations = JSON.parse(localStorage.getItem('violationRecords') || '[]');
        const studentViolations = violations.filter(v => v.student_lrn === student.lrn);

        // Update student info display
        document.getElementById('detailStudentName').textContent = student.name;
        document.getElementById('detailStudentLrn').textContent = student.lrn;
        document.getElementById('detailStudentGrade').textContent = student.grade;
        document.getElementById('detailStudentSection').textContent = student.section;
        document.getElementById('detailStudentPhone').textContent = student.phone || 'N/A';
        document.getElementById('detailStudentEmail').textContent = student.email || 'N/A';
        document.getElementById('detailStudentMotherName').textContent = student.mother_name || 'N/A';
        document.getElementById('detailStudentMotherContact').textContent = student.mother_contact || 'N/A';
        document.getElementById('detailStudentFatherName').textContent = student.father_name || 'N/A';
        document.getElementById('detailStudentFatherContact').textContent = student.father_contact || 'N/A';

        // Display violations
        const violationsList = document.getElementById('studentViolationsList');
        if (studentViolations.length === 0) {
            violationsList.innerHTML = '<p style="color: #888;">No violations recorded</p>';
        } else {
            violationsList.innerHTML = studentViolations.map((violation, idx) => {
                const violationText = violation.violations && violation.violations.length > 0
                    ? violation.violations.join(' • ')
                    : 'Clean record - no violations';
                return `
                    <div style="background: rgba(255, 68, 68, 0.08); border-left: 3px solid #ff4466; padding: 12px; margin-bottom: 8px; border-radius: 0 8px 8px 0; display: flex; justify-content: space-between; align-items: center;">
                        <div style="flex: 1;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <span style="color: #ff6fd8; font-weight: 600; font-size: 0.9rem;">Record #${idx + 1}</span>
                                <span style="color: #888; font-size: 0.8rem;">${new Date(violation.timestamp).toLocaleString()}</span>
                            </div>
                            <div style="color: #ffb3c0; font-size: 0.9rem;">
                                ${violationText}
                            </div>
                        </div>
                        <div style="display: flex; gap: 8px; margin-left: 15px;">
                            <button class="delete-violation-btn" data-violation-timestamp="${violation.timestamp}" style="background: linear-gradient(135deg, #ff4466, #ff2244); border: none; color: #fff; padding: 6px 10px; border-radius: 5px; cursor: pointer; font-size: 0.75rem; font-weight: 600; transition: all 0.3s; white-space: nowrap;">🗑️ Delete</button>
                        </div>
                    </div>
                `;
            }).join('');

            // Add delete handlers for violations
            const deleteViolationButtons = violationsList.querySelectorAll('.delete-violation-btn');
            deleteViolationButtons.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const timestamp = btn.getAttribute('data-violation-timestamp');
                    if (confirm('Are you sure you want to delete this violation record?')) {
                        this.deleteViolation(student.lrn, timestamp);
                    }
                });
                // Add hover effect
                btn.addEventListener('mouseover', () => {
                    btn.style.background = 'linear-gradient(135deg, #ff6b7b, #ff4455)';
                    btn.style.transform = 'scale(1.05)';
                });
                btn.addEventListener('mouseout', () => {
                    btn.style.background = 'linear-gradient(135deg, #ff4466, #ff2244)';
                    btn.style.transform = 'scale(1)';
                });
            });
        }
    }

    toggleEditStudent() {
        if (!this.selectedStudentForDetail) return;
        const student = this.selectedStudentForDetail;
        const viewDiv = document.getElementById('studentInfoView');
        const editDiv = document.getElementById('studentInfoEdit');
        const editBtn = document.getElementById('editStudentBtn');

        // Switch to edit mode
        viewDiv.style.display = 'none';
        editDiv.style.display = 'block';
        editBtn.style.display = 'none';

        // Populate edit fields
        document.getElementById('editStudentName').value = student.name || '';
        document.getElementById('editStudentLrn').value = student.lrn || '';
        document.getElementById('editStudentGrade').value = student.grade || 'Grade 7';
        document.getElementById('editStudentSection').value = student.section || '';
        document.getElementById('editStudentPhone').value = student.phone || '';
        document.getElementById('editStudentEmail').value = student.email || '';
        document.getElementById('editStudentSex').value = student.sex || 'Male';
        document.getElementById('editStudentMotherName').value = student.mother_name || '';
        document.getElementById('editStudentMotherContact').value = student.mother_contact || '';
        document.getElementById('editStudentFatherName').value = student.father_name || '';
        document.getElementById('editStudentFatherContact').value = student.father_contact || '';
    }

    saveStudentEdit() {
        if (!this.selectedStudentForDetail) return;
        const oldLrn = this.selectedStudentForDetail.lrn;

        const updatedStudent = {
            name: document.getElementById('editStudentName').value.trim(),
            lrn: oldLrn, // LRN is readonly
            grade: document.getElementById('editStudentGrade').value,
            section: document.getElementById('editStudentSection').value.trim(),
            phone: document.getElementById('editStudentPhone').value.trim(),
            email: document.getElementById('editStudentEmail').value.trim(),
            sex: document.getElementById('editStudentSex').value,
            mother_name: document.getElementById('editStudentMotherName').value.trim(),
            mother_contact: document.getElementById('editStudentMotherContact').value.trim(),
            father_name: document.getElementById('editStudentFatherName').value.trim(),
            father_contact: document.getElementById('editStudentFatherContact').value.trim()
        };

        if (!updatedStudent.name) {
            alert('Name is required');
            return;
        }

        // Update in studentHistory
        const history = JSON.parse(localStorage.getItem('studentHistory') || '[]');
        const idx = history.findIndex(s => s.lrn === oldLrn);
        if (idx !== -1) {
            history[idx] = { ...history[idx], ...updatedStudent };
            localStorage.setItem('studentHistory', JSON.stringify(history));
        }

        // Update names in violation records too
        const violations = JSON.parse(localStorage.getItem('violationRecords') || '[]');
        violations.forEach(v => {
            if (v.student_lrn === oldLrn) {
                v.student_name = updatedStudent.name;
                v.student_grade = updatedStudent.grade;
                v.student_section = updatedStudent.section;
                v.student_sex = updatedStudent.sex;
            }
        });
        localStorage.setItem('violationRecords', JSON.stringify(violations));

        // Update the selected student reference
        this.selectedStudentForDetail = updatedStudent;

        // Switch back to view mode and refresh
        this.cancelEditStudent();
        this.loadStudentDetail();

        alert('✓ Student info updated successfully!');
    }

    cancelEditStudent() {
        const viewDiv = document.getElementById('studentInfoView');
        const editDiv = document.getElementById('studentInfoEdit');
        const editBtn = document.getElementById('editStudentBtn');

        viewDiv.style.display = 'grid';
        editDiv.style.display = 'none';
        editBtn.style.display = 'inline-block';
    }

    initPrintViolations() {
        const printBtn = document.getElementById('printViolationsBtn');
        if (printBtn) {
            printBtn.addEventListener('click', () => this.printStudentViolations());
        }

        const backBtn = document.getElementById('backToDashboardFromDetailBtn');
        if (backBtn) {
            backBtn.addEventListener('click', () => this.showPage('dashboard'));
        }
    }

    printStudentViolations() {
        if (!this.selectedStudentForDetail) return;

        const student = this.selectedStudentForDetail;
        const violations = JSON.parse(localStorage.getItem('violationRecords') || '[]');
        const studentViolations = violations.filter(v => v.student_lrn === student.lrn);

        const printWindow = window.open('', '', 'width=800,height=600');
        printWindow.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Violation Report - ${student.name}</title>
                <style>
                    body { font-family: Arial, sans-serif; padding: 20px; background: #fff; color: #333; }
                    h1 { color: #333; margin-bottom: 5px; }
                    .header { border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
                    .student-info { background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                    .info-row { display: flex; gap: 30px; margin: 5px 0; }
                    .info-label { font-weight: bold; min-width: 100px; }
                    .violations-title { font-size: 1.2rem; font-weight: bold; margin: 20px 0 10px 0; border-bottom: 1px solid #ddd; padding-bottom: 5px; }
                    .violation-item { background: #fff3cd; padding: 10px; margin: 10px 0; border-left: 3px solid #ff6b6b; border-radius: 3px; }
                    .violation-date { color: #666; font-size: 0.9rem; }
                    .clean-record { background: #d4edda; padding: 10px; margin: 10px 0; border-left: 3px solid #28a745; border-radius: 3px; color: #155724; }
                    @media print { body { background: white; } }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Student Violation Report</h1>
                    <p>National Christian Life College, Inc.</p>
                </div>

                <div class="student-info">
                    <div class="info-row">
                        <div><span class="info-label">Name:</span> ${student.name}</div>
                        <div><span class="info-label">LRN:</span> ${student.lrn}</div>
                    </div>
                    <div class="info-row">
                        <div><span class="info-label">Grade:</span> ${student.grade}</div>
                        <div><span class="info-label">Section:</span> ${student.section}</div>
                    </div>
                    <div class="info-row">
                        <div><span class="info-label">Phone:</span> ${student.phone || 'N/A'}</div>
                        <div><span class="info-label">Email:</span> ${student.email || 'N/A'}</div>
                    </div>
                </div>

                <div class="violations-title">Violations Record (Total Entries: ${studentViolations.length})</div>
                ${studentViolations.length > 0 ? studentViolations.map((v, idx) => {
            const violationText = v.violations && v.violations.length > 0
                ? v.violations.join(', ')
                : 'Clean record - no violations';
            const isClean = !v.violations || v.violations.length === 0;
            return `
                        <div class="${isClean ? 'clean-record' : 'violation-item'}">
                            <strong>Entry #${idx + 1}</strong>
                            <div class="violation-date">${new Date(v.timestamp).toLocaleString()}</div>
                            <div>${violationText}</div>
                        </div>
                    `;
        }).join('') : '<p style="color: #888;">No records for this student</p>'}

                <p style="margin-top: 30px; text-align: center; color: #888; font-size: 0.9rem;">
                    Generated on ${new Date().toLocaleString()}
                </p>
                <script>window.print();</script>
            </body>
            </html>
        `);
        printWindow.document.close();
    }

    printAllStudentRecords() {
        const history = JSON.parse(localStorage.getItem('studentHistory') || '[]');
        const violations = JSON.parse(localStorage.getItem('violationRecords') || '[]');

        if (history.length === 0) {
            alert('No student records to print.');
            return;
        }

        // Build table rows separately to avoid nested template literal issues
        const tableRows = history.map((student, idx) => {
            const studentViolations = violations.filter(v => v.student_lrn === student.lrn);
            const count = studentViolations.length;
            const countClass = count > 0 ? 'has-violations' : 'clean';
            const countText = count > 0 ? count + ' violation' + (count > 1 ? 's' : '') : 'Clean';
            return '<tr>' +
                '<td>' + (idx + 1) + '</td>' +
                '<td><strong>' + student.name + '</strong></td>' +
                '<td>' + student.lrn + '</td>' +
                '<td>' + student.grade + '</td>' +
                '<td>' + student.section + '</td>' +
                '<td>' + student.sex + '</td>' +
                '<td>' + (student.phone || 'N/A') + '</td>' +
                '<td>' + (student.email || 'N/A') + '</td>' +
                '<td class="violations-count ' + countClass + '">' + countText + '</td>' +
                '</tr>';
        }).join('');

        const printWindow = window.open('', '', 'width=1000,height=700');
        printWindow.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>All Student Records - NCLC</title>
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body { font-family: Arial, sans-serif; padding: 30px; background: #fff; color: #333; }
                    .header { text-align: center; border-bottom: 3px solid #0A0980; padding-bottom: 15px; margin-bottom: 25px; }
                    .header h1 { color: #0A0980; font-size: 1.6rem; margin-bottom: 4px; }
                    .header p { color: #555; font-size: 0.95rem; }
                    .summary { display: flex; justify-content: center; gap: 40px; margin-bottom: 20px; padding: 12px; background: #f0f4ff; border-radius: 6px; }
                    .summary-item { text-align: center; }
                    .summary-item .label { font-size: 0.8rem; color: #666; }
                    .summary-item .value { font-size: 1.4rem; font-weight: bold; color: #0A0980; }
                    table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
                    thead th { background: #0A0980; color: #fff; padding: 10px 8px; text-align: left; font-weight: 600; font-size: 0.8rem; }
                    tbody td { padding: 8px; border-bottom: 1px solid #ddd; }
                    tbody tr:nth-child(even) { background: #f9f9f9; }
                    tbody tr:hover { background: #f0f4ff; }
                    .violations-count { font-weight: bold; }
                    .violations-count.has-violations { color: #cc0000; }
                    .violations-count.clean { color: #28a745; }
                    .footer { margin-top: 25px; text-align: center; color: #888; font-size: 0.8rem; border-top: 1px solid #ddd; padding-top: 10px; }
                    @media print {
                        body { padding: 15px; }
                        thead th { background: #0A0980 !important; color: #fff !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
                        tbody tr:nth-child(even) { background: #f5f5f5 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Student Records Report</h1>
                    <p>National Christian Life College, Inc. — Student Violation Tracking System</p>
                </div>

                <div class="summary">
                    <div class="summary-item">
                        <div class="label">Total Students</div>
                        <div class="value">${history.length}</div>
                    </div>
                    <div class="summary-item">
                        <div class="label">Total Violations</div>
                        <div class="value">${violations.length}</div>
                    </div>
                    <div class="summary-item">
                        <div class="label">Report Date</div>
                        <div class="value" style="font-size: 1rem;">${new Date().toLocaleDateString()}</div>
                    </div>
                </div>

                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Name</th>
                            <th>LRN</th>
                            <th>Grade</th>
                            <th>Section</th>
                            <th>Gender</th>
                            <th>Phone</th>
                            <th>Email</th>
                            <th>Violations</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${tableRows}
                    </tbody>
                </table>

                <div class="footer">
                    Generated on ${new Date().toLocaleString()} — National Christian Life College, Inc.
                </div>
                <script>window.print();</script>
            </body>
            </html>
        `);
        printWindow.document.close();
    }
}

// Initialize detector instance
const detector = new FaceDetector();
const app = detector;  // Create global reference for navbar clicks
