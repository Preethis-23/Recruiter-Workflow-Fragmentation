const API_BASE = '/api';

// ─── DOM Elements ────────────────────────────────────────────────────────────
const navLinks = document.querySelectorAll('.nav-links li');
const views = document.querySelectorAll('.view-section');
const jdGrid = document.getElementById('jd-grid');
const resumesTable = document.querySelector('#resumes-table tbody');
const candidatesTable = document.querySelector('#candidates-table tbody');
const jdFilterSelect = document.getElementById('jd-filter-select');
const chatHistory = document.getElementById('chat-history');
const agentInput = document.getElementById('agent-input');
const apiStatus = document.getElementById('api-status');
const uploadZone = document.getElementById('upload-zone');
const uploadInput = document.getElementById('resume-upload-input');
const uploadStatus = document.getElementById('upload-status');
const agentConsoleOutput = document.getElementById('agent-console-output');
const agentInstruction = document.getElementById('agent-instruction');

// Custom Select Wrapper
function createCustomDropdown(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return;
    
    // Remove existing wrapper if it exists (for repopulating)
    if (select.parentElement.classList.contains('custom-select-wrapper')) {
        const wrapper = select.parentElement;
        wrapper.replaceWith(select);
        select.style.display = '';
    }

    const wrapper = document.createElement('div');
    wrapper.className = 'custom-select-wrapper';
    
    const trigger = document.createElement('div');
    trigger.className = 'custom-select glass-input';
    
    const selectedText = document.createElement('span');
    selectedText.textContent = select.options[select.selectedIndex]?.textContent || 'Select...';
    
    const arrow = document.createElement('i');
    arrow.className = 'fa-solid fa-chevron-down custom-arrow';
    
    trigger.appendChild(selectedText);
    trigger.appendChild(arrow);
    
    const optionsContainer = document.createElement('div');
    optionsContainer.className = 'custom-select-options';
    
    Array.from(select.options).forEach((opt, idx) => {
        const optionDiv = document.createElement('div');
        optionDiv.className = 'custom-select-option' + (opt.selected ? ' selected' : '');
        optionDiv.textContent = opt.textContent;
        optionDiv.dataset.value = opt.value;
        optionDiv.addEventListener('click', (e) => {
            e.stopPropagation();
            select.value = opt.value;
            selectedText.textContent = opt.textContent;
            select.dispatchEvent(new Event('change'));
            wrapper.classList.remove('open');
            Array.from(optionsContainer.children).forEach(c => c.classList.remove('selected'));
            optionDiv.classList.add('selected');
        });
        optionsContainer.appendChild(optionDiv);
    });
    
    trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        // Close all other dropdowns
        document.querySelectorAll('.custom-select-wrapper').forEach(w => {
            if (w !== wrapper) w.classList.remove('open');
        });
        wrapper.classList.toggle('open');
    });
    
    // Hide real select
    select.style.display = 'none';
    
    // Assemble
    select.parentNode.insertBefore(wrapper, select);
    wrapper.appendChild(select);
    wrapper.appendChild(trigger);
    wrapper.appendChild(optionsContainer);
}

document.addEventListener('click', () => {
    document.querySelectorAll('.custom-select-wrapper').forEach(w => w.classList.remove('open'));
});

// ─── Navigation ─────────────────────────────────────────────────────────────
navLinks.forEach(link => {
    link.addEventListener('click', () => {
        navLinks.forEach(l => l.classList.remove('active'));
        link.classList.add('active');
        const targetView = link.getAttribute('data-view');
        
        views.forEach(v => v.classList.remove('active'));
        document.getElementById(`view-${targetView}`).classList.add('active');
        
        if (targetView === 'dashboard') loadJDs();
        if (targetView === 'resumes') loadResumes();
        if (targetView === 'candidates') loadCandidates();
        if (targetView === 'settings') loadSelectedDefaultTemplate();
    });
});

// ─── API Health ─────────────────────────────────────────────────────────────
async function checkHealth() {
    try {
        const res = await fetch('/health');
        if (res.ok) {
            const data = await res.json();
            apiStatus.textContent = 'Online (' + data.llm_provider + ')';
            document.querySelector('.dot').style.background = 'var(--success)';
            document.querySelector('.dot').style.boxShadow = '0 0 8px var(--success)';
        } else {
            throw new Error('API Offline');
        }
    } catch (e) {
        apiStatus.textContent = 'Offline';
        document.querySelector('.dot').style.background = 'var(--danger)';
        document.querySelector('.dot').style.boxShadow = '0 0 8px var(--danger)';
    }
}

// ─── Job Descriptions ───────────────────────────────────────────────────────
async function loadJDs() {
    try {
        const res = await fetch(API_BASE + '/jds/');
        const jds = await res.json();
        
        jdGrid.innerHTML = '';
        if (jds.length === 0) {
            jdGrid.innerHTML = '<p style="color: var(--text-muted);">No Job Descriptions found. Create one to get started.</p>';
            return;
        }

        jds.forEach(jd => {
            const el = document.createElement('div');
            el.className = 'glass-panel jd-card';
            el.innerHTML = '<h3>' + escapeHtml(jd.title) + '</h3>' +
                '<div class="jd-meta">' +
                '<i class="fa-solid fa-building"></i> ' + escapeHtml(jd.department || 'N/A') + ' &nbsp;' +
                '<i class="fa-solid fa-location-dot"></i> ' + escapeHtml(jd.location || 'N/A') +
                '</div>' +
                '<p class="jd-desc">' + escapeHtml(jd.description) + '</p>' +
                '<div class="mt-4">' +
                '<button class="btn btn-sm btn-outline" onclick="deleteJD(' + jd.id + ')"><i class="fa-solid fa-trash"></i> Delete</button>' +
                '</div>';
            jdGrid.appendChild(el);
        });
    } catch (e) {
        console.error('Failed to load JDs', e);
    }
    populateJdFilter();
}

async function createJD(e) {
    e.preventDefault();
    const payload = {
        title: document.getElementById('jd-title').value,
        department: document.getElementById('jd-dept').value,
        description: document.getElementById('jd-desc').value,
        required_skills: document.getElementById('jd-skills').value,
    };
    
    try {
        const res = await fetch(API_BASE + '/jds/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        if (res.ok) {
            closeModals();
            loadJDs();
            document.getElementById('create-jd-form').reset();
        } else {
            const err = await res.json();
            alert('Error creating JD: ' + (err.detail || 'Unknown error'));
        }
    } catch (e) {
        alert('Failed to create JD. Check the console.');
        console.error(e);
    }
}
document.getElementById('create-jd-form').addEventListener('submit', createJD);

async function deleteJD(id) {
    if (!confirm('Delete this Job Description?')) return;
    await fetch(API_BASE + '/jds/' + id, { method: 'DELETE' });
    loadJDs();
}

// ─── Resume Upload (Drag & Drop + File Picker) ─────────────────────────────
async function uploadFile(file) {
    uploadStatus.textContent = 'Uploading ' + file.name + '...';
    
    const formData = new FormData();
    formData.append('file', file);
    
    const jdSelect = document.getElementById('upload-jd-select');
    if (!jdSelect || !jdSelect.value) {
        uploadStatus.style.color = 'var(--danger)';
        uploadStatus.textContent = '✗ Error: A target job description is required for uploading resumes.';
        return;
    }
    formData.append('jd_id', jdSelect.value);
    
    try {
        const res = await fetch(API_BASE + '/resumes/upload', {
            method: 'POST',
            body: formData
        });
        
        if (res.ok) {
            const data = await res.json();
            uploadStatus.style.color = 'var(--success)';
            uploadStatus.textContent = '✓ Uploaded: ' + (data.candidate_name || file.name);
            loadResumes();
        } else {
            const err = await res.json();
            uploadStatus.style.color = 'var(--danger)';
            uploadStatus.textContent = '✗ ' + (err.detail || 'Upload failed');
        }
    } catch (e) {
        uploadStatus.style.color = 'var(--danger)';
        uploadStatus.textContent = '✗ Network error uploading file';
        console.error(e);
    }
    
    // Reset status color after 5 seconds
    setTimeout(() => {
        uploadStatus.style.color = 'var(--text-muted)';
    }, 5000);
}

// File picker handler
uploadInput.addEventListener('change', async (e) => {
    const files = e.target.files;
    for (let i = 0; i < files.length; i++) {
        await uploadFile(files[i]);
    }
    uploadInput.value = '';  // Reset so same file can be re-selected
});

// Drag and drop handlers
uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('dragover');
});

uploadZone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
});

uploadZone.addEventListener('drop', async (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    for (let i = 0; i < files.length; i++) {
        await uploadFile(files[i]);
    }
});

// Resume listing
async function loadResumes() {
    try {
        const res = await fetch(API_BASE + '/resumes/');
        const resumes = await res.json();
        
        resumesTable.innerHTML = '';
        if (resumes.length === 0) {
            resumesTable.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No resumes uploaded yet.</td></tr>';
            return;
        }
        resumes.forEach(r => {
            const row = document.createElement('tr');
            const parsedDate = r.parsed_at ? new Date(r.parsed_at).toLocaleDateString() : 'N/A';
            const rolesHtml = r.applied_roles && r.applied_roles.length > 0 
                ? r.applied_roles.map(role => `<span class="badge" style="background: var(--primary); font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; margin-right: 4px;">${escapeHtml(role)}</span>`).join('')
                : '<span style="color: var(--text-muted); font-size: 0.85rem;">General Pool</span>';

            row.innerHTML = '<td><strong>' + escapeHtml(r.candidate_name || 'Unknown') + '</strong></td>' +
                '<td>' + escapeHtml(r.email || 'N/A') + '</td>' +
                '<td>' + rolesHtml + '</td>' +
                '<td>' + parsedDate + '</td>' +
                '<td><button class="icon-btn" onclick="deleteResume(' + r.id + ')"><i class="fa-solid fa-trash" style="color: var(--danger);"></i></button></td>';
            resumesTable.appendChild(row);
        });
    } catch (e) {
        console.error('Failed to load resumes', e);
    }
}

async function deleteResume(id) {
    if (!confirm('Delete this resume?')) return;
    await fetch(API_BASE + '/resumes/' + id, { method: 'DELETE' });
    loadResumes();
}

// ─── Candidates ─────────────────────────────────────────────────────────────
async function populateJdFilter() {
    try {
        const res = await fetch(API_BASE + '/jds/');
        const jds = await res.json();
        jdFilterSelect.innerHTML = '<option value="">All Job Descriptions</option>';
        jds.forEach(jd => {
            const opt = document.createElement('option');
            opt.value = jd.id;
            opt.textContent = jd.title;
            jdFilterSelect.appendChild(opt);
        });
        
        // Also populate the upload target role select
        const uploadSelect = document.getElementById('upload-jd-select');
        if (uploadSelect) {
            uploadSelect.innerHTML = '<option value="" disabled selected>Select Job Description...</option>';
            jds.forEach(jd => {
                const opt = document.createElement('option');
                opt.value = jd.id;
                opt.textContent = jd.title;
                uploadSelect.appendChild(opt);
            });
        }
        
        // Convert to custom animated dropdowns
        createCustomDropdown('jd-filter-select');
        createCustomDropdown('upload-jd-select');
    } catch (e) {
        console.error('Failed to load JD filter', e);
    }
}

jdFilterSelect.addEventListener('change', loadCandidates);

let selectedCandidates = new Set();

function toggleSelectAllCandidates(masterCheckbox) {
    const checkboxes = document.querySelectorAll('.candidate-checkbox');
    selectedCandidates.clear();
    checkboxes.forEach(cb => {
        cb.checked = masterCheckbox.checked;
        if (cb.checked) {
            selectedCandidates.add(parseInt(cb.dataset.id));
        }
    });
    updateBulkActionsState();
}

function onCandidateCheckboxChange(id, cb) {
    if (cb.checked) {
        selectedCandidates.add(id);
    } else {
        selectedCandidates.delete(id);
    }
    
    // Update master select checkbox status
    const master = document.getElementById('select-all-candidates');
    const totalCount = document.querySelectorAll('.candidate-checkbox').length;
    master.checked = (selectedCandidates.size === totalCount && totalCount > 0);
    master.indeterminate = (selectedCandidates.size > 0 && selectedCandidates.size < totalCount);
    
    updateBulkActionsState();
}

function updateBulkActionsState() {
    const countSpan = document.getElementById('selected-count');
    countSpan.textContent = selectedCandidates.size + ' candidates selected';
    
    const emailBtn = document.getElementById('btn-bulk-email');
    const scheduleBtn = document.getElementById('btn-bulk-schedule');
    
    const hasSelection = selectedCandidates.size > 0;
    emailBtn.disabled = !hasSelection;
    scheduleBtn.disabled = !hasSelection;
}

async function loadCandidates() {
    try {
        const jdId = jdFilterSelect.value;
        const url = jdId ? (API_BASE + '/candidates/?jd_id=' + jdId) : (API_BASE + '/candidates/');
        const res = await fetch(url);
        const cands = await res.json();
        
        // Reset bulk selection
        selectedCandidates.clear();
        document.getElementById('select-all-candidates').checked = false;
        document.getElementById('select-all-candidates').indeterminate = false;
        updateBulkActionsState();
        
        candidatesTable.innerHTML = '';
        if (cands.length === 0) {
            candidatesTable.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No candidates yet. Upload resumes and rank them against a JD.</td></tr>';
            return;
        }
        
        cands.forEach(c => {
            const score = c.similarity_score ? (c.similarity_score * 100).toFixed(1) + '%' : 'N/A';
            const name = c.resume ? (c.resume.candidate_name || 'Unknown') : 'Unknown';
            const roleTitle = c.job_description ? c.job_description.title : 'JD #' + c.jd_id;
            
            let badgeClass = 'status-new';
            const st = c.status || 'New';
            if (st.includes('Screening')) badgeClass = 'status-screening';
            if (st.includes('Interview')) badgeClass = 'status-interview';
            if (st.includes('Offer')) badgeClass = 'status-offer';
            if (st.includes('Reject')) badgeClass = 'status-rejected';

            const row = document.createElement('tr');
            row.innerHTML = `
                <td><input type="checkbox" class="candidate-checkbox" data-id="${c.id}" onchange="onCandidateCheckboxChange(${c.id}, this)" style="cursor: pointer; width: 16px; height: 16px; accent-color: var(--primary);"></td>
                <td><strong>${escapeHtml(name)}</strong></td>
                <td><span class="status-badge ${badgeClass}">${escapeHtml(st)}</span></td>
                <td><button class="btn btn-sm btn-outline" onclick="openNotesModal(${c.id}, \`${escapeHtml(c.notes || '').replace(/`/g, '&#96;')}\`)"><i class="fa-solid fa-pen-to-square"></i> Notes</button></td>
                <td><button class="btn btn-sm btn-outline" onclick="viewCandidate(${c.id})">Profile</button></td>
            `;
            candidatesTable.appendChild(row);
        });
    } catch (e) {
        console.error('Failed to load candidates', e);
    }
}

let currentNotesCandidateId = null;

function openNotesModal(id, currentNotes) {
    currentNotesCandidateId = id;
    document.getElementById('candidate-notes-text').value = currentNotes || '';
    document.getElementById('notes-modal').classList.add('active');
}

async function saveNotesFromModal() {
    if (!currentNotesCandidateId) return;
    const val = document.getElementById('candidate-notes-text').value;
    const btn = document.getElementById('save-notes-btn');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Saving...';
    
    try {
        const res = await fetch(API_BASE + '/candidates/' + currentNotesCandidateId + '/notes', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes: val })
        });
        if (!res.ok) {
            console.error('Failed to save notes');
            alert('Failed to save notes.');
        } else {
            closeModals();
            loadCandidates();
        }
    } catch (e) {
        console.error('Error saving candidate notes:', e);
    }
    btn.disabled = false;
    btn.innerHTML = originalText;
}


async function triggerRanking() {
    const jdId = jdFilterSelect.value;
    if (!jdId) {
        alert('Select a Job Description from the dropdown first to rank candidates.');
        return;
    }
    
    const btn = document.querySelector('[onclick="triggerRanking()"]');
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Ranking...';
    
    try {
        const res = await fetch(API_BASE + '/candidates/rank/' + jdId, { method: 'POST' });
        const data = await res.json();
        
        if (res.ok) {
            alert('Ranked ' + (data.results ? data.results.length : 0) + ' candidates successfully!');
        } else {
            alert('Error: ' + (data.detail || 'Ranking failed'));
        }
    } catch (e) {
        alert('Network error during ranking. Check console.');
        console.error(e);
    }
    
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-ranking-star"></i> Rank Candidates';
    loadCandidates();
}

// ─── Modals & Candidate Profile ─────────────────────────────────────────────
function showCreateJDModal() {
    document.getElementById('jd-modal').classList.add('active');
}

function closeModals() {
    document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
}

// Currently viewed candidate ID (used across sections)
let currentCandidateId = null;

async function viewCandidate(id) {
    currentCandidateId = id;
    document.getElementById('candidate-modal').classList.add('active');
    document.getElementById('candidate-modal-title').textContent = 'Candidate #' + id;
    
    // Reset sections and convert to custom dropdowns
    document.getElementById('candidate-summary').textContent = 'No AI summary generated yet.';
    document.getElementById('candidate-questions').innerHTML = '';
    document.getElementById('email-preview').style.display = 'none';
    
    createCustomDropdown('email-template-select');
    createCustomDropdown('round-status');
    
    try {
        const res = await fetch(API_BASE + '/candidates/' + id);
        const data = await res.json();
        
        const name = data.resume ? (data.resume.candidate_name || 'Unknown') : 'Unknown';
        document.getElementById('candidate-modal-title').textContent = escapeHtml(name);
        document.getElementById('candidate-summary').textContent = data.summary || 'No AI summary generated yet.';
        
        // Render Match Details & Automation Status
        const score = data.similarity_score ? (data.similarity_score * 100).toFixed(1) + '%' : 'N/A';
        document.getElementById('cand-match-score').textContent = score;
        
        // Email Status Badge
        const emailStatusEl = document.getElementById('cand-email-status');
        emailStatusEl.textContent = data.email_status || 'Pending';
        if (data.email_status === 'Sent') {
            emailStatusEl.className = 'status-badge status-offer'; // Reuse green status class
        } else if (data.email_status === 'Failed') {
            emailStatusEl.className = 'status-badge status-rejected'; // Reuse red status class
            emailStatusEl.title = data.email_error_reason || 'Unknown error';
        } else {
            emailStatusEl.className = 'status-badge status-screening'; // Reuse orange/grey
        }
        
        document.getElementById('cand-calendar-event').textContent = data.calendar_event_id || 'None';
        
        const linkEl = document.getElementById('cand-meeting-link');
        if (data.meeting_link) {
            linkEl.innerHTML = '<a href="' + escapeHtml(data.meeting_link) + '" target="_blank" style="color: var(--primary); text-decoration: underline; font-weight: 600;"><i class="fa-solid fa-video"></i> Join Meet</a>';
        } else {
            linkEl.textContent = 'None';
        }
        
        document.getElementById('cand-match-explanation').textContent = data.explanation || 'No explanation generated yet.';
        
        // Render existing questions if stored
        const questionsList = document.getElementById('candidate-questions');
        questionsList.innerHTML = '';
        if (data.interview_questions) {
            const questions = data.interview_questions.split('\n');
            questions.forEach(q => {
                if (q.trim()) {
                    const li = document.createElement('li');
                    li.textContent = q;
                    questionsList.appendChild(li);
                }
            });
        }
    } catch (e) {
        document.getElementById('candidate-summary').textContent = 'Failed to load candidate.';
        console.error(e);
    }
    
    // Load pipeline stages
    loadPipeline(id);
    
    // Load meetings
    loadMeetings(id);
    
    // Wire AI buttons
    document.getElementById('btn-gen-summary').onclick = async () => {
        document.getElementById('candidate-summary').textContent = 'Generating summary via LLM...';
        try {
            const sRes = await fetch(API_BASE + '/candidates/' + id + '/summary', { method: 'POST' });
            const sData = await sRes.json();
            document.getElementById('candidate-summary').textContent = sData.summary || sData.detail || 'Could not generate summary.';
        } catch (e) {
            document.getElementById('candidate-summary').textContent = 'Error generating summary.';
        }
    };
    
    document.getElementById('btn-gen-questions').onclick = async () => {
        document.getElementById('candidate-questions').innerHTML = '<li>Generating questions...</li>';
        try {
            const qRes = await fetch(API_BASE + '/interview/questions/' + id, { method: 'POST' });
            const qData = await qRes.json();
            const list = document.getElementById('candidate-questions');
            list.innerHTML = '';
            if (qData.questions && qData.questions.length > 0) {
                qData.questions.forEach(q => {
                    const li = document.createElement('li');
                    li.textContent = q;
                    list.appendChild(li);
                });
            } else {
                list.innerHTML = '<li>No questions generated. ' + (qData.detail || '') + '</li>';
            }
        } catch (e) {
            document.getElementById('candidate-questions').innerHTML = '<li>Error generating questions.</li>';
        }
    };
}

// ─── Pipeline Stepper ───────────────────────────────────────────────────────
const PIPELINE_STAGES = [
    'Screening', 'Phone Interview', 'Technical Interview', 'HR Interview',
    'Assignment', 'Final Round', 'Offer', 'Hired'
];

const ALL_ROUNDS = ["Screening", "Phone Interview", "Technical Interview", "HR Interview", "Assignment", "Final Round", "Offer", "Hired", "Rejected"];
let currentRoundIndex = 0;
let candidateStages = [];

async function loadPipeline(candidateId) {
    candidateStages = [];
    try {
        const res = await fetch(API_BASE + '/stages/candidate/' + candidateId);
        candidateStages = await res.json();
    } catch (e) {
        console.error('Failed to load rounds history', e);
    }
    
    if (candidateStages.length > 0) {
        const latestStage = candidateStages[candidateStages.length - 1].stage;
        const idx = ALL_ROUNDS.indexOf(latestStage);
        currentRoundIndex = idx >= 0 ? idx : 0;
    } else {
        currentRoundIndex = 0;
    }
    
    renderRoundDetails();
}

function prevRound() {
    if (currentRoundIndex > 0) {
        currentRoundIndex--;
        renderRoundDetails();
    }
}

function nextRound() {
    if (currentRoundIndex < ALL_ROUNDS.length - 1) {
        currentRoundIndex++;
        renderRoundDetails();
    }
}

function renderRoundDetails() {
    const roundName = ALL_ROUNDS[currentRoundIndex];
    document.getElementById('current-round-display').textContent = roundName;
    
    const stageEntry = candidateStages.find(s => s.stage === roundName);
    const badge = document.getElementById('round-status-badge');
    
    if (stageEntry) {
        badge.textContent = stageEntry.status || 'Pending';
        badge.className = 'status-badge ' + (stageEntry.status === 'Completed' ? 'status-offer' : (stageEntry.status === 'Failed' ? 'status-rejected' : 'status-screening'));
        
        document.getElementById('round-status').value = stageEntry.status || 'Pending';
        document.getElementById('round-feedback').value = stageEntry.feedback_notes || '';
        
        if (stageEntry.scheduled_date) {
            const date = new Date(stageEntry.scheduled_date);
            const tzOffset = date.getTimezoneOffset() * 60000;
            const localISOTime = (new Date(date - tzOffset)).toISOString().slice(0, 16);
            document.getElementById('round-scheduled-date').value = localISOTime;
        } else {
            document.getElementById('round-scheduled-date').value = '';
        }
    } else {
        badge.textContent = 'Not Started';
        badge.className = 'status-badge status-new';
        
        document.getElementById('round-status').value = 'Pending';
        document.getElementById('round-feedback').value = '';
        document.getElementById('round-scheduled-date').value = '';
    }
    
    createCustomDropdown('round-status');
}

async function saveRoundDetails() {
    if (!currentCandidateId) return;
    const roundName = ALL_ROUNDS[currentRoundIndex];
    const status = document.getElementById('round-status').value;
    const feedback = document.getElementById('round-feedback').value;
    const scheduledDateVal = document.getElementById('round-scheduled-date').value;
    
    const btn = document.getElementById('btn-save-round');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Saving...';
    
    const payload = {
        stage: roundName,
        status: status,
        feedback_notes: feedback
    };
    if (scheduledDateVal) {
        payload.scheduled_date = new Date(scheduledDateVal).toISOString();
    }
    
    try {
        const res = await fetch(API_BASE + '/stages/candidate/' + currentCandidateId, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (res.ok) {
            alert('Round details saved successfully!');
            await loadPipeline(currentCandidateId);
            loadCandidates();
        } else {
            const err = await res.json();
            alert('Error saving round details: ' + (err.detail || 'Unknown error'));
        }
    } catch (e) {
        alert('Network error saving round details.');
        console.error(e);
    }
    btn.disabled = false;
    btn.innerHTML = originalText;
}

// ─── Email Generation ───────────────────────────────────────────────────────
async function generateEmail() {
    if (!currentCandidateId) return;
    const templateType = document.getElementById('email-template-select').value;
    
    const subjectPattern = localStorage.getItem(`template_${templateType}_subject`);
    const bodyPattern = localStorage.getItem(`template_${templateType}_body`);
    
    const customData = {};
    if (subjectPattern) customData.subject_pattern = subjectPattern;
    if (bodyPattern) customData.body_pattern = bodyPattern;
    
    try {
        const res = await fetch(API_BASE + '/email/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                candidate_id: currentCandidateId,
                template_type: templateType,
                custom_data: customData
            })
        });
        const data = await res.json();
        
        if (res.ok) {
            document.getElementById('email-subject').value = data.subject || '';
            document.getElementById('email-body').value = data.body || '';
            document.getElementById('email-preview').style.display = 'block';
        } else {
            alert('Error: ' + (data.detail || 'Failed to generate email'));
        }
    } catch (e) {
        alert('Network error generating email.');
        console.error(e);
    }
}

async function sendDraftedEmail() {
    if (!currentCandidateId) return;
    
    const subject = document.getElementById('email-subject').value;
    const body = document.getElementById('email-body').value;
    const type = document.getElementById('email-template-select').value;
    
    const btn = document.querySelector('[onclick="sendDraftedEmail()"]');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Sending...';
    
    try {
        const res = await fetch(API_BASE + '/email/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                candidate_id: currentCandidateId,
                template_type: type,
                custom_data: {
                    subject_override: subject,
                    body_override: body
                }
            })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            alert('Email sent successfully!');
            viewCandidate(currentCandidateId);
        } else {
            alert('Failed to send email: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        alert('Network error sending email.');
    }
    btn.disabled = false;
    btn.innerHTML = originalText;
}

function copyEmail() {
    const subject = document.getElementById('email-subject').value;
    const body = document.getElementById('email-body').value;
    const full = 'Subject: ' + subject + '\n\n' + body;
    navigator.clipboard.writeText(full).then(() => {
        alert('Email copied to clipboard!');
    }).catch(() => {
        const ta = document.createElement('textarea');
        ta.value = full;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        alert('Email copied to clipboard!');
    });
}

// ─── Meeting Scheduling ────────────────────────────────────────────────────
async function loadMeetings(candidateId) {
    const container = document.getElementById('meetings-list');
    container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.85rem;"><i class="fa-solid fa-spinner fa-spin"></i> Loading...</p>';
    
    try {
        const res = await fetch(API_BASE + '/meetings/candidate/' + candidateId);
        const meetings = await res.json();
        
        if (meetings.length === 0) {
            container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.9rem;">No meetings scheduled yet.</p>';
            return;
        }
        
        container.innerHTML = '';
        meetings.forEach(m => {
            const dateStr = m.scheduled_at ? new Date(m.scheduled_at).toLocaleString() : 'TBD';
            const durStr = m.duration_minutes ? m.duration_minutes + ' min' : '';
            
            const card = document.createElement('div');
            card.className = 'meeting-card';
            card.innerHTML = `
                <div class="meeting-info">
                    <span class="meeting-title-text">${escapeHtml(m.title)}</span>
                    <span class="meeting-meta"><i class="fa-regular fa-clock"></i> ${dateStr} ${durStr ? '&middot; ' + durStr : ''}</span>
                    ${m.attendees ? '<span class="meeting-meta"><i class="fa-regular fa-user"></i> ' + escapeHtml(m.attendees) + '</span>' : ''}
                </div>
                <div class="meeting-actions">
                    ${m.meeting_link ? '<a href="' + escapeHtml(m.meeting_link) + '" target="_blank" class="meeting-link-btn"><i class="fa-solid fa-video"></i> Join</a>' : ''}
                    <button class="icon-btn" onclick="deleteMeeting(${m.id})"><i class="fa-solid fa-trash" style="color: var(--danger); font-size: 0.8rem;"></i></button>
                </div>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        container.innerHTML = '<p style="color: var(--danger); font-size: 0.9rem;">Failed to load meetings.</p>';
        console.error(e);
    }
}

async function scheduleMeeting() {
    if (!currentCandidateId) return;
    
    const title = document.getElementById('meeting-title').value.trim();
    if (!title) { alert('Meeting title is required.'); return; }
    
    const payload = {
        title: title,
        meeting_link: document.getElementById('meeting-link').value.trim() || null,
        duration_minutes: parseInt(document.getElementById('meeting-duration').value) || 30,
        attendees: document.getElementById('meeting-attendees').value.trim() || null,
        notes: document.getElementById('meeting-notes').value.trim() || null,
    };
    
    const dateVal = document.getElementById('meeting-datetime').value;
    if (dateVal) payload.scheduled_at = new Date(dateVal).toISOString();
    
    try {
        const res = await fetch(API_BASE + '/meetings/candidate/' + currentCandidateId, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (res.ok) {
            // Clear form
            document.getElementById('meeting-title').value = '';
            document.getElementById('meeting-link').value = '';
            document.getElementById('meeting-datetime').value = '';
            document.getElementById('meeting-duration').value = '30';
            document.getElementById('meeting-attendees').value = '';
            document.getElementById('meeting-notes').value = '';
            
            loadMeetings(currentCandidateId);
        } else {
            const err = await res.json();
            alert('Error: ' + (err.detail || 'Failed to schedule meeting'));
        }
    } catch (e) {
        alert('Network error scheduling meeting.');
        console.error(e);
    }
}

async function deleteMeeting(meetingId) {
    if (!confirm('Delete this meeting?')) return;
    try {
        await fetch(API_BASE + '/meetings/' + meetingId, { method: 'DELETE' });
        if (currentCandidateId) loadMeetings(currentCandidateId);
    } catch (e) {
        alert('Failed to delete meeting.');
    }
}

// ─── Full Pipeline Automation ───────────────────────────────────────────────
async function runFullPipeline() {
    const jdId = jdFilterSelect.value;
    if (!jdId) {
        alert('Select a Job Description from the dropdown first to run the full pipeline.');
        return;
    }
    
    const btn = document.querySelector('[onclick="runFullPipeline()"]');
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Running Pipeline...';
    
    try {
        const res = await fetch(API_BASE + '/agent/pipeline/' + jdId, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        
        if (res.ok) {
            alert('Full pipeline completed successfully! ' + (data.summary || ''));
        } else {
            alert('Pipeline error: ' + (data.detail || 'Unknown error'));
        }
    } catch (e) {
        alert('Network error running pipeline.');
        console.error(e);
    }
    
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-rocket"></i> Run Full Pipeline';
    loadCandidates();
}

// ─── AI Agent Console ───────────────────────────────────────────────────────
agentInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendAgentMessage();
});

async function sendAgentMessage() {
    const text = agentInput.value.trim();
    if (!text) return;
    
    // Add user message
    const userMsg = document.createElement('div');
    userMsg.className = 'message user';
    userMsg.innerHTML = '<div class="message-content">' + escapeHtml(text) + '</div>';
    chatHistory.appendChild(userMsg);
    
    agentInput.value = '';
    
    // Show typing indicator
    const typingEl = document.createElement('div');
    typingEl.className = 'message system';
    typingEl.innerHTML = '<div class="message-content"><i class="fa-solid fa-circle-notch fa-spin"></i> Agent is thinking...</div>';
    chatHistory.appendChild(typingEl);
    chatHistory.scrollTo(0, chatHistory.scrollHeight);
    
    try {
        const res = await fetch(API_BASE + '/agent/execute', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ instruction: text })
        });
        
        const data = await res.json();
        
        // Remove typing indicator
        typingEl.remove();
        
        // Handle error responses from FastAPI (non-200)
        if (!res.ok) {
            const errMsg = data.detail || data.message || 'Agent returned an error (status ' + res.status + ')';
            appendSystemMessage('⚠️ ' + errMsg);
            return;
        }
        
        // Build response HTML
        let html = '';
        
        // Summary text
        const summaryText = data.summary || 'Task completed.';
        html += escapeHtml(summaryText).replace(/\n/g, '<br>');
        
        // Tool actions trace
        if (data.actions && data.actions.length > 0) {
            html += '<div class="tool-trace" style="margin-top: 15px; padding: 15px; background: rgba(0,0,0,0.2); border-radius: 8px; border: 1px solid var(--glass-border);">';
            html += '<h4 style="margin: 0 0 10px 0; font-size: 0.9rem; color: var(--text-muted);"><i class="fa-solid fa-list-check"></i> Execution Log (' + data.actions.length + ' steps):</h4>';
            html += '<ul style="list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px;">';
            data.actions.forEach((a, i) => {
                const success = a.result && a.result.success;
                const icon = success ? '<i class="fa-solid fa-circle-check" style="color: var(--success-color);"></i>' : '<i class="fa-solid fa-circle-xmark" style="color: var(--error-color);"></i>';
                
                // Try to extract a clean summary from the result, fallback to a brief stringified version
                let detail = '';
                if (a.result && a.result.detail) detail = a.result.detail;
                else if (a.result && a.result.note) detail = a.result.note;
                else if (a.result && a.result.error) detail = a.result.error;
                else detail = Object.keys(a.result).filter(k => k !== 'success').map(k => `${k}: ${a.result[k]}`).join(', ').substring(0, 100);
                
                html += `<li style="font-size: 0.85rem; padding: 8px 12px; background: rgba(255,255,255,0.03); border-radius: 6px; border-left: 3px solid ${success ? 'var(--success-color)' : 'var(--error-color)'};">`;
                html += `  <div style="display: flex; align-items: center; gap: 8px; font-weight: 500;">${icon} Step ${i+1}: <code>${escapeHtml(a.tool)}</code></div>`;
                html += `  <div style="margin-top: 4px; color: var(--text-muted); padding-left: 22px;">${escapeHtml(detail)}</div>`;
                html += `</li>`;
            });
            html += '</ul></div>';
        }
        
        appendSystemMessage(html, true);
        
        // Refresh data views
        loadJDs();
        loadResumes();
        loadCandidates();
    } catch (e) {
        typingEl.remove();
        appendSystemMessage('⚠️ Error communicating with agent. Make sure the server is running.');
        console.error('Agent error:', e);
    }
}

function appendSystemMessage(html, isRaw) {
    const msgEl = document.createElement('div');
    msgEl.className = 'message system';
    const contentEl = document.createElement('div');
    contentEl.className = 'message-content';
    contentEl.innerHTML = html;
    msgEl.appendChild(contentEl);
    chatHistory.appendChild(msgEl);
    chatHistory.scrollTo(0, chatHistory.scrollHeight);
}

// ─── Bulk Actions ───────────────────────────────────────────────────────────
async function bulkSendEmail() {
    if (selectedCandidates.size === 0) return;
    
    const btn = document.getElementById('btn-bulk-email');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Sending...';
    
    let successCount = 0;
    let failCount = 0;
    
    try {
        const jdId = jdFilterSelect.value;
        const url = jdId ? (API_BASE + '/candidates/?jd_id=' + jdId) : (API_BASE + '/candidates/');
        const res = await fetch(url);
        const cands = await res.json();
        
        for (const candId of selectedCandidates) {
            const cand = cands.find(c => c.id === candId);
            if (!cand) continue;
            
            let templateType = 'follow_up';
            const st = (cand.status || '').toLowerCase();
            if (st.includes('reject')) {
                templateType = 'rejection';
            } else if (st.includes('interview')) {
                templateType = 'interview_scheduling';
            } else if (st.includes('offer') || st.includes('hire')) {
                templateType = 'offer';
            }
            
            
            const subjectPattern = localStorage.getItem(`template_${templateType}_subject`);
            const bodyPattern = localStorage.getItem(`template_${templateType}_body`);
            
            const customData = {};
            if (subjectPattern) customData.subject_pattern = subjectPattern;
            if (bodyPattern) customData.body_pattern = bodyPattern;
            
            try {
                const sendRes = await fetch(API_BASE + '/email/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        candidate_id: candId,
                        template_type: templateType,
                        custom_data: customData
                    })
                });
                const sendData = await sendRes.json();
                if (sendRes.ok && sendData.success) {
                    successCount++;
                } else {
                    failCount++;
                }
            } catch (err) {
                failCount++;
            }
        }
        
        alert(`Status Emails Sent!\nSuccessful: ${successCount}\nFailed: ${failCount}`);
    } catch (e) {
        alert('Error processing bulk emails.');
        console.error(e);
    }
    
    btn.disabled = false;
    btn.innerHTML = originalText;
    loadCandidates();
}

function openBulkScheduleModal() {
    if (selectedCandidates.size === 0) return;
    document.getElementById('bulk-schedule-modal').classList.add('active');
}

async function bulkScheduleMeetings(e) {
    e.preventDefault();
    if (selectedCandidates.size === 0) return;
    
    const title = document.getElementById('bulk-meeting-title').value.trim();
    const datetime = document.getElementById('bulk-meeting-datetime').value;
    const duration = parseInt(document.getElementById('bulk-meeting-duration').value) || 30;
    const notes = document.getElementById('bulk-meeting-notes').value.trim();
    
    const submitBtn = document.querySelector('#bulk-schedule-form button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Scheduling...';
    
    let successCount = 0;
    let failCount = 0;
    
    for (const candId of selectedCandidates) {
        const code = Math.random().toString(36).substring(2, 5) + '-' + Math.random().toString(36).substring(2, 6) + '-' + Math.random().toString(36).substring(2, 5);
        const link = `https://meet.google.com/${code}`;
        
        const payload = {
            title: title,
            meeting_link: link,
            scheduled_at: new Date(datetime).toISOString(),
            duration_minutes: duration,
            notes: notes
        };
        
        try {
            const res = await fetch(API_BASE + '/meetings/candidate/' + candId, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                await fetch(API_BASE + '/stages/candidate/' + candId, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        stage: 'Technical Interview',
                        scheduled_date: new Date(datetime).toISOString()
                    })
                });
                successCount++;
            } else {
                failCount++;
            }
        } catch (err) {
            failCount++;
        }
    }
    
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalText;
    
    closeModals();
    document.getElementById('bulk-schedule-form').reset();
    
    alert(`Interviews Scheduled!\nSuccessful: ${successCount}\nFailed: ${failCount}`);
    loadCandidates();
}

// ─── Settings Default Templates ─────────────────────────────────────────────
const DEFAULT_TEMPLATES_MAPPING = {
    interview_scheduling: {
        subject: "Interview Invitation: #name - #position",
        body: "Dear #name,\n\nWe are pleased to invite you to schedule your Technical Interview for the #position role.\n\nDate: #date\n\nBest regards,\nRecruitment Team"
    },
    offer: {
        subject: "Job Offer: #name - #position",
        body: "Dear #name,\n\nWe are thrilled to offer you the #position position at our company.\n\nStage reached: #stage\n\nBest regards,\nRecruitment Team"
    },
    rejection: {
        subject: "Application Update: #name - #position",
        body: "Dear #name,\n\nThank you for interest in the #position role. Unfortunately, we will not be moving forward with your application at this time.\n\nBest regards,\nRecruitment Team"
    },
    follow_up: {
        subject: "Follow-up: #name - #position",
        body: "Dear #name,\n\nWe are writing to follow up on your recent application status for the #position role.\n\nBest regards,\nRecruitment Team"
    }
};

function initializeDefaultTemplates() {
    Object.keys(DEFAULT_TEMPLATES_MAPPING).forEach(type => {
        if (!localStorage.getItem(`template_${type}_subject`)) {
            localStorage.setItem(`template_${type}_subject`, DEFAULT_TEMPLATES_MAPPING[type].subject);
        }
        if (!localStorage.getItem(`template_${type}_body`)) {
            localStorage.setItem(`template_${type}_body`, DEFAULT_TEMPLATES_MAPPING[type].body);
        }
    });
}

function loadSelectedDefaultTemplate() {
    createCustomDropdown('settings-template-type');
    const type = document.getElementById('settings-template-type').value;
    const subject = localStorage.getItem(`template_${type}_subject`);
    const body = localStorage.getItem(`template_${type}_body`);
    
    document.getElementById('settings-template-subject').value = subject || '';
    document.getElementById('settings-template-body').value = body || '';
}

function saveDefaultTemplate() {
    const type = document.getElementById('settings-template-type').value;
    const subject = document.getElementById('settings-template-subject').value;
    const body = document.getElementById('settings-template-body').value;
    
    localStorage.setItem(`template_${type}_subject`, subject);
    localStorage.setItem(`template_${type}_body`, body);
    
    alert('Default template pattern saved!');
}

// ─── Helpers ────────────────────────────────────────────────────────────────
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ─── Initialize ─────────────────────────────────────────────────────────────
initializeDefaultTemplates();
checkHealth();
loadJDs();
