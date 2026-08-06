/**
 * Journey Stepper — Presentation Logic v2.0
 * Phase B-03
 *
 * Reads:  data-stage-state  (completed | current | pending | locked)
 *         data-stage-url     (URL string or null)
 * Applies CSS classes: ds-stage--{state}
 * Enables navigation for completed/current stages with a valid URL.
 *
 * No business logic. No stage mapping. No hardcoded values.
 */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {

    var stages = document.querySelectorAll('[data-stage-id]');
    if (!stages || stages.length === 0) {
      return;
    }

    var currentFound = false;

    stages.forEach(function (stage) {

      // ── 1. Read attributes ──────────────────────────────────
      var state = stage.getAttribute('data-stage-state');
      var url   = stage.getAttribute('data-stage-url');

      // ── 2. Null Safety: missing state → skip silently ──────
      if (!state) {
        return;
      }

      // ── 3. Duplicate current detection ──────────────────────
      if (state === 'current') {
        if (currentFound) {
          // Demote second (and any later) current to pending
          state = 'pending';
        } else {
          currentFound = true;
        }
      }

      // ── 4. Normalise state ──────────────────────────────────
      var VALID_STATES = ['completed', 'current', 'pending', 'locked'];
      if (VALID_STATES.indexOf(state) === -1) {
        state = 'pending';           // unknown → fallback
      }

      // ── 5. Apply CSS class ──────────────────────────────────
      stage.classList.add('ds-stage--' + state);

      // ── 6. Navigation: completed / current with valid URL ──
      if ((state === 'completed' || state === 'current') && url) {
        stage.setAttribute('role', 'link');
        stage.setAttribute('tabindex', '0');
        stage.style.cursor = 'pointer';

        stage.addEventListener('click', function () {
          window.location.href = url;
        });

        stage.addEventListener('keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            window.location.href = url;
          }
        });
      }

      // ── 7. Accessibility: locked state ──────────────────────
      if (state === 'locked') {
        stage.setAttribute('aria-disabled', 'true');
      }

    });

  });
})();
