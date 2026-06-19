/* ============================
   VidSave Pro - Main JavaScript
   ============================ */

// ===== HEADER SCROLL =====
const header = document.getElementById('header');
if (header) {
  window.addEventListener('scroll', () => {
    if (window.scrollY > 20) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }
  });
}

// ===== HAMBURGER MENU =====
const hamburger = document.getElementById('hamburger');
const mobileMenu = document.getElementById('mobile-menu');
if (hamburger && mobileMenu) {
  hamburger.addEventListener('click', () => {
    mobileMenu.classList.toggle('open');
    const spans = hamburger.querySelectorAll('span');
    if (mobileMenu.classList.contains('open')) {
      spans[0].style.transform = 'rotate(45deg) translateY(7px)';
      spans[1].style.opacity = '0';
      spans[2].style.transform = 'rotate(-45deg) translateY(-7px)';
    } else {
      spans[0].style.transform = '';
      spans[1].style.opacity = '';
      spans[2].style.transform = '';
    }
  });

  // Close on outside click
  document.addEventListener('click', (e) => {
    if (!hamburger.contains(e.target) && !mobileMenu.contains(e.target)) {
      mobileMenu.classList.remove('open');
      const spans = hamburger.querySelectorAll('span');
      spans[0].style.transform = '';
      spans[1].style.opacity = '';
      spans[2].style.transform = '';
    }
  });
}

// ===== BACK TO TOP =====
const backToTop = document.getElementById('back-to-top');
if (backToTop) {
  window.addEventListener('scroll', () => {
    if (window.scrollY > 400) {
      backToTop.classList.add('visible');
    } else {
      backToTop.classList.remove('visible');
    }
  });
}

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ===== TOAST =====
function showToast(msg, duration = 3000) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), duration);
}

// ===== CLIPBOARD PASTE =====
async function pasteFromClipboard() {
  try {
    const text = await navigator.clipboard.readText();
    const input = document.getElementById('video-url-input');
    if (input) {
      input.value = text;
      input.focus();
      showToast('✅ URL pasted from clipboard');
    }
  } catch (e) {
    showToast('⚠️ Could not access clipboard. Please paste manually.');
  }
}

// ===== FAQ TOGGLE =====
function toggleFaq(btn) {
  const item = btn.parentElement;
  const isOpen = item.classList.contains('open');

  // Close all
  document.querySelectorAll('.faq-item.open').forEach(i => i.classList.remove('open'));

  // Open clicked (if it was closed)
  if (!isOpen) {
    item.classList.add('open');
  }
}

// ===== PLATFORM TABS =====
const ptabs = document.querySelectorAll('.ptab');
if (ptabs.length) {
  ptabs.forEach(tab => {
    tab.addEventListener('click', () => {
      ptabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const platform = tab.dataset.platform;
      const input = document.getElementById('video-url-input');
      const placeholders = {
        youtube: 'Paste YouTube URL here... (e.g., https://www.youtube.com/watch?v=...)',
        facebook: 'Paste Facebook video URL here...',
        instagram: 'Paste Instagram video/reel URL here...',
        tiktok: 'Paste TikTok video URL here...',
        twitter: 'Paste Twitter/X video URL here...',
        vimeo: 'Paste Vimeo video URL here...'
      };
      if (input && placeholders[platform]) {
        input.placeholder = placeholders[platform];
      }
    });
  });
}

// ===== SCROLL ANIMATIONS =====
const observerOptions = {
  threshold: 0.1,
  rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.style.opacity = '1';
      entry.target.style.transform = 'translateY(0)';
      observer.unobserve(entry.target);
    }
  });
}, observerOptions);

// Animate elements on scroll
document.querySelectorAll('.feature-card, .platform-card, .step-card, .conv-card, .faq-item, .alt-card').forEach((el, i) => {
  el.style.opacity = '0';
  el.style.transform = 'translateY(30px)';
  el.style.transition = `opacity 0.5s ease ${i * 0.05}s, transform 0.5s ease ${i * 0.05}s, border-color 0.25s, background 0.25s, box-shadow 0.25s`;
  observer.observe(el);
});

// ===== QUICK FILTER =====
function setQuickFilter(type) {
  const input = document.getElementById('video-url-input');
  if (input) {
    input.focus();
    const messages = {
      mp4: 'Paste a YouTube URL to download as MP4',
      shorts: 'Paste a YouTube Shorts URL to download',
      mp3: 'Paste a YouTube URL to convert to MP3'
    };
    showToast(`🎬 ${messages[type] || 'Paste a video URL below'}`);
  }
}

// ===== LANGUAGE CHANGE =====
function changeLanguage(select) {
  showToast(`🌐 Language switched to ${select.options[select.selectedIndex].text}`);
}

// ===== SMOOTH NAVIGATION HIGHLIGHT =====
window.addEventListener('load', () => {
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.remove('active');
    const href = link.getAttribute('href');
    if (href === currentPage || (currentPage === '' && href === 'index.html')) {
      link.classList.add('active');
    }
  });
});

// ===== COPY URL HELPER =====
function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast('✅ Copied to clipboard!');
  });
}
