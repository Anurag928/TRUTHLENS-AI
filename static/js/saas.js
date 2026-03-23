(function () {
  function debounce(fn, delay) {
    var timer;
    return function () {
      var args = arguments;
      clearTimeout(timer);
      timer = setTimeout(function () {
        fn.apply(null, args);
      }, delay);
    };
  }

  function ensureToastStack() {
    var stack = document.getElementById('toastStack');
    if (stack) return stack;
    stack = document.createElement('div');
    stack.id = 'toastStack';
    stack.className = 'toast-stack';
    document.body.appendChild(stack);
    return stack;
  }

  function showToast(message, type, timeout) {
    var stack = ensureToastStack();
    var toast = document.createElement('div');
    var tone = type || 'success';
    toast.className = 'toast toast-' + tone;
    toast.innerHTML =
      '<div class="toast-icon"><i class="fas ' + (tone === 'success' ? 'fa-circle-check' : 'fa-circle-info') + '"></i></div>' +
      '<div class="toast-content">' + message + '</div>' +
      '<button class="toast-close" type="button" aria-label="Dismiss notification"><i class="fas fa-xmark"></i></button>';
    stack.appendChild(toast);

    var clear = function () {
      if (!toast.parentNode) return;
      toast.classList.add('toast-hide');
      setTimeout(function () {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast);
        }
      }, 240);
    };

    var closeBtn = toast.querySelector('.toast-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', clear);
    }
    setTimeout(clear, timeout || 3200);
  }

  function toggleTheme() {
    var body = document.body;
    var next = body.classList.contains('light') ? 'dark' : 'light';
    if (next === 'light') {
      body.classList.add('light');
    } else {
      body.classList.remove('light');
    }
    localStorage.setItem('saas_theme', next);
    syncThemeIcon();
  }

  function syncThemeIcon() {
    var icon = document.getElementById('themeIcon');
    if (!icon) return;
    var isLight = document.body.classList.contains('light');
    icon.className = isLight ? 'fas fa-sun' : 'fas fa-moon';
  }

  function initTheme() {
    var saved = localStorage.getItem('saas_theme');
    if (!saved) {
      var preferLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
      saved = preferLight ? 'light' : 'dark';
    }
    if (saved === 'light') {
      document.body.classList.add('light');
    } else {
      document.body.classList.remove('light');
    }
    syncThemeIcon();
  }

  function initMobileNav() {
    var btn = document.getElementById('mobileNavToggle');
    var menu = document.getElementById('mobileNav');
    if (!btn || !menu) return;
    btn.addEventListener('click', function () {
      menu.classList.toggle('show');
    });

    document.addEventListener('click', function (evt) {
      if (!menu.classList.contains('show')) return;
      if (menu.contains(evt.target) || btn.contains(evt.target)) return;
      menu.classList.remove('show');
    });

    menu.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        menu.classList.remove('show');
      });
    });
  }

  function setupDropzone(fileInputId, zoneId) {
    var input = document.getElementById(fileInputId);
    var zone = document.getElementById(zoneId);
    if (!input || !zone) return;

    ['dragenter', 'dragover'].forEach(function (evtName) {
      zone.addEventListener(evtName, function (evt) {
        evt.preventDefault();
        zone.classList.add('drag-over');
      });
    });

    ['dragleave', 'drop'].forEach(function (evtName) {
      zone.addEventListener(evtName, function (evt) {
        evt.preventDefault();
        zone.classList.remove('drag-over');
      });
    });

    zone.addEventListener('drop', function (evt) {
      if (!evt.dataTransfer || !evt.dataTransfer.files || !evt.dataTransfer.files.length) return;
      input.files = evt.dataTransfer.files;
      input.dispatchEvent(new Event('change'));
    });
  }

  function ensureFieldMessage(input) {
    if (!input || !input.parentNode) return null;

    // Reuse a single helper node for each field to avoid duplicate messages
    // when inputs are wrapped (for example password + visibility toggle).
    var messageKey = input.id || input.name;
    var searchRoot = input.closest('.form-row') || input.parentNode;
    if (messageKey && searchRoot && searchRoot.querySelector) {
      var existingByKey = searchRoot.querySelector('.field-message[data-for="' + messageKey + '"]');
      if (existingByKey) return existingByKey;
    }

    var next = input.nextElementSibling;
    if (next && next.classList && next.classList.contains('field-message')) {
      return next;
    }

    var existingInParent = input.parentNode.querySelector && input.parentNode.querySelector('.field-message');
    if (existingInParent) return existingInParent;

    var msg = document.createElement('div');
    msg.className = 'field-message';
    if (messageKey) {
      msg.setAttribute('data-for', messageKey);
    }

    // Place helper text below the whole row for wrapped inputs.
    if (searchRoot && searchRoot !== input.parentNode) {
      searchRoot.appendChild(msg);
    } else {
      input.parentNode.appendChild(msg);
    }

    return msg;
  }

  function getFieldError(input) {
    if (!input) return '';
    if (input.validity.valueMissing) {
      return 'This field is required.';
    }
    if (input.type === 'email' && input.validity.typeMismatch) {
      return 'Please enter a valid email address.';
    }
    if (input.id === 'password1' && input.value && input.value.length < 8) {
      return 'Use at least 8 characters.';
    }
    if (input.id === 'password2') {
      var p1 = document.getElementById('password1');
      if (p1 && input.value && p1.value !== input.value) {
        return 'Passwords do not match.';
      }
    }
    return '';
  }

  function syncFieldState(input) {
    if (!input || !input.classList) return;
    var messageEl = ensureFieldMessage(input);
    var error = getFieldError(input);

    input.classList.remove('is-invalid', 'is-valid');
    if (!input.value) {
      if (messageEl) {
        messageEl.textContent = '';
        messageEl.classList.remove('error');
      }
      return;
    }

    if (error) {
      input.classList.add('is-invalid');
      if (messageEl) {
        messageEl.textContent = error;
        messageEl.classList.add('error');
      }
      return;
    }

    input.classList.add('is-valid');
    if (messageEl) {
      messageEl.textContent = '';
      messageEl.classList.remove('error');
    }
  }

  function saveDraft(form, storageKey) {
    if (!form) return;
    var draft = {};
    form.querySelectorAll('input[name], textarea[name]').forEach(function (field) {
      if (!field.name || field.type === 'password' || field.type === 'file' || field.type === 'checkbox') return;
      draft[field.name] = field.value || '';
    });
    sessionStorage.setItem(storageKey, JSON.stringify(draft));
  }

  function restoreDraft(form, storageKey) {
    if (!form) return;
    var raw = sessionStorage.getItem(storageKey);
    if (!raw) return;
    try {
      var draft = JSON.parse(raw);
      Object.keys(draft).forEach(function (name) {
        var field = form.querySelector('[name="' + name + '"]');
        if (field && !field.value) {
          field.value = draft[name];
          syncFieldState(field);
        }
      });
    } catch (e) {
      sessionStorage.removeItem(storageKey);
    }
  }

  function initAuthForm(formId, storageKey) {
    var form = document.getElementById(formId);
    if (!form) return;

    var submitBtn = form.querySelector('button[type="submit"]');
    if (!submitBtn) return;

    restoreDraft(form, storageKey);

    var saveDraftDebounced = debounce(function () {
      saveDraft(form, storageKey);
    }, 120);

    form.querySelectorAll('input, textarea').forEach(function (field) {
      field.addEventListener('input', function () {
        syncFieldState(field);
        saveDraftDebounced();
      });
      field.addEventListener('blur', function () {
        syncFieldState(field);
      });
    });

    form.addEventListener('submit', function (event) {
      if (form.dataset.submitting === '1') {
        event.preventDefault();
        return;
      }

      var hasError = false;
      form.querySelectorAll('input, textarea').forEach(function (field) {
        syncFieldState(field);
        if (field.classList.contains('is-invalid')) {
          hasError = true;
        }
      });

      if (hasError || !form.checkValidity()) {
        event.preventDefault();
        form.querySelectorAll(':invalid').forEach(function (field) {
          syncFieldState(field);
        });
        return;
      }

      form.dataset.submitting = '1';
      submitBtn.disabled = true;
      submitBtn.setAttribute('aria-busy', 'true');
      submitBtn.classList.add('btn-loading');
      submitBtn.dataset.originalText = submitBtn.innerHTML;
      submitBtn.innerHTML = submitBtn.getAttribute('data-loading-label') || 'Processing';
      saveDraft(form, storageKey);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    initTheme();
    initMobileNav();

    var themeButton = document.getElementById('themeToggle');
    if (themeButton) {
      themeButton.addEventListener('click', toggleTheme);
    }

    setupDropzone('videoUpload', 'uploadDropzone');
    setupDropzone('video_file', 'uploadDropzone');

    initAuthForm('loginForm', 'truthlens_login_draft');
    initAuthForm('signupForm', 'truthlens_signup_draft');

    if (!window.location.pathname.includes('/login')) {
      var attemptedLogin = sessionStorage.getItem('truthlens_login_attempt');
      if (attemptedLogin === '1') {
        sessionStorage.removeItem('truthlens_login_attempt');
        sessionStorage.removeItem('truthlens_login_draft');
        sessionStorage.removeItem('truthlens_signup_draft');
        showToast('Logged in successfully', 'success', 3400);
      }
    }
  });
})();
