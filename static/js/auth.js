(function () {
  function attachPasswordToggle(toggleId, inputId) {
    var toggle = document.getElementById(toggleId);
    var input = document.getElementById(inputId);
    if (!toggle || !input) return;

    toggle.addEventListener('click', function (event) {
      event.preventDefault();
      var isPassword = input.type === 'password';
      input.type = isPassword ? 'text' : 'password';
      toggle.innerHTML = '<i class="fas ' + (isPassword ? 'fa-eye-slash' : 'fa-eye') + '"></i>';
      toggle.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
    });
  }

  function initSignupStrength() {
    var input = document.getElementById('password1');
    var strengthFill = document.getElementById('passwordStrengthFill');
    var strengthText = document.getElementById('passwordStrengthText');
    if (!input || !strengthFill || !strengthText) return;

    function evaluate(value) {
      var score = 0;
      if (value.length >= 8) score += 1;
      if (/[A-Z]/.test(value)) score += 1;
      if (/[a-z]/.test(value)) score += 1;
      if (/\d/.test(value)) score += 1;
      if (/[^A-Za-z0-9]/.test(value)) score += 1;
      return score;
    }

    function render(score, hasValue) {
      var width = 18;
      var text = 'Use at least 8 characters with mixed case, a number, and a symbol.';
      var gradient = 'linear-gradient(90deg, #ef4444, #f59e0b)';

      if (!hasValue) {
        width = 18;
      } else if (score <= 2) {
        width = 34;
        text = 'Weak password. Add length, uppercase letters, numbers, and symbols.';
      } else if (score <= 4) {
        width = 68;
        text = 'Good start. Add one more complexity factor for stronger protection.';
        gradient = 'linear-gradient(90deg, #f59e0b, #2f80ed)';
      } else {
        width = 100;
        text = 'Strong password. This meets enterprise-grade complexity standards.';
        gradient = 'linear-gradient(90deg, #10b981, #14b8a6)';
      }

      strengthFill.style.width = width + '%';
      strengthFill.style.background = gradient;
      strengthText.textContent = text;
    }

    render(0, false);
    input.addEventListener('input', function () {
      var value = input.value || '';
      render(evaluate(value), value.length > 0);
    });
  }

  function initLoginAttemptFlag() {
    var loginForm = document.getElementById('loginForm');
    if (!loginForm) return;

    loginForm.addEventListener('submit', function () {
      sessionStorage.setItem('truthlens_login_attempt', '1');
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    attachPasswordToggle('togglePassword', 'password');
    attachPasswordToggle('togglePassword1', 'password1');
    attachPasswordToggle('togglePassword2', 'password2');
    initSignupStrength();
    initLoginAttemptFlag();
  });
})();
