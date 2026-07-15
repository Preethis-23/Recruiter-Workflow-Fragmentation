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
        if (targetView === 'resumes') {
            populateJdFilter();
            loadResumes();
        }
        if (targetView === 'candidates') {
            populateJdFilter();
            loadCandidates();
        }
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
    if (jdSelect && jdSelect.value) {
        formData.append('jd_id', jdSelect.value);
    }
    
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
            uploadSelect.innerHTML = '<option value="">General Pool (No Role)</option>';
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

async function loadCandidates() {
    try {
        const jdId = jdFilterSelect.value;
        const url = jdId ? (API_BASE + '/candidates/?jd_id=' + jdId) : (API_BASE + '/candidates/');
        const res = await fetch(url);
        const cands = await res.json();
        
        candidatesTable.innerHTML = '';
        if (cands.length === 0) {
            candidatesTable.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No candidates yet. Upload resumes and rank them against a JD.</td></tr>';
            return;
        }
        
        cands.forEach(c => {
            const score = c.similarity_score ? (c.similarity_score * 100).toFixed(1) + '%' : 'N/A';
            const name = c.resume ? (c.resume.candidate_name || 'Unknown') : 'Unknown';
            
            let badgeClass = 'status-new';
            const st = c.status || 'New';
            if (st.includes('Screening')) badgeClass = 'status-screening';
            if (st.includes('Interview')) badgeClass = 'status-interview';
            if (st.includes('Offer')) badgeClass = 'status-offer';
            if (st.includes('Reject')) badgeClass = 'status-rejected';

            const row = document.createElement('tr');
            row.innerHTML = '<td><strong>' + escapeHtml(name) + '</strong></td>' +
                '<td><span class="status-badge ' + badgeClass + '">' + escapeHtml(st) + '</span></td>' +
                '<td>' + score + '</td>' +
                '<td>JD #' + c.jd_id + '</td>' +
                '<td><button class="btn btn-sm btn-outline" onclick="viewCandidate(' + c.id + ')">Profile</button></td>';
            candidatesTable.appendChild(row);
        });
    } catch (e) {
        console.error('Failed to load candidates', e);
    }
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
    
    // Reset sections
    document.getElementById('candidate-summary').textContent = 'No AI summary generated yet.';
    document.getElementById('candidate-questions').innerHTML = '';
    document.getElementById('email-preview').style.display = 'none';
    
    try {
        const res = await fetch(API_BASE + '/candidates/' + id);
        const data = await res.json();
        
        const name = data.resume ? (data.resume.candidate_name || 'Unknown') : 'Unknown';
        document.getElementById('candidate-modal-title').textContent = escapeHtml(name);
        document.getElementById('candidate-summary').textContent = data.summary || 'No AI summary generated yet.';
    } catch (e) {
        document.getElementById('candidate-summary').textContent = 'Failed to load candidate.';
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

async function loadPipeline(candidateId) {
    const stepper = document.getElementById('pipeline-stepper');
    stepper.innerHTML = '';
    
    let completedStages = [];
    try {
        const res = await fetch(API_BASE + '/stages/candidate/' + candidateId);
        const stages = await res.json();
        completedStages = stages.map(s => s.stage);
    } catch (e) {
        console.error('Failed to load pipeline', e);
    }
    
    const isRejected = completedStages.includes('Rejected');
    const lastCompleted = completedStages.length > 0 ? completedStages[completedStages.length - 1] : null;
    
    PIPELINE_STAGES.forEach((stage, idx) => {
        const div = document.createElement('div');
        div.className = 'pipeline-step';
        
        const isCompleted = completedStages.includes(stage);
        const isActive = (lastCompleted === stage && !isRejected);
        
        if (isCompleted) div.classList.add('completed');
        if (isActive) div.classList.add('active');
        if (isRejected && stage === lastCompleted) div.classList.add('rejected');
        
        div.innerHTML = `
            <div class="step-connector"></div>
            <div class="step-dot">${isCompleted ? '<i class="fa-solid fa-check" style="font-size:0.6rem;color:white;"></i>' : (idx + 1)}</div>
            <span class="step-label">${stage}</span>
        `;
        stepper.appendChild(div);
    });
    
    if (isRejected) {
        const rejDiv = document.createElement('div');
        rejDiv.className = 'pipeline-step rejected';
        rejDiv.innerHTML = `
            <div class="step-connector"></div>
            <div class="step-dot"><i class="fa-solid fa-xmark" style="font-size:0.6rem;color:white;"></i></div>
            <span class="step-label">Rejected</span>
        `;
        stepper.appendChild(rejDiv);
    }
}

async function advanceStage() {
    if (!currentCandidateId) return;
    const stage = document.getElementById('advance-stage-select').value;
    if (!stage) { alert('Select a stage first.'); return; }
    
    const dateVal = document.getElementById('advance-stage-date').value;
    const payload = { stage: stage };
    if (dateVal) payload.scheduled_date = new Date(dateVal).toISOString();
    
    try {
        const res = await fetch(API_BASE + '/stages/candidate/' + currentCandidateId, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            loadPipeline(currentCandidateId);
            document.getElementById('advance-stage-select').value = '';
            document.getElementById('advance-stage-date').value = '';
        } else {
            const err = await res.json();
            alert('Error: ' + (err.detail || 'Could not advance stage'));
        }
    } catch (e) {
        alert('Network error advancing stage.');
        console.error(e);
    }
}

// ─── Email Generation ───────────────────────────────────────────────────────
async function generateEmail() {
    if (!currentCandidateId) return;
    const templateType = document.getElementById('email-template-select').value;
    
    try {
        const res = await fetch(API_BASE + '/email/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ candidate_id: currentCandidateId, template_type: templateType })
        });
        const data = await res.json();
        
        if (res.ok) {
            document.getElementById('email-subject').textContent = 'Subject: ' + data.subject;
            document.getElementById('email-body').textContent = data.body;
            document.getElementById('email-preview').style.display = 'block';
        } else {
            alert('Error: ' + (data.detail || 'Failed to generate email'));
        }
    } catch (e) {
        alert('Network error generating email.');
        console.error(e);
    }
}

function copyEmail() {
    const subject = document.getElementById('email-subject').textContent;
    const body = document.getElementById('email-body').textContent;
    const full = subject + '\n\n' + body;
    navigator.clipboard.writeText(full).then(() => {
        alert('Email copied to clipboard!');
    }).catch(() => {
        // Fallback
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
        const res = await fetch(API_BASE + '/agent/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                instruction: 'Run the full recruitment pipeline for job description #' + jdId + '. Rank all candidates, generate a summary for the top candidate, and generate interview questions for the top candidate.'
            })
        });
        const data = await res.json();
        
        if (res.ok) {
            alert('Full pipeline completed! ' + (data.summary || ''));
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
            html += '<div class="tool-trace"><h4><i class="fa-solid fa-wrench"></i> Actions Taken (' + data.actions.length + '):</h4>';
            data.actions.forEach(a => {
                const resultStr = JSON.stringify(a.result, null, 2);
                html += '<strong>' + escapeHtml(a.tool) + '</strong><br>' +
                    '<pre style="white-space: pre-wrap; font-size: 0.8rem; margin: 4px 0 12px 0; max-height: 150px; overflow-y: auto;">' +
                    escapeHtml(resultStr) + '</pre>';
            });
            html += '</div>';
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

// ─── Helpers ────────────────────────────────────────────────────────────────
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ─── Initialize ─────────────────────────────────────────────────────────────
checkHealth();
loadJDs();
