(function () {
  'use strict';

  function csrf() {
    var meta = document.querySelector('meta[name="oy-csrf"]');
    return meta ? meta.getAttribute('content') : '';
  }

  function ensureCsrf(form) {
    if (!form || String(form.method || 'get').toLowerCase() !== 'post') return;
    var input = form.querySelector('input[name="csrf_token"]');
    if (!input) {
      input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'csrf_token';
      form.appendChild(input);
    }
    input.value = csrf();
  }

  document.addEventListener('submit', function (event) {
    ensureCsrf(event.target);
  }, true);

  document.body.addEventListener('htmx:configRequest', function (event) {
    if (String(event.detail.verb || '').toLowerCase() === 'post') {
      event.detail.parameters.csrf_token = csrf();
    }
  });

  var filter = 'open';
  function applyFilter() {
    document.querySelectorAll('[data-filter]').forEach(function (button) {
      button.classList.toggle('active', button.dataset.filter === filter);
    });
    document.querySelectorAll('.shopping-item.done').forEach(function (row) {
      row.hidden = filter === 'open';
    });
    document.querySelectorAll('.shopping-section').forEach(function (section) {
      var visible = Array.from(section.querySelectorAll('.shopping-item')).some(function (row) { return !row.hidden; });
      section.hidden = !visible;
    });
  }

  document.addEventListener('click', function (event) {
    var button = event.target.closest('[data-filter]');
    if (!button) return;
    filter = button.dataset.filter || 'open';
    applyFilter();
  });

  document.body.addEventListener('htmx:afterSwap', function () {
    applyFilter();
  });

  applyFilter();
})();
