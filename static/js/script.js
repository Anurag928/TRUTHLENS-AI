document.addEventListener('DOMContentLoaded', () => {
    setupThemeToggle();
    setupPointerGlow();
    setupMobileNav();
    setupReveal();
    setupPasswordToggle();
    setupUploadModule();
    setupProcessingFlow();
    setupOTP();
});

function setupThemeToggle() {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    
    // Theme logic is executed early to avoid flash, but we bind buttons here
    const saved = localStorage.getItem('theme') || 'dark';
    btn.textContent = saved === 'light' ? '🌙' : '☀️';

    btn.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme') || 'dark';
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        btn.textContent = next === 'light' ? '🌙' : '☀️';
    });
}

function setupPointerGlow() {
    const glow = document.querySelector('.app-bg-glow');
    if (!glow) {
        return;
    }

    window.addEventListener('pointermove', (event) => {
        glow.style.setProperty('--mx', `${event.clientX}px`);
        glow.style.setProperty('--my', `${event.clientY}px`);
    }, { passive: true });
}

function setupMobileNav() {
    const toggle = document.querySelector('[data-nav-toggle]');
    const menu = document.querySelector('[data-mobile-menu]');

    if (!toggle || !menu) {
        return;
    }

    toggle.addEventListener('click', () => {
        const isOpen = menu.classList.toggle('open');
        toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
}

function setupReveal() {
    const nodes = document.querySelectorAll('.reveal');
    if (!nodes.length) {
        return;
    }

    const obs = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                obs.unobserve(entry.target);
            }
        });
    }, {
        rootMargin: '0px 0px -10% 0px',
        threshold: 0.2
    });

    nodes.forEach((node, idx) => {
        node.style.transitionDelay = `${Math.min(idx * 70, 260)}ms`;
        obs.observe(node);
    });
}

function setupPasswordToggle() {
    document.querySelectorAll('[data-password-toggle]').forEach((btn) => {
        btn.addEventListener('click', () => {
            const inputId = btn.getAttribute('data-password-toggle');
            const input = document.getElementById(inputId);
            if (!input) {
                return;
            }

            const visible = input.type === 'text';
            input.type = visible ? 'password' : 'text';
            btn.textContent = visible ? 'Show' : 'Hide';
        });
    });
}

function setupUploadModule() {
    const uploadInput = document.getElementById('video_file');
    const uploadZone = document.querySelector('[data-upload-zone]');
    const fileTag = document.querySelector('[data-file-tag]');
    const preview = document.getElementById('video-preview');
    const progressBar = document.querySelector('[data-upload-progress]');
    const removeBtn = document.querySelector('[data-remove-file]');

    if (!uploadInput || !uploadZone) {
        return;
    }

    const showFile = (file) => {
        if (!file) {
            return;
        }

        if (fileTag) {
            const mb = (file.size / 1024 / 1024).toFixed(2);
            fileTag.textContent = `${file.name} (${mb} MB)`;
            fileTag.parentElement.hidden = false;
        }

        if (preview) {
            const url = URL.createObjectURL(file);
            preview.src = url;
            preview.parentElement.hidden = false;
            preview.onloadeddata = () => URL.revokeObjectURL(url);
        }

        if (progressBar) {
            let progress = 0;
            progressBar.style.setProperty('--p', '0%');
            const timer = setInterval(() => {
                progress += 12;
                progressBar.style.setProperty('--p', `${Math.min(progress, 100)}%`);
                if (progress >= 100) {
                    clearInterval(timer);
                }
            }, 80);
        }
    };

    const clearFile = () => {
        uploadInput.value = '';
        if (fileTag) {
            fileTag.textContent = '';
            fileTag.parentElement.hidden = true;
        }
        if (preview) {
            preview.removeAttribute('src');
            preview.parentElement.hidden = true;
        }
        if (progressBar) {
            progressBar.style.setProperty('--p', '0%');
        }
    };

    ['dragenter', 'dragover'].forEach((eventName) => {
        uploadZone.addEventListener(eventName, (event) => {
            event.preventDefault();
            uploadZone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach((eventName) => {
        uploadZone.addEventListener(eventName, (event) => {
            event.preventDefault();
            uploadZone.classList.remove('dragover');
        });
    });

    uploadZone.addEventListener('drop', (event) => {
        const file = event.dataTransfer && event.dataTransfer.files ? event.dataTransfer.files[0] : null;
        if (!file) {
            return;
        }

        const dt = new DataTransfer();
        dt.items.add(file);
        uploadInput.files = dt.files;
        showFile(file);
    });

    uploadInput.addEventListener('change', () => {
        const file = uploadInput.files && uploadInput.files[0] ? uploadInput.files[0] : null;
        if (file) {
            showFile(file);
        }
    });

    if (removeBtn) {
        removeBtn.addEventListener('click', (event) => {
            event.preventDefault();
            clearFile();
        });
    }
}

function setupProcessingFlow() {
    const wrap = document.querySelector('[data-processing]');
    if (!wrap) {
        return;
    }

    const labels = [
        'Extracting frames',
        'Detecting facial regions',
        'Analyzing inconsistencies',
        'Evaluating temporal behavior',
        'Finalizing authenticity score'
    ];

    const steps = Array.from(document.querySelectorAll('.timeline-step'));
    const labelNode = document.querySelector('[data-processing-label]');
    const progressBar = document.querySelector('[data-processing-progress]');
    const redirect = wrap.getAttribute('data-redirect');
    let idx = 0;

    const tick = () => {
        if (labelNode) {
            labelNode.textContent = labels[idx] || labels[labels.length - 1];
        }

        steps.forEach((step, stepIdx) => {
            step.classList.toggle('active', stepIdx <= idx);
        });

        if (progressBar) {
            const percent = Math.min(Math.round(((idx + 1) / labels.length) * 100), 100);
            progressBar.style.setProperty('--p', `${percent}%`);
        }

        idx += 1;
        if (idx >= labels.length) {
            window.setTimeout(() => {
                if (redirect) {
                    window.location.href = redirect;
                }
            }, 600);
            return;
        }

        window.setTimeout(tick, 980);
    };

    window.setTimeout(tick, 500);
}

function setupOTP() {
    const inputs = document.querySelectorAll('.otp-digit');
    const hiddenOtp = document.getElementById('otp');
    const form = document.getElementById('otp-form');

    if (!inputs.length || !hiddenOtp) return;

    function updateHiddenOTP() {
        let otpValue = '';
        inputs.forEach(input => {
            otpValue += input.value;
        });
        hiddenOtp.value = otpValue;
    }

    inputs.forEach((input, index) => {
        // Select text automatically on focus so next keystroke overwrites it
        input.addEventListener('focus', (e) => {
            e.target.select();
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace') {
                if (e.target.value === '' && index > 0) {
                    inputs[index - 1].focus();
                    inputs[index - 1].value = ''; 
                    updateHiddenOTP();
                }
            } else if (e.key >= '0' && e.key <= '9') {
                e.preventDefault();
                e.target.value = e.key;
                if (index < inputs.length - 1) {
                    inputs[index + 1].focus();
                    inputs[index + 1].select();
                }
                updateHiddenOTP();
            } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
                // Prevent non-numeric characters completely
                e.preventDefault();
            }
        });

        // Fallback for mobile virtual keyboards where keydown doesn't always provide e.key
        input.addEventListener('input', (e) => {
            let val = e.target.value.replace(/\\D/g, ''); // strip non-digits
            if (val.length > 1) {
                val = val.slice(-1);
            }
            e.target.value = val;
            
            if (val !== '') {
                if (index < inputs.length - 1) {
                    inputs[index + 1].focus();
                }
            }
            updateHiddenOTP();
        });
        
        // Handle pasting a full code
        input.addEventListener('paste', (e) => {
            e.preventDefault();
            const pastedData = e.clipboardData.getData('text').replace(/\\D/g, '').slice(0, inputs.length);
            
            // clear out inputs from current index
            for (let i = index; i < inputs.length; i++) {
                inputs[i].value = '';
            }
            
            for (let i = 0; i < pastedData.length; i++) {
                if (index + i < inputs.length) {
                    inputs[index + i].value = pastedData[i];
                }
            }
            
            if (index + pastedData.length < inputs.length) {
                inputs[index + pastedData.length].focus();
            } else {
                inputs[inputs.length - 1].focus();
            }
            updateHiddenOTP();
        });
    });

    if (form) {
        form.addEventListener('submit', () => {
            updateHiddenOTP();
        });
    }
}