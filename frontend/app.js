'use strict';

// ─── Token ───────────────────────────────────────────────────────────────────
function getToken()   { return localStorage.getItem('mps_token'); }
function setToken(t)  { localStorage.setItem('mps_token', t); }
function clearToken() { localStorage.removeItem('mps_token'); }

// ─── API ─────────────────────────────────────────────────────────────────────
async function apiFetch(path, opts) {
  opts = opts || {};
  var token   = getToken();
  var headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
  if (token) headers['Authorization'] = 'Bearer ' + token;

  var res = await fetch(path, Object.assign({}, opts, { headers: headers }));

  if (res.status === 401) {
    clearToken();
    showBoot();
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    var detail = 'HTTP ' + res.status;
    try { var body = await res.json(); detail = body.detail || JSON.stringify(body); } catch (_) {}
    throw new Error(detail);
  }

  var ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) return res.json();
  return null;
}

// ─── Toast ───────────────────────────────────────────────────────────────────
function toast(msg, type, duration) {
  type     = type     || 'ok';
  duration = duration || 3000;

  var container = document.getElementById('toast-container');
  var div = document.createElement('div');
  div.className   = 'toast toast-' + type;
  div.textContent = msg;
  container.appendChild(div);

  requestAnimationFrame(function () { div.classList.add('visible'); });
  setTimeout(function () {
    div.classList.remove('visible');
    setTimeout(function () { div.remove(); }, 320);
  }, duration);
}

// ─── Scene management ────────────────────────────────────────────────────────
var _activeScene = 'run';

function _openScene(el) {
  el.style.display = 'flex';
  el.getBoundingClientRect(); // force reflow
  el.style.transition    = 'opacity 250ms ease, transform 250ms ease';
  el.style.opacity       = '1';
  el.style.transform     = 'scale(1)';
  el.style.pointerEvents = 'auto';
}

function _closeScene(el) {
  if (el.style.display === 'none') return;
  el.style.transition    = 'opacity 200ms ease, transform 200ms ease';
  el.style.opacity       = '0';
  el.style.transform     = 'scale(0.97)';
  el.style.pointerEvents = 'none';
  setTimeout(function () {
    el.style.display = 'none';
  }, 210);
}

function showScene(name) {
  var prev = _activeScene;
  _activeScene = name;

  document.querySelectorAll('.nav-btn').forEach(function (btn) {
    btn.classList.toggle('active', btn.dataset.scene === name);
  });

  if (name === 'run') {
    document.querySelectorAll('.scene').forEach(function (s) { _closeScene(s); });
    MountainCanvas.resume();
    MountainCanvas.setSpeed(State.todayStatus && State.todayStatus.qualified ? 2 : 0.5);
    return;
  }

  MountainCanvas.pause();

  // Close previous scene
  if (prev !== 'run') {
    var prevEl = document.getElementById('scene-' + prev);
    if (prevEl) _closeScene(prevEl);
  }

  var targetEl = document.getElementById('scene-' + name);
  if (!targetEl) return;
  _openScene(targetEl);

  if      (name === 'garage')    loadGarage();
  else if (name === 'inventory') loadInventory();
  else if (name === 'profile')   loadProfile();
  else if (name === 'settings')  loadSettings();
  else if (name === 'dev')       { renderDevPanel(); document.getElementById('dev-dump').textContent = ''; }
}

// ─── Boot ────────────────────────────────────────────────────────────────────
function showBoot() {
  var boot = document.getElementById('boot-screen');
  boot.style.display       = 'flex';
  boot.style.opacity       = '1';
  boot.style.pointerEvents = 'auto';
  BootCanvas.start();
}

function hideBoot() {
  var boot = document.getElementById('boot-screen');
  boot.style.transition    = 'opacity 0.6s ease';
  boot.style.opacity       = '0';
  boot.style.pointerEvents = 'none';
  BootCanvas.stop();
  setTimeout(function () { boot.style.display = 'none'; }, 640);
}

// ─── Init ────────────────────────────────────────────────────────────────────
async function onLoad() {
  var params   = new URLSearchParams(window.location.search);
  var urlToken = params.get('token');
  var isNew    = params.get('new_user') === '1';

  if (urlToken) {
    setToken(urlToken);
    history.replaceState(null, '', window.location.pathname);
  }

  MountainCanvas.init(document.getElementById('mountain-canvas'));

  if (!getToken()) {
    showBoot();
    return;
  }

  hideBoot();
  await initApp(isNew && !!urlToken);
}

async function initApp(isNew) {
  await loadRun();
  loadInventoryBadge();

  if (isNew) {
    setTimeout(function () { toast('Welcome — AE86 awarded', 'ok', 5000); }, 1200);
  }

  setInterval(function () {
    if (_activeScene === 'run') silentRefreshRun();
  }, 60000);
}

// ─── Run ─────────────────────────────────────────────────────────────────────
async function loadRun() {
  try {
    var data = await apiFetch('/run');
    setState({ user: data.user, run: data.run, todayStatus: data.today_status, catchup: data.catchup_summary });
    renderTopbar(State.user);
    renderRunCards(State.run, State.todayStatus, State.catchup);
    MountainCanvas.setTrackName(State.run && State.run.track ? State.run.track.name : '');
    MountainCanvas.setSpeed(State.todayStatus && State.todayStatus.qualified ? 2 : 0.5);
  } catch (e) {
    if (e.message !== 'Unauthorized') toast('Connection failed', 'err');
  }
}

async function silentRefreshRun() {
  try {
    var data = await apiFetch('/run');
    setState({ user: data.user, run: data.run, todayStatus: data.today_status, catchup: data.catchup_summary });
    renderTopbar(State.user);
    renderRunCards(State.run, State.todayStatus, State.catchup);
    MountainCanvas.setTrackName(State.run && State.run.track ? State.run.track.name : '');
    MountainCanvas.setSpeed(State.todayStatus && State.todayStatus.qualified ? 2 : 0.5);
  } catch (_) {}
}

async function checkProgress() {
  try {
    var prevStop = State.run ? State.run.stopwatch_seconds : 0;
    var data = await apiFetch('/run/process', { method: 'POST' });
    setState({ user: data.user, run: data.run, todayStatus: data.today_status, catchup: data.catchup_summary });
    renderTopbar(State.user);
    renderRunCards(State.run, State.todayStatus, State.catchup);

    if (data.today_status && data.today_status.segment_advanced) {
      var delta = (data.run ? data.run.stopwatch_seconds : 0) - prevStop;
      var swEl  = document.getElementById('stopwatch-value');
      if (swEl) floatDelta(swEl, (delta >= 0 ? '+' : '') + delta + 's', delta >= 0 ? 'var(--green)' : 'var(--red)');

      var fillEl = document.getElementById('seg-fill');
      if (fillEl) {
        fillEl.style.transition = 'border-color 0.3s ease';
        fillEl.style.outline = '1px solid var(--green)';
        setTimeout(function () { fillEl.style.outline = ''; }, 700);
      }
      toast('Segment advanced!', 'ok');
    }
  } catch (e) {
    if (e.message !== 'Unauthorized') toast(e.message, 'err');
  }
}

// ─── Inventory ───────────────────────────────────────────────────────────────
async function loadInventory() {
  var gridEl = document.getElementById('lootbox-grid');
  if (gridEl) gridEl.innerHTML = '<p class="loading">Loading...</p>';

  try {
    var boxes = await apiFetch('/inventory/lootboxes');
    setState({ inventory: boxes });
    renderInventoryScene(boxes);
    _updateInvBadge(boxes.length);
  } catch (e) {
    if (e.message !== 'Unauthorized') toast(e.message, 'err');
  }
}

async function loadInventoryBadge() {
  try {
    var boxes = await apiFetch('/inventory/lootboxes');
    setState({ inventory: boxes });
    _updateInvBadge(boxes.length);
  } catch (_) {}
}

function _updateInvBadge(count) {
  var el = document.getElementById('inv-badge');
  if (el) el.textContent = count > 0 ? count : '';
}

async function openLootbox(id, tier) {
  var modal      = document.getElementById('modal');
  var modalRes   = document.getElementById('modal-result');
  var modalClose = document.getElementById('modal-close');
  var lbCanvas   = document.getElementById('lootbox-canvas');

  modal.hidden      = false;
  modalRes.hidden   = true;
  modalClose.hidden = true;

  LootboxCanvas.init(lbCanvas);
  LootboxCanvas.setTier(tier || 'bronze');

  var apiPromise = apiFetch('/inventory/lootboxes/' + id + '/open', { method: 'POST' });

  setTimeout(function () {
    LootboxCanvas.crack(function () {
      apiPromise.then(function (result) {
        var msg = '';
        if (result.type === 'car') {
          msg = '<div class="reward-title">' + result.car_name + '</div>' +
                '<div class="reward-rarity rarity-' + (result.rarity || '').toLowerCase() + '">' + capFirst(result.rarity || '') + '</div>';
        } else if (result.type === 'duplicate_points') {
          msg = '<div class="reward-title">Duplicate</div><div class="reward-sub">+' + result.points + ' pts</div>';
        } else {
          msg = '<div class="reward-title">+' + (result.points || 0) + ' pts</div>';
        }
        modalRes.innerHTML = msg;
        modalRes.hidden    = false;
        modalClose.hidden  = false;

        loadInventory();
        if (result.type === 'car') loadGarage();
        silentRefreshRun();
      }).catch(function (e) {
        modalRes.innerHTML = '<div style="color:var(--red)">' + e.message + '</div>';
        modalRes.hidden    = false;
        modalClose.hidden  = false;
      });
    });
  }, 1500);
}

// ─── Garage ──────────────────────────────────────────────────────────────────
async function loadGarage() {
  var listEl = document.getElementById('car-list');
  if (listEl) listEl.innerHTML = '<p class="loading">Loading...</p>';

  try {
    var results = await Promise.all([
      apiFetch('/garage/cars'),
      apiFetch('/garage/cosmetics'),
      apiFetch('/auth/me'),
    ]);
    var cars = results[0], cosmetics = results[1], me = results[2];
    setState({ garage: { cars: cars, cosmetics: cosmetics, activeCarId: me.active_car_id } });
    renderGarageScene(cars, cosmetics, me.active_car_id);

    setTimeout(function () {
      var carCanvas = document.getElementById('car-canvas');
      if (carCanvas) CarCanvas.init(carCanvas);
    }, 100);
  } catch (e) {
    if (e.message !== 'Unauthorized') toast(e.message, 'err');
  }
}

async function selectCar(ownershipId) {
  try {
    await apiFetch('/garage/cars/' + ownershipId + '/select', { method: 'POST' });
    toast('Active car updated', 'ok');
    loadGarage();
  } catch (e) {
    toast(e.message, 'err');
  }
}

async function upgradeCar(ownershipId) {
  try {
    var result = await apiFetch('/garage/cars/' + ownershipId + '/upgrade', { method: 'POST' });
    toast('Upgraded to Lv ' + result.new_level + ' — cost: ' + result.cost_paid + ' pts', 'ok');
    var spendEl = document.getElementById('sp-spend');
    if (spendEl) floatDelta(spendEl, '-' + result.cost_paid, 'var(--red)');
    loadGarage();
    silentRefreshRun();
  } catch (e) {
    toast(e.message, 'err');
  }
}

// ─── Profile ─────────────────────────────────────────────────────────────────
async function loadProfile() {
  var heroEl = document.getElementById('profile-hero');
  if (heroEl) heroEl.innerHTML = '<p class="loading">Loading...</p>';

  try {
    var p = await apiFetch('/profile');
    setState({ profile: p });
    renderProfileScene(p);
  } catch (e) {
    if (e.message !== 'Unauthorized') toast(e.message, 'err');
  }
}

// ─── Settings ────────────────────────────────────────────────────────────────
async function loadSettings() {
  try {
    var me = await apiFetch('/auth/me');
    renderSettingsScene(me);
  } catch (e) {
    if (e.message !== 'Unauthorized') toast(e.message, 'err');
  }
}

async function saveLeetCode() {
  var input    = document.getElementById('lc-username-input');
  var statusEl = document.getElementById('lc-status');
  if (!input || !input.value.trim()) return;

  if (statusEl) { statusEl.textContent = 'Validating...'; statusEl.className = 'settings-status'; }
  try {
    var res = await apiFetch('/settings/leetcode', {
      method: 'PUT',
      body:   JSON.stringify({ username: input.value.trim() }),
    });
    if (statusEl) { statusEl.textContent = 'Validated: ' + res.username; statusEl.className = 'settings-status ok'; }
    var removeBtn = document.getElementById('lc-remove-btn');
    if (removeBtn) removeBtn.style.display = '';
    toast('LeetCode saved', 'ok');
  } catch (e) {
    if (statusEl) { statusEl.textContent = e.message; statusEl.className = 'settings-status err'; }
  }
}

async function removeLeetCode() {
  try {
    await apiFetch('/settings/leetcode', { method: 'DELETE' });
    var input     = document.getElementById('lc-username-input');
    var statusEl  = document.getElementById('lc-status');
    var removeBtn = document.getElementById('lc-remove-btn');
    if (input)     input.value = '';
    if (statusEl)  { statusEl.textContent = 'Removed'; statusEl.className = 'settings-status'; }
    if (removeBtn) removeBtn.style.display = 'none';
    toast('LeetCode removed', 'ok');
  } catch (e) {
    toast(e.message, 'err');
  }
}

// ─── Dev panel ───────────────────────────────────────────────────────────────
async function _devAction(path, body, successMsg) {
  try {
    var result = await apiFetch(path, {
      method: 'POST',
      body:   body !== undefined ? JSON.stringify(body) : undefined,
    });
    var dump = document.getElementById('dev-dump');
    if (dump) dump.textContent = JSON.stringify(result, null, 2);
    toast(successMsg, 'ok');
    silentRefreshRun().then(function () { renderTopbar(State.user); });
    loadInventoryBadge();
    return result;
  } catch (e) {
    var dump = document.getElementById('dev-dump');
    if (dump) dump.textContent = JSON.stringify({ error: e.message }, null, 2);
    toast(e.message, 'err');
    return null;
  }
}

async function devResetAccount() {
  if (!confirm('Reset all game data? This cannot be undone.')) return;
  var result = await _devAction('/test/user/reset', undefined, 'Account reset');
  if (result) loadRun();
}

async function devProcessDay() {
  var body = {
    commits:   parseInt(document.getElementById('dev-commits').value)  || 0,
    lc_easy:   parseInt(document.getElementById('dev-lc-easy').value)  || 0,
    lc_medium: parseInt(document.getElementById('dev-lc-med').value)   || 0,
    lc_hard:   parseInt(document.getElementById('dev-lc-hard').value)  || 0,
  };
  var result = await _devAction('/test/run/process-day', body, 'Day processed');
  if (result) {
    if (_activeScene === 'run') loadRun();
    if (result.summary && result.summary.crashed) crashFlash();
  }
}

async function devFastForward() {
  var days   = parseInt(document.getElementById('dev-ff-days').value) || 1;
  var result = await _devAction('/test/run/fast-forward', { days: days, commits_per_day: 1 }, 'Fast forward ' + days + ' days');
  if (result && _activeScene === 'run') loadRun();
}

async function devSkipToCompletion() {
  var result = await _devAction('/test/run/skip-to-completion', undefined, 'Skipped to completion');
  if (result && _activeScene === 'run') loadRun();
}

async function devForceCrash() {
  if (!confirm('Force crash? Streak will reset to 0.')) return;
  var result = await _devAction('/test/run/force-crash', undefined, 'Crash forced');
  if (result) { crashFlash(); loadRun(); }
}

async function devGiveGas() {
  var amount = parseInt(document.getElementById('dev-gas-amount').value) || 1;
  await _devAction('/test/user/give-gas', { amount: amount }, '+' + amount + ' gas');
}

async function devGivePoints() {
  var amount = parseInt(document.getElementById('dev-pts-amount').value) || 500;
  await _devAction('/test/user/give-points', { amount: amount }, '+' + amount + ' points');
}

async function devGiveLootbox() {
  var tier = document.getElementById('dev-lb-tier').value;
  await _devAction('/test/inventory/give-lootbox', { tier: tier, count: 1 }, 'Lootbox (' + tier + ') awarded');
}

async function devLoadStateDump() {
  try {
    var data = await apiFetch('/test/state');
    var dump = document.getElementById('dev-dump');
    if (dump) dump.textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    toast(e.message, 'err');
  }
}

// ─── Effects ─────────────────────────────────────────────────────────────────
function crashFlash() {
  var div = document.createElement('div');
  div.style.cssText = [
    'position:fixed', 'inset:0', 'background:rgba(200,16,46,0.35)',
    'z-index:9999', 'pointer-events:none',
    'transition:opacity 0.6s ease-out', 'opacity:0.35',
  ].join(';');
  document.body.appendChild(div);
  requestAnimationFrame(function () {
    div.style.opacity = '0';
    setTimeout(function () { div.remove(); }, 650);
  });
}

// ─── Auth ────────────────────────────────────────────────────────────────────
function logout() {
  clearToken();
  showBoot();
}

// ─── DOMContentLoaded ────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  // Scene close buttons
  document.querySelectorAll('.scene-close-btn').forEach(function (btn) {
    btn.addEventListener('click', function () { showScene('run'); });
  });

  // Nav buttons
  document.querySelectorAll('.nav-btn').forEach(function (btn) {
    btn.addEventListener('click', function () { showScene(btn.dataset.scene); });
  });

  // Today header — toggle expand
  var todayHeader = document.getElementById('today-header');
  if (todayHeader) {
    todayHeader.addEventListener('click', function () {
      var card = document.getElementById('card-today');
      var body = document.getElementById('today-body');
      if (!body || body.hidden) return; // no content to expand
      card.classList.toggle('expanded');
    });
  }

  // Modal close
  var modalClose = document.getElementById('modal-close');
  if (modalClose) {
    modalClose.addEventListener('click', function () {
      document.getElementById('modal').hidden = true;
    });
  }

  onLoad();
});
