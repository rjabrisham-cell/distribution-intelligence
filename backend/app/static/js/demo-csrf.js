// Synchronizer token is checked server-side against the authenticated session.
(() => {
  const token = document.cookie.split('; ').find(x => x.startsWith('dip_csrf='))?.split('=')[1];
  if (!token) return;
  document.querySelectorAll('form').forEach(form => {
    if ((form.method || '').toLowerCase() !== 'post' || new URL(form.action, location.href).origin !== location.origin) return;
    const field = document.createElement('input');
    field.type = 'hidden'; field.name = 'csrf_token'; field.value = decodeURIComponent(token);
    form.appendChild(field);
    const action = new URL(form.action, location.href);
    if (!/^\/projects\/\d+\/(matching\/rerun|readiness(?:\/refresh)?)$/.test(action.pathname)) return;
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (form.dataset.submitting === 'true') return;
      form.dataset.submitting = 'true';
      const buttons = Array.from(form.querySelectorAll('button[type="submit"],button:not([type]),input[type="submit"]'));
      buttons.forEach(button => { button.disabled = true; });
      form.setAttribute('aria-busy', 'true');
      let navigating = false;
      let alert = document.querySelector('[data-operation-alert]');
      if (!alert) {
        alert = document.createElement('div'); alert.dataset.operationAlert = '';
        alert.setAttribute('role', 'alert'); alert.tabIndex = -1;
        alert.style.cssText = 'padding:16px;margin-bottom:20px;border-radius:12px;background:#fff7ed;color:#9a3412';
        document.getElementById('main-content').prepend(alert);
      }
      alert.hidden = true;
      try {
        const response = await fetch(action.href, {method:'POST', body:new FormData(form), credentials:'same-origin', headers:{'Accept':'text/html'}});
        if (response.ok) {
          navigating = true;
          location.assign(response.redirected ? response.url : action.pathname.replace(/\/(matching\/rerun|readiness\/refresh)$/, '/readiness'));
          return;
        }
        const documentResult = new DOMParser().parseFromString(await response.text(), 'text/html');
        alert.textContent = documentResult.querySelector('[data-web-error]')?.textContent || 'درخواست انجام نشد. وضعیت حساب و اطلاعات فرم را بررسی کنید.';
      } catch (_) {
        alert.textContent = 'ارتباط برقرار نشد. چند لحظه بعد وضعیت را بررسی کنید.';
      } finally {
        if (!navigating) {
          form.dataset.submitting = 'false'; form.removeAttribute('aria-busy');
          buttons.forEach(button => { button.disabled = false; });
          alert.hidden = false; alert.focus();
        }
      }
    });
  });
  const result = document.querySelector('[data-trial-result]');
  window.addEventListener('pageshow', () => {
    document.querySelectorAll('form[data-submitting="true"]').forEach(form => {
      form.dataset.submitting = 'false'; form.removeAttribute('aria-busy');
      form.querySelectorAll('button[type="submit"],button:not([type]),input[type="submit"]').forEach(button => { button.disabled = false; });
    });
  });
  if (result && document.visibilityState === 'visible') {
    fetch(result.dataset.trialResult, {method: 'POST', headers: {'X-CSRF-Token': decodeURIComponent(token)}, body: new URLSearchParams({receipt: result.dataset.receipt}), credentials: 'same-origin'});
  }
})();
