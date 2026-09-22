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

// ─── Notifications ────────────────────────────────────────────
let notifPanelOpen = false;

function toggleNotifPanel() {
  const panel = document.getElementById('notifPanel');
  if (!panel) return;
  notifPanelOpen = !notifPanelOpen;
  panel.style.display = notifPanelOpen ? 'block' : 'none';
}

// Close panel when clicking outside
document.addEventListener('click', e => {
  const wrap = document.getElementById('notifWrap');
  if (wrap && !wrap.contains(e.target) && notifPanelOpen) {
    notifPanelOpen = false;
    const panel = document.getElementById('notifPanel');
    if (panel) panel.style.display = 'none';
  }
});

function timeAgo(dateStr) {
  const diff = Math.floor((Date.now() - new Date(dateStr + 'Z').getTime()) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
  if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
  return Math.floor(diff / 86400) + 'd ago';
}

const NOTIF_ICONS = {
  claim_received: '📬',
  claim_approved: '✅',
  claim_rejected: '❌',
  found_match: '🔍'
};

function renderNotifications(data) {
  const badge = document.getElementById('notifBadge');
  const list = document.getElementById('notifList');
  if (!badge || !list) return;

  // Update badge
  if (data.unread > 0) {
    badge.textContent = data.unread > 9 ? '9+' : data.unread;
    badge.style.display = 'flex';
  } else {
    badge.style.display = 'none';
  }

  // Render list
  if (!data.notifications.length) {
    list.innerHTML = '<div class="notif-empty">No notifications yet</div>';
    return;
  }
  list.innerHTML = data.notifications.map(n => `
    <div class="notif-item ${n.is_read ? '' : 'unread'}" onclick="handleNotifClick(${n.id}, '${n.link || ''}')">
      <div class="notif-icon">${NOTIF_ICONS[n.type] || '🔔'}</div>
      <div class="notif-content">
        <div class="notif-msg">${n.message}</div>
        <div class="notif-time">${timeAgo(n.created_at)}</div>
      </div>
      ${n.is_read ? '' : '<div class="notif-dot"></div>'}
    </div>
  `).join('');
}

function handleNotifClick(id, link) {
  fetch(`/notifications/${id}/read`, { method: 'POST' });
  if (link) window.location.href = link;
  else { notifPanelOpen = false; document.getElementById('notifPanel').style.display = 'none'; }
  fetchNotifications();
}

function markAllRead() {
  fetch('/notifications/mark-read', { method: 'POST' })
    .then(() => fetchNotifications());
}

function fetchNotifications() {
  fetch('/notifications')
    .then(r => r.ok ? r.json() : null)
    .then(data => { if (data) renderNotifications(data); })
    .catch(() => {});
}

function initNotifications() {
  if (!document.getElementById('notifBellBtn')) return;
  fetchNotifications();
  setInterval(fetchNotifications, 30000);
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
  initImagePreview();
  initBrowseTabs();
  initNotifications();
});
