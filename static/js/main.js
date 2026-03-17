// ─── Sidebar Toggle ───────────────────────────────────────────
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  if (sidebar) sidebar.classList.toggle('open');
  if (overlay) overlay.classList.toggle('open');
}

// ─── Auto-dismiss Toasts ──────────────────────────────────────
(function () {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const toasts = container.querySelectorAll('.toast');
  toasts.forEach((t, i) => {
    setTimeout(() => {
      t.style.opacity = '0';
      t.style.transform = 'translateX(20px)';
      t.style.transition = 'opacity .3s, transform .3s';
      setTimeout(() => t.remove(), 320);
    }, 3500 + i * 400);
  });
})();

// ─── Hosteler Toggle ─────────────────────────────────────────
function initHostelerToggle() {
  const statusInput = document.getElementById('hostelerStatus');
  const hostelGroup = document.getElementById('hostelGroup');
  const hostelInput = document.getElementById('hostelName');
  const btns = document.querySelectorAll('[data-hosteler]');
  if (!btns.length) return;

  btns.forEach(btn => {
    btn.addEventListener('click', () => {
      btns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const val = btn.dataset.hosteler;
      if (statusInput) statusInput.value = val;
      if (hostelGroup) {
        hostelGroup.style.display = val === 'Hosteler' ? 'block' : 'none';
        if (hostelInput) hostelInput.required = val === 'Hosteler';
      }
    });
  });
}

// ─── Image Preview ────────────────────────────────────────────
function initImagePreview() {
  const input = document.getElementById('imageInput');
  const preview = document.getElementById('imagePreview');
  const previewImg = preview ? preview.querySelector('img') : null;
  const drop = document.querySelector('.file-drop');

  if (!input || !preview || !previewImg) return;

  input.addEventListener('change', () => {
    const file = input.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = e => {
        previewImg.src = e.target.result;
        preview.style.display = 'block';
      };
      reader.readAsDataURL(file);
    }
  });

  if (drop) {
    drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('dragover'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('dragover'));
    drop.addEventListener('drop', e => {
      e.preventDefault();
      drop.classList.remove('dragover');
      if (e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        input.dispatchEvent(new Event('change'));
      }
    });
  }
}

// ─── Browse Tabs ──────────────────────────────────────────────
function initBrowseTabs() {
  const tabs = document.querySelectorAll('.tab-btn');
  const lostSection = document.getElementById('lostSection');
  const foundSection = document.getElementById('foundSection');
  if (!tabs.length) return;

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const target = tab.dataset.tab;
      if (lostSection) lostSection.style.display = target === 'lost' ? 'block' : 'none';
      if (foundSection) foundSection.style.display = target === 'found' ? 'block' : 'none';
    });
  });
}

// ─── Confirm Delete ───────────────────────────────────────────
document.addEventListener('click', e => {
  if (e.target.closest('[data-confirm]')) {
    const msg = e.target.closest('[data-confirm]').dataset.confirm;
    if (!confirm(msg || 'Are you sure?')) e.preventDefault();
  }
});

// ─── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initHostelerToggle();
  initImagePreview();
  initBrowseTabs();
});
