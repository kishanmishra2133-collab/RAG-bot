/**
 * Document Q&A RAG Chatbot — Client Application & Ambient Canvas
 * 
 * Includes:
 * 1. Ambient Particle Background: Interactive canvas with velocity-oriented elongated particles
 * 2. Session Management: Ephemeral client UUID lifecycle
 * 3. Document Ingestion: Drag-and-drop / file selector with inline processing state
 * 4. Grounded Chat: Conversational stream, typing indicator, and source citations
 */

document.addEventListener('DOMContentLoaded', () => {
  // =========================================================================
  // 1. Ambient Interactive Particle Canvas
  // =========================================================================
  const canvas = document.getElementById('particle-canvas');
  const ctx = canvas.getContext('2d');

  let width = 0;
  let height = 0;
  let particles = [];
  
  // Interaction state
  const mouse = {
    x: -9999,
    y: -9999,
    targetRadius: 130,
    isActive: false
  };

  function resizeCanvas() {
    const dpr = window.devicePixelRatio || 1;
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.scale(dpr, dpr);
    initParticles();
  }

  // Particle representation: elongated soft capsules oriented along velocity
  class Particle {
    constructor() {
      this.reset(true);
    }

    reset(initial = false) {
      this.x = Math.random() * width;
      this.y = initial ? Math.random() * height : -10;
      // Slow, calm ambient drift
      this.vx = (Math.random() - 0.5) * 0.35;
      this.vy = 0.25 + Math.random() * 0.45;
      this.baseLength = 5 + Math.random() * 7;
      this.width = 1.4 + Math.random() * 0.8;
      // Soft periwinkle/light-blue palette (HSL 225-235, low-medium saturation)
      this.alpha = 0.25 + Math.random() * 0.45;
      this.hue = 220 + Math.random() * 20;
    }

    update() {
      // Gentle cursor interaction: subtle repulsion/nudge
      if (mouse.isActive) {
        const dx = this.x - mouse.x;
        const dy = this.y - mouse.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < mouse.targetRadius && dist > 1) {
          const force = (1 - dist / mouse.targetRadius) * 0.08;
          this.vx += (dx / dist) * force;
          this.vy += (dy / dist) * force;
        }
      }

      // Air resistance / damping back toward ambient drift
      this.vx *= 0.98;
      this.vy = this.vy * 0.98 + 0.007; // Natural gentle downward bias

      this.x += this.vx;
      this.y += this.vy;

      // Wrap-around bounds
      if (this.y > height + 20) {
        this.y = -10;
        this.x = Math.random() * width;
      }
      if (this.x < -20) this.x = width + 10;
      if (this.x > width + 20) this.x = -10;
    }

    draw() {
      const speed = Math.sqrt(this.vx * this.vx + this.vy * this.vy);
      const angle = Math.atan2(this.vy, this.vx);
      const length = Math.max(this.baseLength, this.baseLength * (speed * 1.5));

      ctx.save();
      ctx.translate(this.x, this.y);
      ctx.rotate(angle);

      // Draw rounded elongated capsule
      ctx.beginPath();
      ctx.fillStyle = `hsla(${this.hue}, 80%, 75%, ${this.alpha})`;
      ctx.roundRect(-length / 2, -this.width / 2, length, this.width, this.width / 2);
      ctx.fill();

      ctx.restore();
    }
  }

  function initParticles() {
    // Particle count scaled moderately by viewport size (cap between 60 and 110)
    const count = Math.min(110, Math.max(55, Math.floor((width * height) / 14000)));
    particles = [];
    for (let i = 0; i < count; i++) {
      particles.push(new Particle());
    }
  }

  window.addEventListener('mousemove', (e) => {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
    mouse.isActive = true;
  });

  window.addEventListener('mouseleave', () => {
    mouse.isActive = false;
  });

  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  function animateParticles() {
    ctx.clearRect(0, 0, width, height);
    for (let i = 0; i < particles.length; i++) {
      particles[i].update();
      particles[i].draw();
    }
    requestAnimationFrame(animateParticles);
  }
  requestAnimationFrame(animateParticles);

  // =========================================================================
  // 2. Session Management
  // =========================================================================
  function getOrCreateSessionId() {
    let sid = sessionStorage.getItem('rag_session_id');
    if (!sid) {
      if (typeof crypto.randomUUID === 'function') {
        sid = crypto.randomUUID();
      } else {
        sid = 'sess_' + Math.random().toString(36).substring(2, 11) + Date.now().toString(36);
      }
      sessionStorage.setItem('rag_session_id', sid);
    }
    return sid;
  }

  let currentSessionId = getOrCreateSessionId();
  let uploadedDocuments = [];
  let conversationHistory = [];

  const sessionIdDisplay = document.getElementById('session-id-display');
  const btnResetSession = document.getElementById('btn-reset-session');
  const docCounter = document.getElementById('doc-counter');
  const docList = document.getElementById('doc-list');
  const docEmptyState = document.getElementById('doc-empty-state');
  const uploadAlert = document.getElementById('upload-alert');

  function updateSessionDisplay() {
    const shortSid = currentSessionId.length > 12 
      ? currentSessionId.substring(0, 8) + '...' + currentSessionId.substring(currentSessionId.length - 4)
      : currentSessionId;
    sessionIdDisplay.textContent = `Session: ${shortSid}`;
  }
  updateSessionDisplay();

  async function resetSession() {
    if (confirm('Start a new session? This will clear all uploaded documents and conversation history from memory.')) {
      try {
        await fetch(`/session/${currentSessionId}`, { method: 'DELETE' });
      } catch (e) {
        // Ignore network errors on reset
      }
      sessionStorage.removeItem('rag_session_id');
      currentSessionId = getOrCreateSessionId();
      uploadedDocuments = [];
      conversationHistory = [];
      updateSessionDisplay();
      renderDocumentList();
      resetChatUI();
    }
  }
  btnResetSession.addEventListener('click', resetSession);

  // =========================================================================
  // 3. Document Ingestion & Uploads
  // =========================================================================
  const dropzone = document.getElementById('upload-dropzone');
  const fileInput = document.getElementById('file-input');
  const chatInput = document.getElementById('chat-input');
  const btnSend = document.getElementById('btn-send');

  dropzone.addEventListener('click', () => fileInput.click());

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('drag-over');
  });

  ['dragleave', 'dragend'].forEach(evt => {
    dropzone.addEventListener(evt, () => dropzone.classList.remove('drag-over'));
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('drag-over');
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files && fileInput.files.length > 0) {
      handleFiles(Array.from(fileInput.files));
      fileInput.value = '';
    }
  });

  function showUploadAlert(msg) {
    uploadAlert.textContent = msg;
    uploadAlert.classList.remove('hidden');
    setTimeout(() => {
      uploadAlert.classList.add('hidden');
    }, 6000);
  }

  function getFileExtension(filename) {
    return filename.split('.').pop().toLowerCase();
  }

  async function handleFiles(files) {
    if (!files.length) return;

    const allowed = ['pdf', 'docx', 'txt', 'md'];
    const validFiles = [];
    const invalidFiles = [];

    files.forEach(f => {
      const ext = getFileExtension(f.name);
      if (allowed.includes(ext)) {
        validFiles.push(f);
      } else {
        invalidFiles.push(f.name);
      }
    });

    if (invalidFiles.length > 0) {
      showUploadAlert(`Unsupported format: ${invalidFiles.join(', ')}. Only .pdf, .docx, .txt, .md allowed.`);
    }

    if (validFiles.length === 0) return;

    // Add temporary processing rows
    validFiles.forEach(f => {
      addProcessingRow(f.name);
    });

    const formData = new FormData();
    formData.append('session_id', currentSessionId);
    validFiles.forEach(f => formData.append('files', f));

    try {
      const resp = await fetch('/upload', {
        method: 'POST',
        body: formData
      });

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || `Upload failed with HTTP ${resp.status}`);
      }

      const data = await resp.json();

      // Check for individual file failures
      const failed = data.processed_files.filter(p => p.status === 'failed');
      if (failed.length > 0) {
        const reasons = failed.map(f => `${f.filename} (${f.error})`).join('; ');
        showUploadAlert(`Some files failed: ${reasons}`);
      }

      uploadedDocuments = data.documents;
      renderDocumentList();
      updateChatInputState();
    } catch (err) {
      showUploadAlert(`Error uploading documents: ${err.message}`);
      // Refresh current session docs from server
      fetchSessionInfo();
    }
  }

  function addProcessingRow(filename) {
    docEmptyState.style.display = 'none';
    const ext = getFileExtension(filename);

    const row = document.createElement('div');
    row.className = 'doc-row processing';
    row.id = `proc-${filename.replace(/[^a-zA-Z0-9]/g, '_')}`;
    row.innerHTML = `
      <div class="doc-info">
        <span class="doc-tag ${ext}">${ext}</span>
        <span class="doc-name">${escapeHtml(filename)}</span>
      </div>
      <div class="doc-spinner" title="Extracting text & computing embeddings..."></div>
    `;
    docList.appendChild(row);
  }

  function renderDocumentList() {
    docList.innerHTML = '';

    if (uploadedDocuments.length === 0) {
      docList.appendChild(docEmptyState);
      docEmptyState.style.display = 'flex';
      docCounter.textContent = '0 docs';
      return;
    }

    docEmptyState.style.display = 'none';
    docCounter.textContent = `${uploadedDocuments.length} doc${uploadedDocuments.length > 1 ? 's' : ''}`;

    uploadedDocuments.forEach(doc => {
      const ext = getFileExtension(doc.filename);
      const row = document.createElement('div');
      row.className = 'doc-row';
      row.innerHTML = `
        <div class="doc-info">
          <span class="doc-tag ${ext}">${ext}</span>
          <span class="doc-name" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</span>
          <span class="doc-meta">${doc.chunk_count} chunks</span>
        </div>
      `;
      docList.appendChild(row);
    });
  }

  async function fetchSessionInfo() {
    try {
      const resp = await fetch(`/session/${currentSessionId}`);
      if (resp.ok) {
        const data = await resp.json();
        uploadedDocuments = data.documents;
        renderDocumentList();
        updateChatInputState();
      }
    } catch (e) {
      // Offline / server reboot
    }
  }
  fetchSessionInfo();

  // =========================================================================
  // 4. Grounded Chat Interface
  // =========================================================================
  const chatMessages = document.getElementById('chat-messages');
  const chatEmptyState = document.getElementById('chat-empty-state');
  const chatForm = document.getElementById('chat-form');

  function updateChatInputState() {
    const hasDocs = uploadedDocuments.length > 0;
    chatInput.disabled = !hasDocs;
    btnSend.disabled = !hasDocs || !chatInput.value.trim();

    if (hasDocs) {
      chatInput.placeholder = 'Ask a question about your uploaded documents...';
    } else {
      chatInput.placeholder = 'Upload a document first to start chatting...';
    }
  }

  // Auto-resize textarea
  chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
    btnSend.disabled = uploadedDocuments.length === 0 || !chatInput.value.trim();
  });

  // Enter to send, Shift+Enter for newline
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!btnSend.disabled) {
        chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
      }
    }
  });

  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const question = chatInput.value.trim();
    if (!question || uploadedDocuments.length === 0) return;

    // 1. Append User Message
    chatInput.value = '';
    chatInput.style.height = 'auto';
    btnSend.disabled = true;
    chatInput.disabled = true;

    if (chatEmptyState && chatEmptyState.parentNode) {
      chatEmptyState.remove();
    }

    appendMessage('user', question);
    conversationHistory.push({ role: 'user', content: question });

    // 2. Show Typing Indicator
    const typingRow = showTypingIndicator();
    scrollChatToBottom();

    // 3. Request Grounded Answer
    try {
      const resp = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: currentSessionId,
          question: question,
          history: conversationHistory.slice(0, -1) // Exclude current question turn
        })
      });

      typingRow.remove();

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error (${resp.status})`);
      }

      const data = await resp.json();
      appendMessage('assistant', data.answer, data.sources);
      conversationHistory.push({ role: 'assistant', content: data.answer });
    } catch (err) {
      typingRow.remove();
      appendMessage('assistant', `Error: ${err.message}`, []);
    } finally {
      chatInput.disabled = false;
      chatInput.focus();
      btnSend.disabled = !chatInput.value.trim();
      scrollChatToBottom();
    }
  });

  function appendMessage(role, text, sources = []) {
    const row = document.createElement('div');
    row.className = `message-row ${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = text;
    row.appendChild(bubble);

    if (role === 'assistant' && sources && sources.length > 0) {
      const sourcesDiv = document.createElement('div');
      sourcesDiv.className = 'message-sources';
      sourcesDiv.innerHTML = `
        <span class="sources-label">Sources:</span>
        <span class="sources-list">${sources.map(s => escapeHtml(s)).join(', ')}</span>
      `;
      row.appendChild(sourcesDiv);
    }

    chatMessages.appendChild(row);
    scrollChatToBottom();
  }

  function showTypingIndicator() {
    const row = document.createElement('div');
    row.className = 'typing-indicator-row';
    row.innerHTML = `
      <div class="typing-bubble">
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
      </div>
    `;
    chatMessages.appendChild(row);
    return row;
  }

  function scrollChatToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function resetChatUI() {
    chatMessages.innerHTML = '';
    chatMessages.appendChild(chatEmptyState);
    updateChatInputState();
  }

  // =========================================================================
  // 5. Mobile Toggle
  // =========================================================================
  const mobileToggleBtn = document.getElementById('mobile-toggle-btn');
  const documentsPanel = document.getElementById('documents-panel');
  const mobileToggleLabel = document.getElementById('mobile-toggle-label');

  if (mobileToggleBtn) {
    mobileToggleBtn.addEventListener('click', () => {
      const isCollapsed = documentsPanel.classList.toggle('collapsed');
      mobileToggleLabel.textContent = isCollapsed ? 'Show' : 'Hide';
    });
  }

  // Utility helper for safe HTML text rendering
  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
});
