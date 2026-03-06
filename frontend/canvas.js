// canvas.js — Canvas 2D viewports
// API designed as a drop-in surface for Three.js later.

// ─── MountainCanvas ──────────────────────────────────────────────────────────
var MountainCanvas = (function () {
  var canvas, ctx;
  var w, h;
  var animId;
  var paused = false;
  var currentSpeed = 0;
  var targetSpeed = 0;
  var trackName = '';

  // Road path: array of {x, y} control points (relative 0-1)
  var roadPoints = [
    { x: 0.50, y: 1.0 },
    { x: 0.48, y: 0.80 },
    { x: 0.44, y: 0.65 },
    { x: 0.46, y: 0.52 },
    { x: 0.42, y: 0.42 },
    { x: 0.45, y: 0.34 },
  ];
  // Car position along road (0-1)
  var carT = 0;
  var stars = [];

  function init(el) {
    canvas = el;
    ctx = canvas.getContext('2d');
    _resize();
    window.addEventListener('resize', _resize);
    _loop();
  }

  function _resize() {
    w = canvas.width  = window.innerWidth;
    h = canvas.height = window.innerHeight;
    _buildStars();
  }

  function _buildStars() {
    stars = [];
    for (var i = 0; i < 80; i++) {
      stars.push({
        x:    Math.random() * w,
        y:    Math.random() * h * 0.55,
        r:    Math.random() * 1.2 + 0.3,
        a:    Math.random() * 0.3 + 0.3,
      });
    }
  }

  function _draw() {
    currentSpeed += (targetSpeed - currentSpeed) * 0.04;

    // Sky
    var sky = ctx.createLinearGradient(0, 0, 0, h * 0.72);
    sky.addColorStop(0, '#0b0b0f');
    sky.addColorStop(1, '#1c1420');
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, w, h);

    // Stars
    stars.forEach(function (s) {
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(255,250,240,' + s.a + ')';
      ctx.fill();
    });

    // Moon — top right
    var mx = w * 0.82, my = h * 0.14, mr = 28;
    var moonGlow = ctx.createRadialGradient(mx, my, mr * 0.5, mx, my, mr * 2.4);
    moonGlow.addColorStop(0, 'rgba(255,250,240,0.12)');
    moonGlow.addColorStop(1, 'rgba(255,250,240,0)');
    ctx.fillStyle = moonGlow;
    ctx.beginPath();
    ctx.arc(mx, my, mr * 2.4, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(mx, my, mr, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(255,250,240,0.7)';
    ctx.fill();

    // Mountains — 3 layers, far to near
    _drawMountain([
      [0, h * 0.72], [w * 0.1, h * 0.38], [w * 0.25, h * 0.52],
      [w * 0.38, h * 0.28], [w * 0.52, h * 0.46], [w * 0.65, h * 0.30],
      [w * 0.78, h * 0.50], [w * 0.90, h * 0.34], [w, h * 0.62], [w, h * 0.72],
    ], '#1c1828');

    _drawMountain([
      [0, h * 0.72], [w * 0.08, h * 0.48], [w * 0.22, h * 0.60],
      [w * 0.35, h * 0.38], [w * 0.50, h * 0.55], [w * 0.62, h * 0.40],
      [w * 0.75, h * 0.58], [w * 0.88, h * 0.44], [w, h * 0.68], [w, h * 0.72],
    ], '#141220');

    _drawMountain([
      [0, h], [0, h * 0.72], [w * 0.06, h * 0.58], [w * 0.18, h * 0.68],
      [w * 0.30, h * 0.52], [w * 0.45, h * 0.65], [w * 0.58, h * 0.50],
      [w * 0.70, h * 0.64], [w * 0.84, h * 0.56], [w, h * 0.70], [w, h],
    ], '#0e0d16');

    // Ground fill below mountains
    ctx.fillStyle = '#0e0d16';
    ctx.fillRect(0, h * 0.72, w, h);

    // Road — winding bezier path up nearest mountain face
    ctx.save();
    ctx.beginPath();
    var pts = roadPoints;
    ctx.moveTo(pts[0].x * w, pts[0].y * h);
    for (var i = 1; i < pts.length - 1; i++) {
      var cx_ = (pts[i].x * w + pts[i + 1].x * w) * 0.5;
      var cy_ = (pts[i].y * h + pts[i + 1].y * h) * 0.5;
      ctx.quadraticCurveTo(pts[i].x * w, pts[i].y * h, cx_, cy_);
    }
    ctx.lineTo(pts[pts.length - 1].x * w, pts[pts.length - 1].y * h);
    ctx.strokeStyle = 'rgba(255,255,255,0.08)';
    ctx.lineWidth = 3;
    ctx.stroke();
    ctx.restore();

    // Car dot moving along road
    carT = (carT + currentSpeed * 0.0004) % 1;
    var carPos = _roadPoint(carT);
    ctx.beginPath();
    ctx.rect(carPos.x - 2, carPos.y - 4, 4, 8);
    ctx.fillStyle = '#c8102e';
    ctx.fill();

    // Track name watermark near mountain peak
    if (trackName) {
      ctx.save();
      ctx.font = '90px "Bebas Neue", sans-serif';
      ctx.fillStyle = 'rgba(255,255,255,0.03)';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(trackName.toUpperCase(), w * 0.5, h * 0.28);
      ctx.restore();
    }
  }

  function _drawMountain(pts, color) {
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (var i = 1; i < pts.length; i++) {
      ctx.lineTo(pts[i][0], pts[i][1]);
    }
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
  }

  function _roadPoint(t) {
    // Lerp along the polyline of roadPoints
    var pts = roadPoints;
    var totalLen = pts.length - 1;
    var idx = Math.min(Math.floor(t * totalLen), totalLen - 1);
    var frac = (t * totalLen) - idx;
    var a = pts[idx], b = pts[idx + 1];
    return {
      x: (a.x + (b.x - a.x) * frac) * w,
      y: (a.y + (b.y - a.y) * frac) * h,
    };
  }

  function _loop() {
    if (!paused) _draw();
    animId = requestAnimationFrame(_loop);
  }

  function setSpeed(s)     { targetSpeed = s; }
  function setTrackName(n) { trackName = n || ''; }
  function pause()         { paused = true; }
  function resume()        { paused = false; }

  return { init: init, setSpeed: setSpeed, setTrackName: setTrackName, pause: pause, resume: resume };
})();

// Keep WorldCanvas as alias so any stale references don't crash
var WorldCanvas = MountainCanvas;


// ─── CarCanvas ───────────────────────────────────────────────────────────────
var CarCanvas = (function () {
  var canvas, ctx;
  var animId;
  var rarity = 'common';
  var active = false;
  var t = 0;

  var RARITY_COLORS = {
    common:    '#8a86a8',
    uncommon:  '#22c55e',
    rare:      '#60a5fa',
    epic:      '#a78bfa',
    legendary: '#c4a25a',
  };

  function init(el) {
    canvas = el;
    ctx = canvas.getContext('2d');
    canvas.width  = canvas.parentElement ? (canvas.parentElement.clientWidth  || 360) : 360;
    canvas.height = canvas.parentElement ? (canvas.parentElement.clientHeight || 300) : 300;
    if (animId) cancelAnimationFrame(animId);
    _loop();
  }

  function _draw() {
    t += 0.010;
    var cw = canvas.width, ch = canvas.height;
    ctx.clearRect(0, 0, cw, ch);

    // Spotlight background
    var bg = ctx.createRadialGradient(cw * 0.5, ch * 0.5, 0, cw * 0.5, ch * 0.5, Math.max(cw, ch) * 0.55);
    bg.addColorStop(0, active ? 'rgba(200,16,46,0.05)' : 'rgba(255,255,255,0.04)');
    bg.addColorStop(1, '#0b0b0f');
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, cw, ch);

    var color = RARITY_COLORS[(rarity || 'common').toLowerCase()] || RARITY_COLORS.common;
    var squeeze = Math.abs(Math.cos(t * 0.4));

    // Low-profile car silhouette (bezier)
    var bw = cw * 0.55 * (0.55 + 0.45 * squeeze);
    var bh = ch * 0.18;
    var bx = cw * 0.5 - bw * 0.5;
    var by = ch * 0.46;

    ctx.globalAlpha = 0.85;
    ctx.fillStyle = color;

    // Body
    ctx.beginPath();
    ctx.moveTo(bx, by + bh);
    ctx.lineTo(bx + bw * 0.06, by + bh * 0.4);
    ctx.bezierCurveTo(bx + bw * 0.12, by, bx + bw * 0.28, by - bh * 0.55, bx + bw * 0.38, by - bh * 0.6);
    ctx.lineTo(bx + bw * 0.68, by - bh * 0.6);
    ctx.bezierCurveTo(bx + bw * 0.78, by - bh * 0.55, bx + bw * 0.88, by, bx + bw * 0.92, by + bh * 0.4);
    ctx.lineTo(bx + bw, by + bh);
    ctx.closePath();
    ctx.fill();

    // Roof highlight
    ctx.globalAlpha = 0.3;
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.ellipse(bx + bw * 0.5, by - bh * 0.3, bw * 0.18 * squeeze, bh * 0.12, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;

    // Wheels
    var wr = bw * 0.1;
    var wy = by + bh * 0.88;
    [[bx + bw * 0.2, wy], [bx + bw * 0.73, wy]].forEach(function (pos) {
      ctx.beginPath();
      ctx.ellipse(pos[0], pos[1], wr * squeeze + wr * 0.1, wr, 0, 0, Math.PI * 2);
      ctx.fillStyle = '#0b0b0f';
      ctx.globalAlpha = 0.9;
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.globalAlpha = 0.6;
      ctx.stroke();
      ctx.globalAlpha = 1;
    });

    // Rarity ring at base
    var ringY = ch * 0.72;
    var ringRx = bw * 0.42 * squeeze + bw * 0.06;
    ctx.beginPath();
    ctx.ellipse(cw * 0.5, ringY, ringRx, 6, 0, 0, Math.PI * 2);
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.globalAlpha = 0.3;
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  function _loop() {
    _draw();
    animId = requestAnimationFrame(_loop);
  }

  function setRarity(r) { rarity = r; }
  function setActive(a) { active = a; }

  return { init: init, setRarity: setRarity, setActive: setActive };
})();


// ─── LootboxCanvas ───────────────────────────────────────────────────────────
var LootboxCanvas = (function () {
  var canvas, ctx;
  var animId;
  var tier = 'bronze';
  var state = 'idle';
  var t = 0;
  var particles = [];
  var shakeStart = 0;
  var burstStart = 0;
  var completeCb = null;

  var TIER_COLORS = {
    bronze:   '#cd7f32',
    silver:   '#b0b8c8',
    gold:     '#c4a25a',
    platinum: '#60a5fa',
  };

  function _initParticles() {
    particles = [];
    for (var i = 0; i < 32; i++) {
      particles.push({
        angle:  Math.random() * Math.PI * 2,
        radius: 38 + Math.random() * 44,
        speed:  0.012 + Math.random() * 0.022,
        size:   2 + Math.random() * 3,
        vx: 0, vy: 0, x: 0, y: 0, alpha: 1,
      });
    }
  }

  function init(el) {
    canvas = el;
    ctx = canvas.getContext('2d');
    canvas.width  = canvas.parentElement ? (canvas.parentElement.clientWidth  || 300) : 300;
    canvas.height = canvas.parentElement ? (canvas.parentElement.clientHeight || 300) : 300;
    state = 'idle';
    t = 0;
    _initParticles();
    if (animId) cancelAnimationFrame(animId);
    _loop();
  }

  function _drawBox(cx, cy, color, offX, offY, scale) {
    var bw = 55, bh = 48;
    ctx.save();
    ctx.translate(cx + offX, cy + offY);
    ctx.scale(scale, scale);

    ctx.beginPath();
    ctx.moveTo(0, -bh * 0.5);
    ctx.lineTo(bw * 0.5 * Math.cos(t), -bh * 0.5 + bw * 0.5 * Math.sin(t) * 0.4);
    ctx.lineTo(0, -bh * 0.5 + bw * Math.sin(t) * 0.4);
    ctx.lineTo(-bw * 0.5 * Math.cos(t), -bh * 0.5 + bw * 0.5 * Math.sin(t) * 0.4);
    ctx.closePath();
    ctx.fillStyle = color; ctx.globalAlpha = 0.9; ctx.fill();

    ctx.beginPath();
    ctx.moveTo(0, -bh * 0.5 + bw * Math.sin(t) * 0.4);
    ctx.lineTo(bw * 0.5 * Math.cos(t), -bh * 0.5 + bw * 0.5 * Math.sin(t) * 0.4);
    ctx.lineTo(bw * 0.5 * Math.cos(t), bh * 0.5 + bw * 0.5 * Math.sin(t) * 0.4);
    ctx.lineTo(0, bh * 0.5 + bw * Math.sin(t) * 0.4);
    ctx.closePath();
    ctx.fillStyle = color; ctx.globalAlpha = 0.55; ctx.fill();

    ctx.beginPath();
    ctx.moveTo(0, -bh * 0.5 + bw * Math.sin(t) * 0.4);
    ctx.lineTo(-bw * 0.5 * Math.cos(t), -bh * 0.5 + bw * 0.5 * Math.sin(t) * 0.4);
    ctx.lineTo(-bw * 0.5 * Math.cos(t), bh * 0.5 + bw * 0.5 * Math.sin(t) * 0.4);
    ctx.lineTo(0, bh * 0.5 + bw * Math.sin(t) * 0.4);
    ctx.closePath();
    ctx.fillStyle = color; ctx.globalAlpha = 0.35; ctx.fill();

    ctx.globalAlpha = 0.65;
    ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.stroke();
    ctx.globalAlpha = 1;
    ctx.restore();
  }

  function _draw() {
    var cw = canvas.width, ch = canvas.height;
    var cx = cw * 0.5, cy = ch * 0.5;
    var color = TIER_COLORS[tier] || TIER_COLORS.bronze;
    var now = Date.now();

    ctx.clearRect(0, 0, cw, ch);
    ctx.fillStyle = '#0b0b0f';
    ctx.fillRect(0, 0, cw, ch);

    if (state === 'done') return;

    if (state === 'burst') {
      var bElap = now - burstStart;
      if (bElap > 600) {
        state = 'done';
        if (completeCb) { var cb = completeCb; completeCb = null; cb(); }
        return;
      }
      particles.forEach(function (p) {
        p.x += p.vx; p.y += p.vy;
        p.alpha = Math.max(0, 1 - bElap / 600);
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.globalAlpha = p.alpha;
        ctx.fill();
        ctx.globalAlpha = 1;
      });
      return;
    }

    var offX = 0, offY = 0, scale = 1;
    if (state === 'cracking') {
      var cElap = now - shakeStart;
      if (cElap > 800) {
        state = 'burst';
        burstStart = now;
        particles.forEach(function (p) {
          var a = Math.random() * Math.PI * 2;
          var spd = 3 + Math.random() * 6;
          p.vx = Math.cos(a) * spd; p.vy = Math.sin(a) * spd;
          p.x = cx; p.y = cy; p.alpha = 1;
        });
        return;
      }
      offX  = Math.sin(cElap * 0.055) * 8 * (1 - cElap / 800);
      offY  = Math.cos(cElap * 0.07)  * 6 * (1 - cElap / 800);
      scale = 1 + Math.sin(cElap * 0.022) * 0.12;
    } else {
      t += 0.016;
    }

    particles.forEach(function (p) {
      p.angle += p.speed;
      var px = cx + Math.cos(p.angle) * p.radius + offX * 0.3;
      var py = cy + Math.sin(p.angle) * p.radius * 0.42 + offY * 0.3;
      ctx.beginPath(); ctx.arc(px, py, p.size, 0, Math.PI * 2);
      ctx.fillStyle = color; ctx.globalAlpha = 0.4; ctx.fill(); ctx.globalAlpha = 1;
    });

    _drawBox(cx, cy, color, offX, offY, scale);
  }

  function _loop() {
    _draw();
    animId = requestAnimationFrame(_loop);
  }

  function setTier(tierVal) { tier = tierVal; }

  function crack(callback) {
    if (state === 'idle') {
      state = 'cracking';
      shakeStart = Date.now();
      completeCb = callback;
    }
  }

  return { init: init, setTier: setTier, crack: crack };
})();


// ─── BootCanvas ──────────────────────────────────────────────────────────────
var BootCanvas = (function () {
  var canvas, ctx;
  var animId;
  var running = false;
  var driftStars = [];

  function start() {
    canvas = document.getElementById('boot-canvas');
    if (!canvas) return;
    ctx = canvas.getContext('2d');
    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;
    running = true;

    driftStars = [];
    for (var i = 0; i < 60; i++) {
      driftStars.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height * 0.65,
        r: Math.random() * 1.0 + 0.2,
        a: Math.random() * 0.25 + 0.1,
        vy: -(0.04 + Math.random() * 0.12),
      });
    }
    _loop();
  }

  function _loop() {
    if (!running) return;
    var w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Mountain silhouette bottom
    ctx.beginPath();
    ctx.moveTo(0, h);
    ctx.lineTo(0, h * 0.68);
    ctx.lineTo(w * 0.12, h * 0.50);
    ctx.lineTo(w * 0.24, h * 0.62);
    ctx.lineTo(w * 0.36, h * 0.42);
    ctx.lineTo(w * 0.50, h * 0.56);
    ctx.lineTo(w * 0.62, h * 0.40);
    ctx.lineTo(w * 0.76, h * 0.58);
    ctx.lineTo(w * 0.88, h * 0.46);
    ctx.lineTo(w, h * 0.64);
    ctx.lineTo(w, h);
    ctx.closePath();
    ctx.fillStyle = '#0e0d16';
    ctx.fill();

    // Horizon line accent
    ctx.beginPath();
    ctx.moveTo(0, h * 0.68);
    ctx.lineTo(w, h * 0.68);
    ctx.strokeStyle = 'rgba(200,16,46,0.2)';
    ctx.lineWidth = 1;
    ctx.stroke();

    // Drifting stars
    driftStars.forEach(function (s) {
      s.y += s.vy;
      if (s.y < 0) { s.y = h * 0.65; s.x = Math.random() * w; }
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(255,250,240,' + s.a + ')';
      ctx.fill();
    });

    animId = requestAnimationFrame(_loop);
  }

  function stop() {
    running = false;
    if (animId) cancelAnimationFrame(animId);
  }

  return { start: start, stop: stop };
})();
