// Synchronizer token is checked server-side against the authenticated session.
(() => {
  const token = document.cookie.split('; ').find(x => x.startsWith('dip_csrf='))?.split('=')[1];
  if (!token) return;
  document.querySelectorAll('form').forEach(form => {
    if ((form.method || '').toLowerCase() !== 'post' || new URL(form.action, location.href).origin !== location.origin) return;
    const field = document.createElement('input');
    field.type = 'hidden'; field.name = 'csrf_token'; field.value = decodeURIComponent(token);
    form.appendChild(field);
  });
  const result = document.querySelector('[data-trial-result]');
  if (result && document.visibilityState === 'visible') {
    fetch(result.dataset.trialResult, {method: 'POST', headers: {'X-CSRF-Token': decodeURIComponent(token)}, body: new URLSearchParams({receipt: result.dataset.receipt}), credentials: 'same-origin'});
  }
})();
