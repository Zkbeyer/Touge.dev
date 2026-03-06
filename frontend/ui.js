// ui.js — render functions
// All functions read from State and write to the DOM. No API calls here.

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmtSeconds(s) {
  s = s || 0;
  var m = Math.floor(s / 60);
  var sec = s % 60;
  return m + ':' + (sec < 10 ? '0' : '') + sec;
}

function fmtNum(n) {
  return (n || 0).toLocaleString();
}

function capFirst(s) {
  if (!s) return '';
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function animateCount(el, from, to) {
  from = from || 0;
  var start = null;
  var duration = 400;
  function step(ts) {
    if (!start) start = ts;
    var p = Math.min(1, (ts - start) / duration);
    var eased = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(from + (to - from) * eased);
    if (p < 1) requestAnimationFrame(step);
    else el.textContent = to;
  }
  requestAnimationFrame(step);
}

function floatDelta(anchorEl, deltaStr, color) {
  var rect = anchorEl.getBoundingClientRect();
  var div = document.createElement('div');
  div.style.cssText = [
    'position:fixed',
    'left:' + Math.round(rect.left + rect.width * 0.5) + 'px',
    'top:' + Math.round(rect.top) + 'px',
    'color:' + color,
    'font-family:"Bebas Neue",sans-serif',
    'font-size:22px',
    'pointer-events:none',
    'z-index:999',
    'transition:transform 1.2s ease-out,opacity 1.2s ease-out',
    'opacity:1',
    'transform:translateY(0)',
    'white-space:nowrap',
  ].join(';');
  div.textContent = deltaStr;
  document.body.appendChild(div);
  requestAnimationFrame(function () {
    div.style.transform = 'translateY(-40px)';
    div.style.opacity = '0';
  });
  setTimeout(function () { div.remove(); }, 1350);
}

// ─── Topbar ──────────────────────────────────────────────────────────────────

var _topbarPrev = {};

function renderTopbar(user) {
  if (!user) return;
  _setStatPill('sp-streak', user.streak,           user.streak + ' streak');
  _setStatPill('sp-gas',    user.gas,              user.gas + ' gas');
  _setStatPill('sp-pts',    user.total_points,     fmtNum(user.total_points) + ' pts');
  _setStatPill('sp-spend',  user.spendable_points, fmtNum(user.spendable_points) + ' spendable');
}

function _setStatPill(id, value, label) {
  var el = document.getElementById(id);
  if (!el) return;
  var prev = _topbarPrev[id];
  _topbarPrev[id] = value;

  el.textContent = label;

  if (prev !== undefined && prev !== value) {
    var delta = value - prev;
    floatDelta(el, (delta >= 0 ? '+' : '') + delta, delta >= 0 ? 'var(--green)' : 'var(--red)');
  }
}

// ─── Run Cards ───────────────────────────────────────────────────────────────

var _stopwatchInterval = null;

function renderRunCards(run, todayStatus, catchup) {
  // Track card
  var trackEl = document.getElementById('card-track');
  if (trackEl) {
    if (run && run.track) {
      trackEl.innerHTML =
        '<div class="card-track-name">' + run.track.name + '</div>' +
        '<div class="card-track-diff">' + (run.track.difficulty || '') + ' · S' + (run.track.length_days || '?') + '</div>';
    } else {
      trackEl.innerHTML = '<div class="card-track-name">Starting new run...</div>';
    }
  }

  // Stopwatch card
  var swEl = document.getElementById('card-stopwatch');
  var baseSeconds = run ? (run.stopwatch_seconds || 0) : 0;
  if (swEl) {
    swEl.innerHTML =
      '<div id="stopwatch-value">' + fmtSeconds(baseSeconds) + '</div>' +
      '<div id="stopwatch-label">stopwatch</div>';
  }

  if (_stopwatchInterval) { clearInterval(_stopwatchInterval); _stopwatchInterval = null; }
  if (todayStatus && todayStatus.qualified && !todayStatus.segment_advanced && run) {
    var swStart = Date.now();
    _stopwatchInterval = setInterval(function () {
      var valEl = document.getElementById('stopwatch-value');
      if (valEl) valEl.textContent = fmtSeconds(baseSeconds + Math.floor((Date.now() - swStart) / 1000));
    }, 1000);
  }

  // Segment card
  var seg   = run ? run.segment_index : 0;
  var total = run && run.track ? run.track.length_days : 1;
  var pct   = Math.min(100, Math.round((seg / total) * 100));
  var segEl = document.getElementById('card-segment');
  if (segEl) {
    segEl.innerHTML =
      '<div class="seg-bar-bg"><div class="seg-bar-fill" id="seg-fill" style="width:' + pct + '%"></div></div>' +
      '<div class="seg-bar-meta">' +
        '<span class="seg-label-left">Seg ' + seg + ' / ' + total + '</span>' +
        '<span class="seg-label-right">' + pct + '%</span>' +
      '</div>';
  }

  renderTodayCard(todayStatus);
  renderCatchupBanner(catchup);
}

// ─── Today Card ──────────────────────────────────────────────────────────────

function renderTodayCard(todayStatus) {
  var card    = document.getElementById('card-today');
  var header  = document.getElementById('today-header');
  var body    = document.getElementById('today-body');
  var msgEl   = document.getElementById('today-msg');
  var listEl  = document.getElementById('challenges-list');
  var actEl   = document.getElementById('today-actions');
  if (!card || !header) return;

  listEl.innerHTML = '';
  actEl.innerHTML  = '';
  msgEl.innerHTML  = '';

  if (!todayStatus) {
    header.innerHTML = '<div class="today-dot"></div><span class="today-status-text">No activity yet</span>';
    body.hidden = true;
    return;
  }

  if (todayStatus.segment_advanced) {
    header.innerHTML =
      '<div class="today-dot success"></div>' +
      '<span class="today-status-text" style="color:var(--green)">Segment complete</span>';
    body.hidden = true;
    card.classList.remove('expanded');
    setTimeout(function () {
      header.innerHTML = '<div class="today-dot"></div><span class="today-status-text">Ready for tomorrow</span>';
    }, 3200);
    return;
  }

  if (!todayStatus.qualified) {
    header.innerHTML =
      '<div class="today-dot"></div>' +
      '<span class="today-status-text">No activity today</span>' +
      '<span class="today-chevron">▼</span>';
    msgEl.innerHTML =
      '<span class="msg-warn">No commits or solutions today.</span><br>' +
      '<span style="color:var(--text3);font-size:11px">Push a commit or solve a LeetCode problem to qualify.</span>';
    body.hidden = false;
    card.classList.add('expanded');
    return;
  }

  if (todayStatus.has_challenges) {
    var count = todayStatus.challenges ? todayStatus.challenges.length : 0;
    header.innerHTML =
      '<div class="today-dot active"></div>' +
      '<span class="today-status-text">' + count + ' challenge' + (count !== 1 ? 's' : '') + ' active</span>' +
      '<span class="today-chevron">▼</span>';

    todayStatus.challenges.forEach(function (c) {
      var row = document.createElement('div');
      row.className = 'challenge-row';

      var label = capFirst(c.event_type);
      if (c.corner_type)  label += ' — ' + c.corner_type;
      if (c.weather_type) label += ' — ' + c.weather_type;
      if (c.ghost_name)   label += ' vs ' + c.ghost_name;

      var req = '';
      if (c.requirement) {
        if (typeof c.requirement === 'object') {
          req = Object.keys(c.requirement).map(function (k) { return k + ': ' + c.requirement[k]; }).join(', ');
        } else {
          req = String(c.requirement);
        }
      }
      var cur = (c.current_value !== null && c.current_value !== undefined) ? String(c.current_value) : '?';

      row.innerHTML =
        '<div class="ch-left">' +
          '<div class="ch-event-type">' + label + '</div>' +
          '<div class="ch-req-text">' + req + '</div>' +
        '</div>' +
        '<div class="ch-right">' +
          '<div class="ch-val">' + cur + '</div>' +
          (c.met ? '<div class="ch-check">✓</div>' : '') +
        '</div>';
      listEl.appendChild(row);
    });

    var btn = document.createElement('button');
    btn.className   = 'check-progress-btn';
    btn.textContent = 'Check Progress';
    btn.onclick = function () { if (typeof checkProgress === 'function') checkProgress(); };
    actEl.appendChild(btn);

    body.hidden = false;
    card.classList.add('expanded');
  } else {
    header.innerHTML =
      '<div class="today-dot active"></div>' +
      '<span class="today-status-text">Qualified — segment advances automatically</span>';
    body.hidden = true;
    card.classList.remove('expanded');
  }
}

// ─── Catchup Banner ──────────────────────────────────────────────────────────

function renderCatchupBanner(catchup) {
  var el = document.getElementById('catchup-banner');
  if (!el) return;

  if (!catchup || catchup.days_processed === 0) {
    el.classList.remove('visible');
    el.innerHTML = '';
    return;
  }

  var days = catchup.days_processed;
  el.innerHTML =
    '<span>↑ ' + days + ' day' + (days > 1 ? 's' : '') + ' caught up</span>' +
    (catchup.crashed ? '<span class="banner-crash"> — crashed</span>' : '') +
    '<button class="banner-dismiss" onclick="this.parentElement.classList.remove(\'visible\')">✕</button>';
  el.classList.add('visible');
  setTimeout(function () { el.classList.remove('visible'); }, 5000);
}

// ─── Garage ──────────────────────────────────────────────────────────────────

var _RARITY_COLORS = {
  common:    '#8a86a8',
  uncommon:  '#22c55e',
  rare:      '#60a5fa',
  epic:      '#a78bfa',
  legendary: '#c4a25a',
};

function computeUpgradeCost(rarity, currentLevel) {
  var base = [100, 200, 350, 500, 750];
  var mult = { common: 1.0, uncommon: 1.5, rare: 2.0, epic: 3.0, legendary: 5.0 };
  var cost = base[currentLevel] !== undefined ? base[currentLevel] : 750;
  var m    = mult[(rarity || 'common').toLowerCase()] || 1.0;
  return Math.round(cost * m);
}

function renderGarageScene(cars, cosmetics, activeCarId) {
  var listEl = document.getElementById('car-list');
  var cosEl  = document.getElementById('cosmetics-list');
  if (!listEl) return;

  listEl.innerHTML = '';

  if (!cars || cars.length === 0) {
    listEl.innerHTML = '<div class="empty-state">No cars owned</div>';
    if (typeof CarCanvas !== 'undefined') { CarCanvas.setRarity('common'); CarCanvas.setActive(false); }
    return;
  }

  cars.forEach(function (owned) {
    var car      = owned.car;
    var isActive = car.id === activeCarId;
    var atMax    = owned.upgrade_level >= car.max_upgrade_level;
    var cost     = atMax ? null : computeUpgradeCost(car.rarity, owned.upgrade_level);

    var div = document.createElement('div');
    div.className = 'car-list-item' + (isActive ? ' active-car' : '');

    div.innerHTML =
      '<div class="car-item-info">' +
        '<div class="car-item-name">' + car.name + '</div>' +
        '<div class="car-item-model">' + (car.base_model || '') + '</div>' +
        '<div class="car-item-meta">' +
          '<span class="rarity-badge rarity-' + (car.rarity || 'common').toLowerCase() + '">' + capFirst(car.rarity || 'common') + '</span>' +
          '<span class="lvl-badge">Lv ' + owned.upgrade_level + '/' + car.max_upgrade_level + (owned.iconic_unlocked ? ' ★' : '') + '</span>' +
          (car.perk ? '<span class="perk-badge">' + car.perk.name + (owned.perk_active ? ' ●' : '') + '</span>' : '') +
        '</div>' +
      '</div>' +
      '<div class="car-item-actions">' +
        (isActive
          ? '<span class="active-badge">Active</span>'
          : '<button class="car-btn" onclick="selectCar(\'' + owned.id + '\')">Select</button>') +
        (atMax
          ? '<span class="max-badge">Max</span>'
          : '<button class="car-btn upgrade-btn" onclick="upgradeCar(\'' + owned.id + '\')">' + (cost ? 'Upgrade (' + fmtNum(cost) + ')' : 'Upgrade') + '</button>') +
      '</div>';

    div.addEventListener('click', function () {
      if (typeof CarCanvas !== 'undefined') {
        CarCanvas.setRarity(car.rarity || 'common');
        CarCanvas.setActive(isActive);
      }
    });

    listEl.appendChild(div);

    if (isActive && typeof CarCanvas !== 'undefined') {
      CarCanvas.setRarity(car.rarity || 'common');
      CarCanvas.setActive(true);
    }
  });

  if (!cosEl) return;
  cosEl.innerHTML = '';
  if (!cosmetics || cosmetics.length === 0) {
    cosEl.innerHTML = '<div class="empty-state" style="padding:16px 0;font-size:12px">Win ghost races to earn cosmetics</div>';
    return;
  }
  cosmetics.forEach(function (c) {
    var d = document.createElement('div');
    d.className = 'cosmetic-item';
    d.innerHTML =
      '<span class="cosmetic-name">' + c.name + '</span>' +
      '<span class="cosmetic-meta">' + c.type + ' · ' + capFirst(c.rarity) + '</span>';
    cosEl.appendChild(d);
  });
}

// Keep old name as alias
var renderGaragePanel = renderGarageScene;

// ─── Inventory ────────────────────────────────────────────────────────────────

function renderInventoryScene(lootboxes) {
  var gridEl = document.getElementById('lootbox-grid');
  if (!gridEl) return;

  if (!lootboxes || lootboxes.length === 0) {
    gridEl.innerHTML =
      '<div class="empty-state">◈<br>No lootboxes<br>' +
      '<span style="font-size:11px;color:var(--text3)">Complete a run to earn one</span></div>';
    return;
  }

  gridEl.innerHTML = '';
  lootboxes.forEach(function (lb) {
    var div = document.createElement('div');
    div.className = 'lootbox-card';
    div.id = 'lb-' + lb.id;
    div.innerHTML =
      '<div class="lb-tier-badge tier-' + lb.tier + '">' + capFirst(lb.tier) + '</div>' +
      '<div class="lb-icon">◈</div>' +
      '<div class="lb-date">' + (lb.created_at || '').slice(0, 10) + '</div>' +
      '<button class="lb-open-btn" onclick="openLootbox(\'' + lb.id + '\', \'' + lb.tier + '\')">Open</button>';
    gridEl.appendChild(div);
  });
}

var renderInventoryPanel = renderInventoryScene;

// ─── Profile ─────────────────────────────────────────────────────────────────

function renderProfileScene(p) {
  if (!p) return;

  var heroEl  = document.getElementById('profile-hero');
  var statsEl = document.getElementById('profile-stats-grid');
  var pbEl    = document.getElementById('profile-pbs');

  if (heroEl) {
    heroEl.innerHTML =
      '<div class="profile-handle">' + (p.display_name || p.github_username) + '</div>' +
      '<div class="profile-github">@' + p.github_username +
        (p.leetcode_validated ? '<span class="lc-badge">LC ✓</span>' : '') +
      '</div>';
  }

  if (statsEl) {
    statsEl.innerHTML =
      _profileStat('Streak',    p.streak)         +
      _profileStat('Best',      p.longest_streak) +
      _profileStat('Gas',       p.gas)            +
      _profileStat('Pts',       fmtNum(p.total_points));
  }

  if (pbEl) {
    var stats = p.lifetime_stats || {};
    var rows = [
      ['Runs Completed',   stats.total_runs_completed   || 0],
      ['Days Qualified',   stats.total_days_qualified   || 0],
      ['Crashes',          stats.total_crashes          || 0],
      ['Gas Used',         stats.total_gas_used         || 0],
      ['Corner Saves',     stats.total_corner_saves     || 0],
      ['Weather Survived', stats.total_weather_survived || 0],
      ['Ghost Wins',       stats.total_ghost_wins       || 0],
      ['Lootboxes Opened', stats.total_lootboxes_opened || 0],
      ['Cars Owned',       stats.total_cars_owned       || 0],
    ];
    var html = '<div class="profile-divider"></div><table class="stats-table">';
    rows.forEach(function (r) { html += '<tr><td>' + r[0] + '</td><td>' + r[1] + '</td></tr>'; });
    html += '</table>';

    if (p.personal_bests && p.personal_bests.length > 0) {
      html += '<div class="section-label" style="margin-top:24px">Personal Bests</div><table class="stats-table">';
      p.personal_bests.forEach(function (pb) {
        html += '<tr><td>' + pb.track_name + '</td><td>' + pb.best_formatted + '</td></tr>';
      });
      html += '</table>';
    }
    pbEl.innerHTML = html;
  }
}

var renderProfilePanel = renderProfileScene;

function _profileStat(label, val) {
  return '<div class="profile-stat-card"><div class="profile-stat-val">' + val + '</div><div class="profile-stat-key">' + label + '</div></div>';
}

// ─── Settings ────────────────────────────────────────────────────────────────

function renderSettingsScene(me) {
  var el = document.getElementById('settings-lc');
  if (!el) return;

  var validated = me && me.leetcode_validated;
  var lcUser    = me && me.leetcode_username ? me.leetcode_username : '';

  el.innerHTML =
    '<div class="settings-section">' +
      '<div class="settings-section-label">LeetCode Integration <span class="optional-tag">(optional)</span></div>' +
      '<div class="settings-row">' +
        '<input id="lc-username-input" class="settings-input" type="text" placeholder="your-lc-username" value="' + lcUser + '">' +
        '<button class="settings-btn" onclick="saveLeetCode()">Save</button>' +
        '<button class="settings-btn danger" id="lc-remove-btn" onclick="removeLeetCode()" style="' + (validated ? '' : 'display:none') + '">Remove</button>' +
      '</div>' +
      '<div id="lc-status" class="settings-status' + (validated ? ' ok' : '') + '">' +
        (validated ? 'Validated: ' + lcUser : 'Not connected') +
      '</div>' +
    '</div>';
}

var renderSettingsPanel = renderSettingsScene;

// ─── Dev Panel ───────────────────────────────────────────────────────────────

var _devRendered = false;

function renderDevPanel() {
  if (_devRendered) return;
  _devRendered = true;
  var el = document.getElementById('dev-controls');
  if (!el) return;

  el.innerHTML =
    '<div class="dev-section">' +
      '<button class="dev-action-btn danger" onclick="devResetAccount()">Reset Account</button>' +
    '</div>' +

    '<div class="dev-section">' +
      '<div class="dev-label">Process Day (inject + game loop)</div>' +
      '<div class="dev-row">' +
        '<label class="dev-field">commits<input id="dev-commits" type="number" value="1" min="0"></label>' +
        '<label class="dev-field">lc easy<input id="dev-lc-easy" type="number" value="0" min="0"></label>' +
        '<label class="dev-field">lc med<input id="dev-lc-med" type="number" value="0" min="0"></label>' +
        '<label class="dev-field">lc hard<input id="dev-lc-hard" type="number" value="0" min="0"></label>' +
        '<button class="dev-action-btn" onclick="devProcessDay()">Process Day</button>' +
      '</div>' +
    '</div>' +

    '<div class="dev-section">' +
      '<div class="dev-label">Fast Forward</div>' +
      '<div class="dev-row">' +
        '<label class="dev-field">days<input id="dev-ff-days" type="number" value="3" min="1" max="60"></label>' +
        '<button class="dev-action-btn" onclick="devFastForward()">Fast Forward</button>' +
      '</div>' +
    '</div>' +

    '<div class="dev-section">' +
      '<div class="dev-row">' +
        '<button class="dev-action-btn" onclick="devSkipToCompletion()">Skip to Completion</button>' +
        '<button class="dev-action-btn danger" onclick="devForceCrash()">Force Crash</button>' +
      '</div>' +
    '</div>' +

    '<div class="dev-section">' +
      '<div class="dev-label">Give Gas</div>' +
      '<div class="dev-row">' +
        '<label class="dev-field">amount<input id="dev-gas-amount" type="number" value="1" min="1"></label>' +
        '<button class="dev-action-btn" onclick="devGiveGas()">Give Gas</button>' +
      '</div>' +
    '</div>' +

    '<div class="dev-section">' +
      '<div class="dev-label">Give Points</div>' +
      '<div class="dev-row">' +
        '<label class="dev-field">amount<input id="dev-pts-amount" type="number" value="500" min="1"></label>' +
        '<button class="dev-action-btn" onclick="devGivePoints()">Give Points</button>' +
      '</div>' +
    '</div>' +

    '<div class="dev-section">' +
      '<div class="dev-label">Give Lootbox</div>' +
      '<div class="dev-row">' +
        '<select id="dev-lb-tier" class="dev-select">' +
          '<option value="bronze">Bronze</option>' +
          '<option value="silver">Silver</option>' +
          '<option value="gold" selected>Gold</option>' +
          '<option value="platinum">Platinum</option>' +
        '</select>' +
        '<button class="dev-action-btn" onclick="devGiveLootbox()">Give Lootbox</button>' +
      '</div>' +
    '</div>' +

    '<div class="dev-section">' +
      '<div class="dev-row">' +
        '<button class="dev-action-btn" onclick="devLoadStateDump()">Load State Dump</button>' +
      '</div>' +
    '</div>';
}

// Keep old alias
var renderHUD = renderTopbar;
var renderRunOverlay = renderRunCards;
var renderTodayPanel = renderTodayCard;
