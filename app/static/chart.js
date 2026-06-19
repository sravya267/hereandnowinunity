
// ─── Vibrational tab ─────────────────────────────────────────────────────────

function vibSetAll(on) {
  document.querySelectorAll('.vib-body').forEach(function(cb){ cb.checked = on; });
}

function vibCompute() {
  if (!LAST_DATA) { alert('Calculate a chart first.'); return; }

  var active = [];
  document.querySelectorAll('.vib-body:checked').forEach(function(cb){ active.push(cb.value); });
  if (active.length < 2) { alert('Select at least two bodies.'); return; }

  var btn = document.getElementById('vib-compute-btn');
  btn.disabled = true;
  document.getElementById('vib-empty').style.display = 'none';
  document.getElementById('vib-results').style.display = 'none';
  document.getElementById('vib-spinner').style.display = 'flex';

  var d = LAST_DATA;
  var payload = {
    birth_datetime: d.birth_datetime,
    location: d.location,
    zodiac_system: d.zodiac_system,
    house_system: d.moment ? (d.house_system || 'Koch') : 'Koch',
    base_orb: parseFloat(document.getElementById('vib-base-orb').value) || 8.0,
    orb_formula: document.getElementById('vib-orb-formula').value,
    active_bodies: active,
    max_harmonic: 32,
    min_tightness_pct: 0,
    personal_only: true,
  };

  fetch('/harmonics', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload) })
    .then(function(r){
      if (!r.ok) return r.json().then(function(e){ throw new Error(e.detail || 'Failed'); });
      return r.json();
    })
    .then(function(data){ vibRender(data); })
    .catch(function(err){
      document.getElementById('vib-spinner').style.display = 'none';
      document.getElementById('vib-empty').textContent = 'Error: ' + err.message;
      document.getElementById('vib-empty').style.display = 'flex';
    })
    .finally(function(){ btn.disabled = false; });
}

function vibRender(data) {
  document.getElementById('vib-spinner').style.display = 'none';
  var ranked = data.ranked || [];
  if (!ranked.length) {
    document.getElementById('vib-empty').textContent = 'No harmonic resonances found with current settings.';
    document.getElementById('vib-empty').style.display = 'flex';
    return;
  }

  var maxPairs = ranked[0].PairCount || 1;
  var tbody = document.getElementById('vib-tbody');
  tbody.innerHTML = '';

  ranked.forEach(function(row, i) {
    var barW = Math.round((row.PairCount / maxPairs) * 100);
    var pairHtml = (row.Pairs || '').split(',  ').map(function(p) {
      p = p.trim();
      var m = p.match(/^(.*?)(\s[\d.]+°.*)$/);
      return m ? '<b>' + m[1] + '</b>' + m[2] : p;
    }).join('<br>');

    var name = row.Name ? ' · ' + row.Name : '';
    var hasMeaning = row.NatalMeaning && row.NatalMeaning !== 'nan' && row.NatalMeaning !== '';
    var detailId = 'vib-detail-' + i;

    var tr = document.createElement('tr');
    tr.className = 'vib-data-row';
    tr.style.cursor = hasMeaning ? 'pointer' : 'default';
    tr.innerHTML =
      '<td class="vib-h">' +
        'H' + row.Harmonic +
        (hasMeaning ? '<span class="vib-expand-icon" id="icon-' + i + '">&#9656;</span>' : '') +
      '</td>' +
      '<td><span class="vib-name">' + (row.Name || '&mdash;') + '</span><br>' +
        '<span class="vib-factors">' + (row.Factors || '') + '</span></td>' +
      '<td class="num">' +
        '<div style="display:flex;align-items:center;gap:4px;justify-content:flex-end">' +
          '<div style="width:40px;height:6px;background:#f5efe6;border-radius:3px;overflow:hidden">' +
            '<div style="width:' + barW + '%;height:100%;background:#8b7355"></div>' +
          '</div>' +
          row.PairCount +
        '</div>' +
      '</td>' +
      '<td class="num">' + (row.Tightest || 0).toFixed(3) + '&deg;</td>' +
      '<td class="vib-pairs">' + pairHtml + '</td>';

    // Meaning detail row (hidden by default)
    var trDetail = document.createElement('tr');
    trDetail.id = detailId;
    trDetail.className = 'vib-meaning-row';
    trDetail.style.display = 'none';
    if (hasMeaning) {
      var src = (row.Source && row.Source !== 'nan') ? '<div class="vib-source">Source: ' + row.Source + '</div>' : '';
      trDetail.innerHTML =
        '<td colspan="5" class="vib-meaning-cell">' +
          '<div class="vib-meaning-natal">' + row.NatalMeaning + '</div>' +
          src +
        '</td>';

      (function(tr, trDetail, iconId) {
        tr.addEventListener('click', function() {
          var open = trDetail.style.display !== 'none';
          trDetail.style.display = open ? 'none' : 'table-row';
          var icon = document.getElementById(iconId);
          if (icon) icon.textContent = open ? '▸' : '▾';
        });
      })(tr, trDetail, 'icon-' + i);
    }

    tbody.appendChild(tr);
    tbody.appendChild(trDetail);
  });

  document.getElementById('vib-results').style.display = 'block';
}

// ─── Wheel drawing ────────────────────────────────────────────────────────────
var SIGN_NAMES_W = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'];
var SIGN_ABBR_W  = ['Ari','Tau','Gem','Can','Leo','Vir','Lib','Sco','Sag','Cap','Aqu','Pis'];
// Element-tinted glyphs: Fire=red, Earth=green, Air=amber, Water=blue
var SIGN_GLYPH_COLS = ['#c0392b','#3a8a3a','#d4a017','#2e7e9e','#c0392b','#3a8a3a','#d4a017','#2e7e9e','#c0392b','#3a8a3a','#d4a017','#2e7e9e'];
var NAK_NAMES = ['Ashw','Bhar','Krit','Rohi','Mrig','Ardr','Puna','Push','Ashl','Magh','PPha','UPha','Hast','Chit','Swat','Vish','Anur','Jyes','Mool','PAsh','UAsh','Shra','Dhan','Shat','PBha','UBha','Reva'];

// Aspect catalog. major=true for the 5 major aspects, positive=true for harmonious.
// inAspPanel=false aspects are computed by the backend and used by the
// Vibrational Resonance card, but they don't appear as checkboxes in the
// Aspects filter and never render on the main natal wheel.
var ASP_TYPES = [
  {name:'Conjunction',  sym:'☌',  major:true,  positive:false, harmonic:1,  defaultOn:true,  inAspPanel:true},
  {name:'Opposition',   sym:'☍',  major:true,  positive:false, harmonic:2,  defaultOn:true,  inAspPanel:true},
  {name:'Trine',        sym:'△',  major:true,  positive:true,  harmonic:3,  defaultOn:true,  inAspPanel:true},
  {name:'Square',       sym:'□',  major:true,  positive:false, harmonic:4,  defaultOn:true,  inAspPanel:true},
  {name:'Sextile',      sym:'✶',  major:true,  positive:true,  harmonic:6,  defaultOn:true,  inAspPanel:true},
  {name:'Quincunx',     sym:'⚻',  major:false, positive:false, harmonic:12, defaultOn:false, inAspPanel:true},
  {name:'Semi-sextile', sym:'⚹',  major:false, positive:true,  harmonic:12, defaultOn:false, inAspPanel:true},
  {name:'Semi-square',  sym:'∠',  major:false, positive:false, harmonic:8,  defaultOn:false, inAspPanel:true},
  {name:'Sesquisquare', sym:'Sq', major:false, positive:false, harmonic:8,  defaultOn:false, inAspPanel:true},
  {name:'Quintile',     sym:'Q',  major:false, positive:true,  harmonic:5,  defaultOn:false, inAspPanel:true},
  {name:'Bi-Quintile',  sym:'bQ', major:false, positive:true,  harmonic:5,  defaultOn:false, inAspPanel:true},
  {name:'Septile',      sym:'S',  major:false, positive:false, harmonic:7,  defaultOn:false, inAspPanel:true},
  {name:'Biseptile',    sym:'bS', major:false, positive:false, harmonic:7,  defaultOn:false, inAspPanel:true},
  {name:'Triseptile',   sym:'tS', major:false, positive:false, harmonic:7,  defaultOn:false, inAspPanel:true},
  {name:'Novile',       sym:'N',  major:false, positive:true,  harmonic:9,  defaultOn:false, inAspPanel:true},
  {name:'Bi-Novile',    sym:'bN', major:false, positive:true,  harmonic:9,  defaultOn:false, inAspPanel:true},
  {name:'Quadri-Novile',sym:'qN', major:false, positive:true,  harmonic:9,  defaultOn:false, inAspPanel:true},
  {name:'Decile',       sym:'D',  major:false, positive:true,  harmonic:10, defaultOn:false, inAspPanel:true},
  {name:'Tri-Decile',   sym:'tD', major:false, positive:true,  harmonic:10, defaultOn:false, inAspPanel:true},
  {name:'Undecile',     sym:'U',  major:false, positive:true,  harmonic:11, defaultOn:false, inAspPanel:true}
];
// major-neg=red, major-pos=green, minor-neg=orange, minor-pos=seagreen
function aspLineColor(meta) {
  if (!meta) return '#999';
  if (meta.major  && !meta.positive) return '#c0392b';
  if (meta.major  &&  meta.positive) return '#27ae60';
  if (!meta.major && !meta.positive) return '#e67e22';
  return '#1e8449';
}

// Display toggles. Per-planet keys default to true; group keys default to false.
// Unchecking a body hides its symbol and any aspect lines involving it.
var BODY_DISPLAY = {
  Sun:true, Moon:true, Mercury:true, Venus:true, Mars:true,
  Jupiter:true, Saturn:true, Uranus:true, Neptune:true, Pluto:true,
  Chiron:false, Nodes:false, Angles:false, Points:false
};
var ASPECT_TO    = {Chiron:false, Nodes:false, Angles:false, Points:false};
var MAJOR_ORB_VAL = 8;
var MINOR_ORB_VAL = 4;
var NODE_NAMES  = ['North Node','South Node','True Node','Mean Node','Rahu','Ketu'];
var ANGLE_NAMES = ['Asc','Desc','MC','IC'];
var POINT_NAMES = ['Vertex','Fortune'];

function bodyGroup(name) {
  if (name === 'Chiron') return 'Chiron';
  if (NODE_NAMES.indexOf(name) !== -1) return 'Nodes';
  if (ANGLE_NAMES.indexOf(name) !== -1) return 'Angles';
  if (POINT_NAMES.indexOf(name) !== -1) return 'Points';
  return null;
}

// Filter state. ASP_FILTER[name] = bool.
var ASP_FILTER = {};
ASP_TYPES.forEach(function(a){ ASP_FILTER[a.name] = a.defaultOn; });

// Latest chart data, kept so filter changes can re-render without re-fetching.
var LAST_DATA = null;
var LAST_HARM_PARAMS = null; // params used for the last /harmonics fetch
var PAT_SEGMENTS = []; // aspect segments belonging to active patterns, set by drawWheel
var UNKNOWN_TIME_MOON_RANGE = null; // {start: lon°, end: lon°} when unknown-time is active

function drawWheel(data) {
  if (!data) return;
  PAT_SEGMENTS = [];
  var cvs = document.getElementById('wheel-canvas');
  var parent = cvs.parentElement;
  var dpr = window.devicePixelRatio || 1;
  var W = parent.clientWidth, H = parent.clientHeight;
  cvs.width = W * dpr; cvs.height = H * dpr;
  cvs.style.width = W + 'px'; cvs.style.height = H + 'px';

  var ctx = cvs.getContext('2d');
  ctx.setTransform(1,0,0,1,0,0);
  ctx.scale(dpr, dpr);

  var cx = W / 2, cy = H / 2;
  var isSid = data.zodiac_system === 'Sidereal';

  // Radii (outer to inner).
  var outerPad = isSid ? 26 : 6;
  var R   = Math.min(cx, cy) - outerPad;
  var rTickOut = R;
  var r4      = R * 0.93;  // sign ring outer
  var r3      = R * 0.78;  // sign ring inner / merged ring outer
  var rPl_sym = R * 0.71;  // planet symbol in merged ring
  var rPl_lbl = R * 0.62;  // degree label in merged ring
  var r1      = R * 0.44;  // aspect circle / merged ring inner

  // Rotation: Desc at right (3 o'clock), Asc at left (9 o'clock).
  var desc = data.bodies.find(function(b){ return b.Body === 'Desc'; });
  var rotLon = desc ? desc['Longitude (°)'] : 0;
  function lon2a(lon) { return -(lon - rotLon) * Math.PI / 180; }
  function pt(r, a) { return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; }

  // ── canvas background
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, W, H);

  // ── zodiac sign band (white cells, hairline separators, element-tinted names)
  for (var i = 0; i < 12; i++) {
    var sa1 = lon2a(i * 30);
    var sa2 = lon2a((i + 1) * 30);
    ctx.beginPath();
    ctx.arc(cx, cy, r4, sa1, sa2, true);
    ctx.arc(cx, cy, r3, sa2, sa1, false);
    ctx.closePath();
    ctx.fillStyle = '#fff';
    ctx.fill();
    ctx.strokeStyle = '#888'; ctx.lineWidth = 0.6; ctx.stroke();

    var midA = lon2a(i * 30 + 15);
    var mr = (r4 + r3) / 2;
    var sgp = pt(mr, midA);
    ctx.save();
    ctx.translate(sgp[0], sgp[1]);
    ctx.rotate(midA + Math.PI / 2);
    ctx.font = '600 ' + Math.round(R * 0.038) + 'px sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillStyle = SIGN_GLYPH_COLS[i];
    ctx.fillText(SIGN_NAMES_W[i], 0, 0);
    ctx.restore();
  }

  // ── degree tick marks (outside the sign band)
  for (var dt = 0; dt < 360; dt++) {
    var ta = lon2a(dt);
    var inner = (dt % 10 === 0) ? r4 - R*0.025
              : (dt % 5  === 0) ? r4 - R*0.014
                                 : r4 - R*0.007;
    var tp1 = pt(inner, ta), tp2 = pt(rTickOut, ta);
    ctx.beginPath();
    ctx.moveTo(tp1[0], tp1[1]); ctx.lineTo(tp2[0], tp2[1]);
    ctx.strokeStyle = (dt % 10 === 0) ? '#444' : (dt % 5 === 0 ? '#888' : '#bbb');
    ctx.lineWidth   = (dt % 10 === 0) ? 0.7   : 0.4;
    ctx.stroke();
  }

  // ── nakshatra ring (sidereal only)
  if (isSid) {
    var nakSpan = 360 / 27;
    var nakR = R + outerPad - 4;
    var nakInner = rTickOut + 2;
    for (var ni = 0; ni < 27; ni++) {
      var na1 = lon2a(ni * nakSpan);
      var na2 = lon2a((ni + 1) * nakSpan);
      ctx.beginPath();
      ctx.arc(cx, cy, nakR, na1, na2, true);
      ctx.arc(cx, cy, nakInner, na2, na1, false);
      ctx.closePath();
      ctx.fillStyle = ni % 2 === 0 ? '#fdf8f2' : '#f5efe6';
      ctx.fill();
      ctx.strokeStyle = '#e8e0d5'; ctx.lineWidth = 0.3; ctx.stroke();

      var nMid = lon2a(ni * nakSpan + nakSpan / 2);
      var nMr = (nakR + nakInner) / 2;
      var np = pt(nMr, nMid);
      ctx.save();
      ctx.translate(np[0], np[1]);
      ctx.rotate(nMid + Math.PI / 2);
      ctx.font = Math.round(R * 0.042) + 'px sans-serif';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillStyle = '#8b7355';
      ctx.fillText(NAK_NAMES[ni], 0, 0);
      ctx.restore();
    }
  }

  // ── merged ring inner edge (aspect circle)
  ctx.beginPath(); ctx.arc(cx, cy, r1, 0, 2*Math.PI);
  ctx.strokeStyle = '#bbb'; ctx.lineWidth = 0.5; ctx.stroke();

  // ── house cusp tick lines (r1 -> r3)
  var cusps = data.bodies.filter(function(b){ return b.Body.indexOf('House Cusp') !== -1; });
  cusps.forEach(function(c) {
    var ca = lon2a(c['Longitude (°)']);
    var cp1 = pt(r1, ca), cp2 = pt(r3, ca);
    ctx.beginPath();
    ctx.moveTo(cp1[0], cp1[1]); ctx.lineTo(cp2[0], cp2[1]);
    ctx.strokeStyle = '#bbb'; ctx.lineWidth = 0.5; ctx.stroke();
  });

  // ── house numbers in the house band
  var sorted = cusps.slice().sort(function(a,b){ return a['Longitude (°)'] - b['Longitude (°)']; });
  for (var hi = 0; hi < sorted.length; hi++) {
    var l1 = sorted[hi]['Longitude (°)'];
    var l2 = sorted[(hi+1) % sorted.length]['Longitude (°)'];
    if (l2 <= l1) l2 += 360;
    var houseNum = parseInt(sorted[hi].Body.replace('House Cusp ', ''), 10);
    var hMid = lon2a((l1 + l2) / 2);
    var hR = r1 + R * 0.055;
    var hp = pt(hR, hMid);
    ctx.font = Math.round(R * 0.05) + 'px sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillStyle = '#888';
    ctx.fillText(String(houseNum), hp[0], hp[1]);
  }

  // ── Asc / Desc / MC / IC axes — drawn only between the first (r1) and
  //    second (r3) circles, leaving the inner aspect circle clear of axis
  //    lines. Names sit just inside r3, parallel to each line.
  if (BODY_DISPLAY.Angles) ['Asc','Desc','MC','IC'].forEach(function(name) {
    var b = data.bodies.find(function(x){ return x.Body === name; });
    if (!b) return;
    var aa = lon2a(b['Longitude (°)']);
    var ip = pt(r1, aa);
    var ap = pt(r3, aa);
    ctx.beginPath();
    ctx.moveTo(ip[0], ip[1]); ctx.lineTo(ap[0], ap[1]);
    ctx.strokeStyle = '#222'; ctx.lineWidth = 1.0; ctx.stroke();

    var lp = pt(r3 - R * 0.06, aa);
    var rot = aa;
    if (Math.cos(rot) < 0) rot += Math.PI;
    var fs = Math.round(R * 0.038);
    var degStr = signDeg(b['Longitude (°)']);
    ctx.save();
    ctx.translate(lp[0], lp[1]);
    ctx.rotate(rot);
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.lineWidth = 3; ctx.strokeStyle = '#fff';
    ctx.font = 'bold ' + fs + 'px sans-serif';
    ctx.strokeText(name, 0, -fs * 0.65);
    ctx.fillStyle = '#222';
    ctx.fillText(name, 0, -fs * 0.65);
    ctx.font = (fs - 1) + 'px sans-serif';
    ctx.strokeText(degStr, 0, fs * 0.65);
    ctx.fillStyle = '#555';
    ctx.fillText(degStr, 0, fs * 0.65);
    ctx.restore();
  });

  // ── planets in merged ring — bold, radially rotated, stacked inward for clusters
  var planets = data.bodies.filter(function(b){
    if (!b.Symbol || b.Body.indexOf('House') !== -1) return false;
    if (ANGLE_NAMES.indexOf(b.Body) !== -1) return false;
    if (BODY_DISPLAY.hasOwnProperty(b.Body) && !BODY_DISPLAY[b.Body]) return false;
    var grp = bodyGroup(b.Body);
    if (grp && !BODY_DISPLAY[grp]) return false;
    return true;
  }).slice().sort(function(a,b){ return a['Longitude (°)'] - b['Longitude (°)']; });

  var clusterDeg = 6, rShift = R * 0.075;
  var lastLon = -1e9, lastShift = 0;
  var placements = planets.map(function(p) {
    var lon = p['Longitude (°)'];
    var shift = (lon - lastLon < clusterDeg) ? Math.min(lastShift + 1, 3) : 0;
    lastLon = lon; lastShift = shift;
    return { p: p, rSym: Math.max(r1 + R*0.06, rPl_sym - shift * rShift), a: lon2a(lon) };
  });
  placements.forEach(function(it){
    var t1 = pt(r3, it.a), t2 = pt(it.rSym + R*0.038, it.a);
    ctx.beginPath(); ctx.moveTo(t1[0], t1[1]); ctx.lineTo(t2[0], t2[1]);
    ctx.strokeStyle = '#ccc'; ctx.lineWidth = 0.5; ctx.stroke();
  });
  placements.forEach(function(it) {
    var p = it.p, a = it.a;
    var ssp = pt(it.rSym, a);
    ctx.save();
    ctx.translate(ssp[0], ssp[1]);
    ctx.rotate(a + Math.PI / 2);
    ctx.font = 'bold ' + Math.round(R * 0.088) + 'px serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillStyle = '#000';
    ctx.fillText(p.Symbol, 0, 0);
    ctx.restore();
    var dd = p['Longitude (°)'] % 30;
    var deg = Math.floor(dd), mn = Math.floor((dd - deg) * 60);
    var lbl = deg + '°' + (mn < 10 ? '0' : '') + mn + "'";
    if (p.Motion === 'R') lbl += ' R';
    var lbp = pt(it.rSym - R*0.095, a);
    ctx.save();
    ctx.translate(lbp[0], lbp[1]);
    // Radial orientation (parallel to aspect lines). Flip on left half so text stays upright.
    var flip = (a > Math.PI / 2 || a < -Math.PI / 2) ? Math.PI : 0;
    ctx.rotate(a + flip);
    ctx.font = Math.round(R * 0.032) + 'px sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillStyle = p.Motion === 'R' ? '#c0392b' : '#444';
    ctx.fillText(lbl, 0, 0);
    ctx.restore();
  });

  // ── aspect lines (filtered by orb type, major/minor thresholds, and body toggles)
  var posMap = {};
  data.bodies.forEach(function(b){ posMap[b.Body] = lon2a(b['Longitude (°)']); });

  // Build set of body-pairs that belong to any currently-active pattern type.
  // These get drawn with extra emphasis so the user sees the pattern on the chart.
  var patternEdges = {};
  (data.patterns || []).forEach(function(p){
    if (!PAT_FILTER[p.type]) return;
    var bodies = p.bodies || [];
    for (var i = 0; i < bodies.length; i++) {
      for (var j = i + 1; j < bodies.length; j++) {
        var a = bodies[i], b = bodies[j];
        var key = a < b ? a + '|' + b : b + '|' + a;
        if (!patternEdges[key]) patternEdges[key] = [];
        patternEdges[key].push(p);
      }
    }
  });
  function edgeKey(a, b) { return a < b ? a + '|' + b : b + '|' + a; }
  // Asc/Desc and MC/IC are 180° apart by definition; suppress only those
  // diameter pairs so the chart doesn't double the axis line. Cross pairs
  // (Asc-MC, Asc-IC, Desc-MC, Desc-IC) remain valid aspects.
  var AXIS_DIAM_PAIRS = {'Asc|Desc':1, 'Desc|Asc':1, 'MC|IC':1, 'IC|MC':1};
  function isAxisDiameterPair(a) { return AXIS_DIAM_PAIRS[a.Body1 + '|' + a.Body2]; }

  var aspects = (data.aspects || []).filter(function(a) {
    if (isAxisDiameterPair(a)) return false;
    // Aspects in an active pattern are always shown so the complete
    // pattern shape (triangle, cross, etc.) is visible — bypass the
    // aspect-type, body-display, and orb filters. The user explicitly
    // enabled the pattern and expects to see its full geometry.
    if (patternEdges[edgeKey(a.Body1, a.Body2)]) return true;
    if (!ASP_FILTER[a.Aspect]) return false;
    // Per-body display: hidden bodies hide their aspect lines
    if (BODY_DISPLAY.hasOwnProperty(a.Body1) && !BODY_DISPLAY[a.Body1]) return false;
    if (BODY_DISPLAY.hasOwnProperty(a.Body2) && !BODY_DISPLAY[a.Body2]) return false;
    var g1 = bodyGroup(a.Body1), g2 = bodyGroup(a.Body2);
    if ((g1 && !ASPECT_TO[g1]) || (g2 && !ASPECT_TO[g2])) return false;
    var meta2 = ASP_TYPES.find(function(t){ return t.name === a.Aspect; });
    var isMajor = meta2 ? meta2.major : true;
    var val = isMajor ? MAJOR_ORB_VAL : MINOR_ORB_VAL;
    var orbDelta = (a.OrbLimit != null && a.Closeness != null)
      ? (1 - a.Closeness) * a.OrbLimit
      : Math.abs((a.Angle || 0) - (a.Degrees || 0));
    return orbDelta <= val;
  });

  aspects.forEach(function(asp) {
    var a1 = posMap[asp.Body1], a2 = posMap[asp.Body2];
    if (a1 == null || a2 == null) return;
    var meta = ASP_TYPES.find(function(t){ return t.name === asp.Aspect; });
    var closeness = asp.Closeness || 0.5;
    var ep1 = pt(r1, a1), ep2 = pt(r1, a2);
    var inPattern = patternEdges[edgeKey(asp.Body1, asp.Body2)];
    ctx.beginPath();
    ctx.moveTo(ep1[0], ep1[1]); ctx.lineTo(ep2[0], ep2[1]);
    ctx.strokeStyle = aspLineColor(meta);
    var hasActivePatterns = Object.keys(patternEdges).length > 0;
    if (inPattern) {
      ctx.lineWidth = Math.max(2.5, closeness * 4);
      ctx.globalAlpha = 1;
      ctx.shadowColor = aspLineColor(meta);
      ctx.shadowBlur = 6;
      ctx.stroke();
      ctx.shadowBlur = 0;
      PAT_SEGMENTS.push({x1:ep1[0], y1:ep1[1], x2:ep2[0], y2:ep2[1], pats: inPattern});
    } else {
      ctx.lineWidth = Math.max(0.4, closeness * 2.5);
      ctx.globalAlpha = hasActivePatterns ? 0.08 : 0.25 + closeness * 0.75;
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  });

  // ── Moon day-range arc (unknown birth time) ──────────────────────────────
  if (UNKNOWN_TIME_MOON_RANGE) {
    var mr = UNKNOWN_TIME_MOON_RANGE;
    var rArc = rPl_sym;  // same ring as planet symbols

    // Convert longitudes to canvas angles
    function moonLon2a(lon) { return -(lon - rotLon) * Math.PI / 180; }

    var aStart2 = moonLon2a(mr.start);
    var aEnd2   = moonLon2a(mr.end);

    // Draw arc (moon moves counter-clockwise when drawn this way → use anticlockwise=true)
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, rArc, aEnd2, aStart2, false);
    ctx.strokeStyle = '#2471a3';
    ctx.lineWidth = 5;
    ctx.globalAlpha = 0.22;
    ctx.stroke();
    ctx.globalAlpha = 1;

    // Tick marks at start and end
    [aStart2, aEnd2].forEach(function(aa) {
      var ip2 = pt(rArc - R*0.04, aa), op2 = pt(rArc + R*0.04, aa);
      ctx.beginPath();
      ctx.moveTo(ip2[0], ip2[1]); ctx.lineTo(op2[0], op2[1]);
      ctx.strokeStyle = '#2471a3'; ctx.lineWidth = 1.2; ctx.globalAlpha = 0.7;
      ctx.stroke();
      ctx.globalAlpha = 1;
    });

    // Label at midpoint of arc
    var span = ((mr.end - mr.start) + 360) % 360;
    var midLon = (mr.start + span / 2) % 360;
    var aMid = moonLon2a(midLon);
    var lp2 = pt(rArc + R * 0.12, aMid);
    ctx.save();
    ctx.translate(lp2[0], lp2[1]);
    ctx.rotate(aMid + Math.PI / 2);
    ctx.font = '600 ' + Math.round(R * 0.036) + 'px sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillStyle = '#2471a3';
    ctx.fillText('☽ ±' + (span / 2).toFixed(1) + '°', 0, 0);
    ctx.restore();
  }
}

// ─── Info box ─────────────────────────────────────────────────────────────────
function signDeg(lon) {
  if (lon == null) return '';
  var d = lon % 30, deg = Math.floor(d), mn = Math.floor((d - deg) * 60);
  return deg + '°' + (mn < 10 ? '0' : '') + mn + "'";
}
function fmtDeg(d) {
  if (d == null) return '';
  var deg = Math.floor(d), mn = Math.floor((d - deg) * 60);
  return deg + '°' + (mn < 10 ? '0' : '') + mn + "'";
}

function buildInfoBox(d) {
  var isSid = d.zodiac_system === 'Sidereal';
  var planets = d.bodies.filter(function(x){
    return x.Body && x.Body.indexOf('House') === -1 &&
      ANGLE_NAMES.indexOf(x.Body) === -1 &&
      POINT_NAMES.indexOf(x.Body) === -1;
  });
  var angles  = d.bodies.filter(function(x){ return ANGLE_NAMES.indexOf(x.Body) !== -1; });
  var points  = d.bodies.filter(function(x){ return POINT_NAMES.indexOf(x.Body) !== -1; });
  var houses  = d.bodies.filter(function(x){ return x.Body && x.Body.indexOf('House Cusp') !== -1; });

  var html = '<div class="s-hdr">Planets</div>';
  planets.forEach(function(p) {
    var sym    = p.Symbol || '';
    var motion = p.Motion === 'R' ? '<span class="retro"> (R)</span>' : ' (D)';
    var house  = p.House ? ' &bull; H' + p.House : '';
    var nak    = (isSid && p.Nakshatra) ? ' &bull; ' + p.Nakshatra + ' P' + p.Pada : '';
    html += sym + ' ' + p.Body + motion + '  ' + p.Sign + ' ' + signDeg(p['Longitude (°)']) + house + nak + '\n';
  });

  if (angles.length) {
    html += '<div class="s-hdr">Angles</div>';
    angles.forEach(function(a){ html += a.Body + '  ' + a.Sign + ' ' + signDeg(a['Longitude (°)']) + '\n'; });
  }
  if (points.length) {
    html += '<div class="s-hdr">Points</div>';
    points.forEach(function(p){
      var sym = p.Symbol ? p.Symbol + ' ' : '';
      var house = p.House ? ' &bull; H' + p.House : '';
      html += sym + p.Body + '  ' + p.Sign + ' ' + signDeg(p['Longitude (°)']) + house + '\n';
    });
  }
  if (houses.length) {
    html += '<div class="s-hdr">Houses</div>';
    houses.forEach(function(h){
      html += h.Body.replace('House Cusp ','H') + '  ' + h.Sign + ' ' + signDeg(h['Longitude (°)']) + '\n';
    });
  }
  if (d.aspects && d.aspects.length) {
    html += '<div class="s-hdr">Aspects (' + d.aspects.length + ')</div>';
    d.aspects.forEach(function(a){
      var orb = (a.Angle != null && a.Degrees != null) ? fmtDeg(Math.abs(a.Angle - a.Degrees)) : '';
      html += '<span class="asp-line">' + a.Body1 + ' ' + (a.aspect_symbol||'') + ' ' + a.Body2 + '  ' + a.Aspect + (orb ? '  orb ' + orb : '') + '</span>\n';
    });
  }
  document.getElementById('info-box').innerHTML = html;
}

function copyNatalAspects() {
  if (!LAST_DATA) return;
  var lines = [];
  (LAST_DATA.aspects || []).forEach(function(a) {
    if (!ASP_FILTER[a.Aspect]) return;
    if (BODY_DISPLAY.hasOwnProperty(a.Body1) && !BODY_DISPLAY[a.Body1]) return;
    if (BODY_DISPLAY.hasOwnProperty(a.Body2) && !BODY_DISPLAY[a.Body2]) return;
    var g1 = bodyGroup(a.Body1), g2 = bodyGroup(a.Body2);
    if ((g1 && !ASPECT_TO[g1]) || (g2 && !ASPECT_TO[g2])) return;
    var meta2 = ASP_TYPES.find(function(t){ return t.name === a.Aspect; });
    var isMajor = meta2 ? meta2.major : true;
    var val = isMajor ? MAJOR_ORB_VAL : MINOR_ORB_VAL;
    var orbDelta = (a.OrbLimit != null && a.Closeness != null)
      ? (1 - a.Closeness) * a.OrbLimit
      : Math.abs((a.Angle || 0) - (a.Degrees || 0));
    if (orbDelta > val) return;
    lines.push(a.Body1 + ' ' + (a.aspect_symbol || a.Aspect) + ' ' + a.Body2 + '  orb ' + orbDelta.toFixed(1) + '°');
  });
  var txt = lines.join('\n');
  navigator.clipboard.writeText(txt).then(function(){
    var b = document.getElementById('natal-copy-asp-btn');
    if (b) { b.textContent = 'Copied!'; setTimeout(function(){ b.textContent = 'Copy Aspects'; }, 1500); }
  });
}

function copyInfo() {
  var txt = document.getElementById('info-box').innerText;
  navigator.clipboard.writeText(txt).then(function(){
    var b = document.querySelector('.copy-btn');
    b.textContent = 'Copied!';
    setTimeout(function(){ b.textContent = 'Copy'; }, 1500);
  });
}

// ─── Tab meta caption ────────────────────────────────────────────────────────
function buildMeta(d) {
  var items = [
    ['Location', d.location],
    ['Coords', d.moment.latitude.toFixed(2) + ', ' + d.moment.longitude.toFixed(2)],
    ['Tz', d.moment.timezone],
    ['Sys', d.zodiac_system]
  ];
  if (d.ayanamsa != null) items.push(['Ayan', fmtDeg(d.ayanamsa)]);
  document.getElementById('tab-meta').innerHTML = items.map(function(x){
    return '<span>' + x[0] + ': <b>' + x[1] + '</b></span>';
  }).join('');
}

// ─── Tab switcher ────────────────────────────────────────────────────────────
// Auto-collapse the welcome quotes banner after a few seconds.
// Clicking the banner collapses it immediately; clicking the peek bar re-opens it.
(function initIntroBanner(){
  var banner = document.getElementById('intro-banner');
  var peek = document.getElementById('intro-peek');
  if (!banner || !peek) return;

  function collapse() {
    banner.classList.add('collapsed');
    peek.classList.add('show');
  }
  function expand() {
    banner.classList.remove('collapsed');
    peek.classList.remove('show');
  }

  setTimeout(collapse, 6000);
  banner.addEventListener('click', collapse);
  peek.addEventListener('click', expand);
})();

(function initTabs(){
  var tabs = document.querySelectorAll('.tab');
  var chartFormEl   = document.getElementById('chart-form');
  var synTbFormEl   = document.getElementById('syn-toolbar-form');
  var toolbarEl     = document.getElementById('toolbar');

  tabs.forEach(function(btn){
    btn.addEventListener('click', function(){
      var name = btn.dataset.tab;
      tabs.forEach(function(b){ b.classList.toggle('active', b === btn); });
      document.querySelectorAll('.tab-page').forEach(function(p){
        p.classList.toggle('active', p.id === 'tab-' + name);
      });

      // Swap toolbar form: synastry gets its own two-person form
      var isSyn = name === 'synastry';
      if (chartFormEl) chartFormEl.style.display = isSyn ? 'none' : '';
      if (synTbFormEl) synTbFormEl.style.display  = isSyn ? '' : 'none';
      if (toolbarEl)   toolbarEl.classList.toggle('toolbar--synastry', isSyn);

      // On the Natal tab, show empty state if no chart loaded yet.
      if (name === 'natal') {
        var ne = document.getElementById('natal-empty-state');
        var nc = document.getElementById('natal-content');
        if (ne) ne.style.display = LAST_DATA ? 'none' : 'flex';
        if (nc) nc.style.display = LAST_DATA ? 'block' : 'none';
      }
      // Returning to Natal: redraw the wheel (canvas was sized 0×0 while hidden).
      if (name === 'natal' && LAST_DATA) {
        requestAnimationFrame(function(){
          drawCurrentWheel();
          if (SELECTED_HARMONIC != null && LAST_HARMONICS) renderHarmDetail(SELECTED_HARMONIC);
        });
      }
      // Redraw synastry canvases on re-entry.
      if (name === 'synastry' && LAST_SYN_DATA) {
        requestAnimationFrame(function(){
          drawBiWheel(LAST_SYN_DATA.chart_a, LAST_SYN_DATA.chart_b, LAST_SYN_DATA.cross_aspects, LAST_SYN_DATA._nameA, LAST_SYN_DATA._nameB);
          drawCompositeWheel(LAST_SYN_DATA.composite_bodies, LAST_SYN_DATA.composite_aspects);
        });
      }
    });
  });
})();

// ─── Patterns display ────────────────────────────────────────────────────────
var PAT_ICONS = {
  'Grand Trine':       '△',
  'T-Square':          '⊤',
  'Yod':               '🔻',
  'Grand Cross':       '✛',
  'Kite':              '◇',
  'Mystic Rectangle':  '▭',
};
var PAT_TYPES = ['Grand Trine', 'T-Square', 'Yod', 'Grand Cross', 'Kite', 'Mystic Rectangle'];
var PAT_FILTER = {};
PAT_TYPES.forEach(function(t){ PAT_FILTER[t] = false; });


function redrawAll() {
  if (!LAST_DATA) return;
  drawWheel(LAST_DATA);
  renderWordCloud(LAST_DATA);
}

// CSS word cloud built from chart.traits (word + weight). Top-weighted
// "core" traits are rendered slightly larger and bolder; the rest sit at a
// compact size so a long list still fits the quadrant.
function renderWordCloud(d) {
  var el = document.getElementById('word-cloud');
  if (!el) return;
  var traits = (d && d.traits) || [];
  if (!traits.length) {
    el.innerHTML = '<div class="wc-empty">No personality themes derived for this chart.</div>';
    return;
  }
  var sorted = traits.slice().sort(function(a,b){ return (b.weight||1) - (a.weight||1); });
  var nCore = Math.min(6, sorted.length);
  var palette = ['#5a4e3c','#7a644a','#8b7355','#3a8a3a','#c0392b','#2e7e9e','#d4a017','#7d3c98'];
  el.innerHTML = sorted.map(function(t, i){
    var isCore = i < nCore;
    var size = isCore ? 12.5 : 9.5;
    var weight = isCore ? 700 : 500;
    var color = palette[i % palette.length];
    return '<span class="wc-word" style="font-size:' + size + 'px;font-weight:' + weight +
           ';color:' + color + '">' + t.word + '</span>';
  }).join('');
}

// ─── Harmonic resonance card ──────────────────────────────────────────────

var SELECTED_HARMONIC = null;
var LAST_HARMONICS = null;   // ranked[] from /harmonics response

// Per-body archetypal theme — used in the mini-wheel detail panel.
var BODY_THEMES = {
  Sun:        'core identity & vitality',
  Moon:       'emotions, instincts & inner needs',
  Mercury:    'mind, communication & learning',
  Venus:      'love, values & aesthetics',
  Mars:       'drive, action & assertion',
  Jupiter:    'expansion, optimism & belief',
  Saturn:     'discipline, structure & responsibility',
  Uranus:     'change, freedom & innovation',
  Neptune:    'imagination, dreams & dissolution',
  Pluto:      'transformation, depth & power',
  Chiron:     'the wound that becomes the healer',
  Asc:        'self-presentation and persona',
  Desc:       'partnerships and the other',
  MC:         'public role and life direction',
  IC:         'roots, home & inner foundation',
  Vertex:     'fated encounters',
  Fortune:    'natural flow of good fortune',
  'North Node': 'soul direction and growth',
  'South Node': 'familiar patterns to release',
  'True Node':  'soul direction and growth',
  'Mean Node':  'soul direction and growth'
};

function sortHarmonics(ranked, method) {
  var sorted = ranked.slice();
  if (method === 'sumclose') {
    sorted.sort(function(a, b) { return (b.SumClose || 0) - (a.SumClose || 0); });
  } else if (method === 'adjusted') {
    sorted.sort(function(a, b) { return (b.SumCloseAdj || 0) - (a.SumCloseAdj || 0); });
  } else {
    sorted.sort(function(a, b) {
      if (b.PairCount !== a.PairCount) return b.PairCount - a.PairCount;
      return (a.Tightest || 0) - (b.Tightest || 0);
    });
  }
  return sorted;
}

function renderHarmonics(ranked) {
  var emptyEl  = document.getElementById('harm-empty');
  var contentEl = document.getElementById('harm-content');
  var listEl   = document.getElementById('harm-list');
  var detailEl = document.getElementById('harm-detail-right');
  SELECTED_HARMONIC = null;
  LAST_HARMONICS = ranked;

  if (!ranked || !ranked.length) {
    emptyEl.style.display = 'flex';
    contentEl.style.display = 'none';
    return;
  }
  emptyEl.style.display = 'none';
  contentEl.style.display = 'flex';

  renderHarmonicsList();
}

function renderHarmonicsList() {
  if (!LAST_HARMONICS) return;
  var listEl   = document.getElementById('harm-list');
  var detailEl = document.getElementById('harm-detail-right');
  var hdrEl    = document.getElementById('harm-list-hdr');
  var rankBy   = (document.getElementById('harm-rank-by') || {}).value || 'pairs';

  var LABELS = {
    pairs:    'Ranked by pair count',
    sumclose: 'Ranked by total resonance (Σ closeness)',
    adjusted: 'Ranked by noise-adjusted score (Σ closeness ÷ √h)',
  };
  if (hdrEl) hdrEl.textContent = (LABELS[rankBy] || LABELS.pairs) + ' · click a row for meaning';

  var sorted = sortHarmonics(LAST_HARMONICS, rankBy);
  var metricKey = { pairs: 'PairCount', sumclose: 'SumClose', adjusted: 'SumCloseAdj' }[rankBy];
  var maxVal = sorted.length ? (sorted[0][metricKey] || 1) : 1;

  listEl.innerHTML = sorted.map(function(r, i) {
    var val = r[metricKey] || 0;
    var barW = Math.max(4, Math.round((val / maxVal) * 100));
    var label = 'H' + r.Harmonic + (r.Name && r.Name !== '—' ? ' · ' + r.Name : '');
    var hasMeaning = r.NatalMeaning && r.NatalMeaning !== 'nan' && r.NatalMeaning !== '';
    var metaStr = rankBy === 'pairs'
      ? r.PairCount + ' pairs · ' + (r.Tightest || 0).toFixed(3) + '°'
      : (rankBy === 'sumclose' ? 'Σ' : 'adj') + ' ' + val.toFixed(2) + ' · ' + r.PairCount + ' pairs';
    return (
      '<div class="harm-row' + (SELECTED_HARMONIC === r.Harmonic ? ' sel' : '') +
           '" data-harm="' + r.Harmonic + '" ' +
           (hasMeaning ? 'style="cursor:pointer"' : '') + '>' +
        '<div class="harm-row-num">' + (i+1) + '</div>' +
        '<div class="harm-row-name">' + label + '</div>' +
        '<div class="harm-row-bar-bg"><div class="harm-row-bar" style="width:' + barW + '%"></div></div>' +
        '<div class="harm-row-meta">' + metaStr + '</div>' +
      '</div>'
    );
  }).join('');

  detailEl.innerHTML = '<div class="harm-hint">Select a harmonic above to see its natal meaning.</div>';

  listEl.querySelectorAll('.harm-row').forEach(function(row) {
    row.addEventListener('click', function() {
      renderHarmDetail(parseInt(row.dataset.harm, 10));
    });
  });

  var mini = document.getElementById('harm-mini-canvas');
  if (mini) {
    var ctx = mini.getContext('2d');
    ctx.setTransform(1,0,0,1,0,0);
    ctx.clearRect(0, 0, mini.width, mini.height);
  }
}

function renderHarmDetail(harmonic) {
  if (!LAST_HARMONICS) return;
  SELECTED_HARMONIC = harmonic;

  document.querySelectorAll('.harm-row').forEach(function(r) {
    r.classList.toggle('sel', parseInt(r.dataset.harm, 10) === harmonic);
  });

  var row = LAST_HARMONICS.find(function(r) { return r.Harmonic === harmonic; });
  if (!row) return;

  var name = row.Name && row.Name !== '—' ? row.Name : 'H' + harmonic;
  var factors = row.Factors ? ' <span style="font-size:10px;color:#9b9185;font-weight:400">(' + row.Factors + ')</span>' : '';

  var html = '<div class="harm-title">H' + harmonic + ' · ' + name + factors + '</div>';

  var meaning = row.NatalMeaning && row.NatalMeaning !== 'nan' ? row.NatalMeaning : '';
  if (meaning) {
    html += '<div class="harm-meaning">' + meaning + '</div>';
  }

  if (row.Pairs) {
    var pairs = row.Pairs.split(',  ').map(function(p) { return p.trim(); }).filter(Boolean);
    html += '<div class="harm-asp-label">' + row.PairCount + ' resonating pair' + (row.PairCount===1?'':'s') + '</div>';
    html += pairs.map(function(p) {
      var m = p.match(/^(.*?)\s+([\d.]+°)$/);
      var pairName = m ? m[1] : p;
      var orb = m ? m[2] + '°' : '';
      return '<div class="harm-asp-item">' +
        '<div class="harm-asp-head">' + pairName +
          (orb ? ' <span class="asp-close">&middot; ' + orb + ' off exact</span>' : '') +
        '</div>' +
      '</div>';
    }).join('');
  }

  if (row.Source && row.Source !== 'nan') {
    html += '<div style="font-size:9px;color:#b09e82;margin-top:10px;font-style:italic">' + row.Source + '</div>';
  }

  document.getElementById('harm-detail-right').innerHTML = html;

  drawHarmMini(LAST_DATA, harmonic);
}

// Plot the H-h harmonic chart: every planet's longitude is multiplied by h
// and taken mod 360. Pairs that were 360/h apart in the natal chart land on
// top of each other in this view — those are the H-h resonances, drawn as
// conjunction lines.
function drawHarmMini(data, harmonic) {
  var cvs = document.getElementById('harm-mini-canvas');
  if (!cvs) return;
  var h = harmonic || 1;
  var parent = cvs.parentElement;
  var dpr = window.devicePixelRatio || 1;
  var W = parent.clientWidth, H = parent.clientHeight;
  if (W < 20 || H < 20) return;
  cvs.width = W * dpr; cvs.height = H * dpr;
  cvs.style.width = W + 'px'; cvs.style.height = H + 'px';
  var ctx = cvs.getContext('2d');
  ctx.setTransform(1,0,0,1,0,0);
  ctx.scale(dpr, dpr);

  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, W, H);

  var cx = W/2, cy = H/2;
  var R = Math.min(cx, cy) - 14;
  var rSignOut = R;
  var rSignIn  = R * 0.83;
  var rOuter   = R * 0.83;
  var rInner   = R * 0.66;
  var rPlanet  = (rOuter + rInner) / 2;
  var rLine    = rInner;

  // Rotate so the harmonic-chart Desc sits at 3 o'clock for consistency
  // with the natal wheel layout. Desc longitude is also multiplied by h.
  var desc = data.bodies.find(function(b){ return b.Body === 'Desc'; });
  var rotLon = desc ? ((desc['Longitude (°)'] * h) % 360 + 360) % 360 : 0;
  function lon2a(lon){ return -(lon - rotLon) * Math.PI / 180; }
  function pt(r, a){ return [cx + r*Math.cos(a), cy + r*Math.sin(a)]; }

  // ── zodiac sign band
  for (var i = 0; i < 12; i++) {
    var sa1 = lon2a(i * 30);
    var sa2 = lon2a((i + 1) * 30);
    ctx.beginPath();
    ctx.arc(cx, cy, rSignOut, sa1, sa2, true);
    ctx.arc(cx, cy, rSignIn,  sa2, sa1, false);
    ctx.closePath();
    ctx.fillStyle = '#fafaf7';
    ctx.fill();
    ctx.strokeStyle = '#ccc'; ctx.lineWidth = 0.5; ctx.stroke();

    var midA = lon2a(i * 30 + 15);
    var mr   = (rSignOut + rSignIn) / 2;
    var sgp  = pt(mr, midA);
    ctx.save();
    ctx.translate(sgp[0], sgp[1]);
    ctx.rotate(midA + Math.PI / 2);
    ctx.font = Math.round(R * 0.09) + 'px sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillStyle = SIGN_GLYPH_COLS[i];
    ctx.fillText(SIGN_ABBR_W[i], 0, 0);
    ctx.restore();
  }

  // ── main rings
  ctx.strokeStyle = '#bbb'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.arc(cx, cy, rOuter, 0, 2*Math.PI); ctx.stroke();
  ctx.beginPath(); ctx.arc(cx, cy, rInner, 0, 2*Math.PI); ctx.stroke();

  // Show all 10 main planets at their h-chart positions.
  var PLANETS = ['Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn','Uranus','Neptune','Pluto'];
  var bodyPos = {};   // angle on the canvas
  var bodyLonH = {};  // raw H-h longitude (mod 360), for orb math
  data.bodies.forEach(function(b){
    if (PLANETS.indexOf(b.Body) === -1) return;
    var lonH = ((b['Longitude (°)'] * h) % 360 + 360) % 360;
    bodyLonH[b.Body] = lonH;
    bodyPos[b.Body] = lon2a(lonH);
  });

  // Draw aspects in the h-chart. Each planet is at its harmonic-chart
  // position (lon × h mod 360); we check standard aspect angles between them.
  var MINI_ASPECTS = [
    { deg: 0,   orb: 8, color: '#27ae60' },  // conjunction
    { deg: 180, orb: 6, color: '#e74c3c' },  // opposition
    { deg: 120, orb: 5, color: '#3498db' },  // trine
    { deg: 90,  orb: 4, color: '#e67e22' },  // square
    { deg: 60,  orb: 3, color: '#9b59b6' },  // sextile
  ];
  var names = Object.keys(bodyLonH);
  for (var i = 0; i < names.length; i++) {
    for (var j = i + 1; j < names.length; j++) {
      var diff0 = Math.abs(bodyLonH[names[i]] - bodyLonH[names[j]]);
      var sep = Math.min(diff0, 360 - diff0);
      for (var k = 0; k < MINI_ASPECTS.length; k++) {
        var asp = MINI_ASPECTS[k];
        var adiff = Math.abs(sep - asp.deg);
        if (adiff > asp.orb) continue;
        var closeness = 1 - adiff / asp.orb;
        var a1 = bodyPos[names[i]], a2 = bodyPos[names[j]];
        var p1 = pt(rLine, a1), p2 = pt(rLine, a2);
        ctx.beginPath();
        ctx.moveTo(p1[0], p1[1]); ctx.lineTo(p2[0], p2[1]);
        ctx.strokeStyle = asp.color;
        ctx.lineWidth = Math.max(1.0, closeness * 2.5);
        ctx.globalAlpha = 0.35 + closeness * 0.55;
        ctx.stroke();
        ctx.globalAlpha = 1;
        break;
      }
    }
  }

  // Cluster offset for planets nearly on top of each other in the h-chart
  // (which is exactly what a tight H-h resonance looks like). Stagger their
  // symbols slightly inward so glyphs don't overlap.
  var sorted = names.slice().sort(function(x, y){ return bodyLonH[x] - bodyLonH[y]; });
  var placements = [];
  var lastLon = -1e9, stack = 0;
  sorted.forEach(function(name){
    var lon = bodyLonH[name];
    stack = (lon - lastLon < 4) ? Math.min(stack + 1, 3) : 0;
    lastLon = lon;
    placements.push({ name: name, r: rPlanet - stack * R * 0.08 });
  });

  placements.forEach(function(it){
    var ang = bodyPos[it.name];
    var b = data.bodies.find(function(x){ return x.Body === it.name; });
    if (!b) return;
    var p = pt(it.r, ang);
    var sym = b.Symbol || it.name.substring(0, 2);
    ctx.font = 'bold ' + Math.round(R * 0.11) + 'px serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.lineWidth = 3.5; ctx.strokeStyle = '#fff';
    ctx.strokeText(sym, p[0], p[1]);
    ctx.fillStyle = '#000';
    ctx.fillText(sym, p[0], p[1]);
  });

  // ── Asc / Desc / MC / IC at their h-chart positions
  var ANGLE_ABBR = { Asc: 'Ac', Desc: 'Dc', MC: 'MC', IC: 'IC' };
  ['Asc','Desc','MC','IC'].forEach(function(name) {
    var b = data.bodies.find(function(x){ return x.Body === name; });
    if (!b) return;
    var lonH = ((b['Longitude (°)'] * h) % 360 + 360) % 360;
    var aa   = lon2a(lonH);
    var ip   = pt(rLine, aa), ap = pt(rSignIn, aa);
    ctx.beginPath();
    ctx.moveTo(ip[0], ip[1]); ctx.lineTo(ap[0], ap[1]);
    ctx.strokeStyle = '#333'; ctx.lineWidth = 1.5; ctx.stroke();

    var lp  = pt(rOuter - R * 0.035, aa);
    var rot = aa;
    if (Math.cos(rot) < 0) rot += Math.PI;
    ctx.save();
    ctx.translate(lp[0], lp[1]);
    ctx.rotate(rot);
    ctx.font = 'bold ' + Math.round(R * 0.085) + 'px sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.lineWidth = 3; ctx.strokeStyle = '#fff';
    ctx.strokeText(ANGLE_ABBR[name], 0, 0);
    ctx.fillStyle = '#333';
    ctx.fillText(ANGLE_ABBR[name], 0, 0);
    ctx.restore();
  });

  // "Hn" label in the centre so the user knows which harmonic chart this is.
  ctx.fillStyle = '#b09e82';
  ctx.font = 'bold ' + Math.round(R * 0.22) + 'px sans-serif';
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText('H' + h, cx, cy);
}

// Click delegation for harm-list rows
(function initHarmClick(){
  var listEl = document.getElementById('harm-list');
  if (!listEl) return;
  listEl.addEventListener('click', function(e){
    var row = e.target.closest('.harm-row');
    if (!row) return;
    var h = parseInt(row.dataset.harm, 10);
    if (!isNaN(h)) renderHarmDetail(h);
  });
})();


// Backwards-compat alias used by older redraw call sites
function drawCurrentWheel() { redrawAll(); }


(function initFilters(){
  var fp = document.getElementById('filter-panel');

  // Build aspect checkboxes inline (Cochrane harmonic-multiple entries are
  // hidden — they live in the Vibrational Resonance card)
  document.getElementById('asp-list').innerHTML = ASP_TYPES
    .filter(function(t){ return t.inAspPanel; })
    .map(function(t){
      var checked = ASP_FILTER[t.name] ? 'checked' : '';
      return '<label><input type="checkbox" data-asp="' + t.name + '" ' + checked +
             '><span class="fp-asp-glyph">' + t.sym + '</span>' + t.name + '</label>';
    }).join('');

  function renderPatFilter() {
    var el = document.getElementById('pat-filter-list');
    if (!el) return;
    el.innerHTML = PAT_TYPES.map(function(t){
      var cls = PAT_FILTER[t] ? 'pat-btn on' : 'pat-btn';
      var label = (PAT_ICONS[t] || '') + ' ' + t;
      return '<button type="button" class="' + cls + '" data-pat="' + t + '" title="' + t + '">' + label + '</button>';
    }).join('');
  }
  renderPatFilter();

  // Gear button: collapse/expand filter panel. Redraw after the CSS width
  // transition (.2s) finishes so the canvas matches the final layout, not an
  // intermediate transitional size.
  document.getElementById('gear-btn').addEventListener('click', function(){
    fp.classList.toggle('closed');
    if (LAST_DATA) setTimeout(drawCurrentWheel, 220);
  });

  // Dismiss the "showing major aspects only" note (manually or as soon as
  // the user touches the aspect filter at all).
  function hideChartNote() {
    var n = document.getElementById('chart-note');
    if (n) n.style.display = 'none';
  }
  var noteX = document.getElementById('chart-note-x');
  if (noteX) noteX.addEventListener('click', hideChartNote);

  // All checkbox changes delegated to filter panel
  fp.addEventListener('change', function(e){
    var cb = e.target;
    if (!cb || cb.tagName !== 'INPUT') return;
    if (cb.dataset.asp) {
      ASP_FILTER[cb.dataset.asp] = cb.checked;
      hideChartNote();
    } else if (cb.dataset.dispName) {
      BODY_DISPLAY[cb.dataset.dispName] = cb.checked;
    } else if (cb.dataset.disp) {
      // Display covers both showing the body and including its aspects.
      var key = cb.dataset.disp;
      BODY_DISPLAY[key] = cb.checked;
      ASPECT_TO[key] = cb.checked;
    }
    if (LAST_DATA) drawCurrentWheel();
  });

  // All button clicks delegated to filter panel
  fp.addEventListener('click', function(e){
    // Aspect bulk
    var aspBulk = e.target.closest('button[data-asp-bulk]');
    if (aspBulk) {
      var mode = aspBulk.dataset.aspBulk;
      fp.querySelectorAll('input[data-asp]').forEach(function(cb){
        var t = ASP_TYPES.find(function(x){ return x.name === cb.dataset.asp; });
        var on = mode === 'all' || (mode === 'major' && t && t.major) || (mode === 'minor' && t && !t.major);
        cb.checked = on;
        ASP_FILTER[cb.dataset.asp] = on;
      });
      hideChartNote();
      if (LAST_DATA) drawCurrentWheel();
      return;
    }
    // Pattern bulk (All / None)
    var patBulk = e.target.closest('button[data-pat-bulk]');
    if (patBulk) {
      var on2 = patBulk.dataset.patBulk === 'all';
      PAT_TYPES.forEach(function(t){ PAT_FILTER[t] = on2; });
      renderPatFilter();
      if (LAST_DATA) drawCurrentWheel();
      return;
    }
    // Pattern button toggle
    var patBtn = e.target.closest('.pat-btn[data-pat]');
    if (patBtn) {
      PAT_FILTER[patBtn.dataset.pat] = !PAT_FILTER[patBtn.dataset.pat];
      renderPatFilter();
      if (LAST_DATA) drawCurrentWheel();
      return;
    }
    // Display bulk
    var bulk = e.target.closest('button[data-bulk="disp"]');
    if (bulk) {
      var on3 = bulk.dataset.bulkState === 'all';
      fp.querySelectorAll('input[data-disp-name]').forEach(function(cb){
        cb.checked = on3; BODY_DISPLAY[cb.dataset.dispName] = on3;
      });
      fp.querySelectorAll('input[data-disp]').forEach(function(cb){
        cb.checked = on3;
        BODY_DISPLAY[cb.dataset.disp] = on3;
        ASPECT_TO[cb.dataset.disp] = on3;
      });
      if (LAST_DATA) drawCurrentWheel();
      return;
    }
  });

  // Orb sliders
  function fmtOrb(v) {
    return v.toFixed(1) + '°';
  }
  function bindOrb(id, readoutId, setter) {
    var el = document.getElementById(id);
    var read = document.getElementById(readoutId);
    function update() {
      var v = parseFloat(el.value);
      if (!isFinite(v)) return;
      setter(v);
      read.textContent = fmtOrb(v);
      if (LAST_DATA) drawCurrentWheel();
    }
    el.addEventListener('input', update);
  }
  bindOrb('major-orb-val', 'major-orb-readout', function(v){ MAJOR_ORB_VAL = v; });
  bindOrb('minor-orb-val', 'minor-orb-readout', function(v){ MINOR_ORB_VAL = v; });

  document.getElementById('house-system').addEventListener('change', function(){
    if (LAST_DATA) document.getElementById('chart-form').requestSubmit();
  });

  document.getElementById('zodiac').addEventListener('change', function(){
    if (this.value === 'Sidereal') document.getElementById('house-system').value = 'Whole Sign';
  });

  window.addEventListener('resize', function(){
    if (LAST_DATA) {
      requestAnimationFrame(drawCurrentWheel);
      if (SELECTED_HARMONIC != null) requestAnimationFrame(function(){ renderHarmDetail(SELECTED_HARMONIC); });
    }
  });
})();

// ─── Pattern tooltip (hover over highlighted aspects) ────────────────────────
(function initPatTooltip(){
  var cvs = document.getElementById('wheel-canvas');
  var tip = document.getElementById('pat-tooltip');
  if (!cvs || !tip) return;

  function distSeg(px, py, x1, y1, x2, y2) {
    var dx = x2-x1, dy = y2-y1, l2 = dx*dx+dy*dy;
    if (!l2) return Math.sqrt((px-x1)*(px-x1)+(py-y1)*(py-y1));
    var t = Math.max(0,Math.min(1,((px-x1)*dx+(py-y1)*dy)/l2));
    return Math.sqrt((px-x1-t*dx)*(px-x1-t*dx)+(py-y1-t*dy)*(py-y1-t*dy));
  }

  cvs.addEventListener('mousemove', function(e){
    if (!PAT_SEGMENTS.length){ tip.classList.remove('vis'); return; }
    var mx = e.offsetX, my = e.offsetY;
    var best = null, bd = 14;
    for (var i = 0; i < PAT_SEGMENTS.length; i++){
      var s = PAT_SEGMENTS[i];
      var d = distSeg(mx, my, s.x1, s.y1, s.x2, s.y2);
      if (d < bd){ bd = d; best = s; }
    }
    if (!best){ tip.classList.remove('vis'); return; }
    var pats = best.pats || [];
    var html = pats.map(function(p){
      return '<div class="pt-type">' + (PAT_ICONS[p.type]||'◉') + ' ' + p.type + '</div>' +
             '<div class="pt-bodies">' + p.bodies.join(' · ') + (p.apex ? ' — apex: '+p.apex : '') + '</div>' +
             '<div class="pt-score">' + Math.round(p.score*100) + '% tight</div>' +
             '<div class="pt-desc">' + p.description + '</div>';
    }).join('<div style="border-top:1px solid #f0ece7;margin:5px 0"></div>');
    if (!html){ tip.classList.remove('vis'); return; }
    tip.innerHTML = html;
    var cw = cvs.offsetWidth, ch = cvs.offsetHeight;
    var tx = mx+14, ty = my-10;
    if (tx+220 > cw) tx = mx-228;
    if (ty+130 > ch) ty = ch-130;
    if (ty < 0) ty = 0;
    tip.style.left = tx+'px'; tip.style.top = ty+'px';
    tip.classList.add('vis');
  });
  cvs.addEventListener('mouseleave', function(){ tip.classList.remove('vis'); });
})();

// ─── Auto-fetch natal harmonics after chart loads ────────────────────────────
function fetchNatalHarmonics(d, chartParams) {
  var loadingEl = document.getElementById('harm-loading');
  if (loadingEl) loadingEl.style.display = 'inline';
  document.getElementById('harm-empty').style.display = 'flex';
  document.getElementById('harm-empty').textContent = 'Computing harmonic resonances…';
  document.getElementById('harm-content').style.display = 'none';

  var payload = {
    birth_datetime: chartParams.birth_datetime,
    location: chartParams.location,
    zodiac_system: chartParams.zodiac_system,
    house_system: chartParams.house_system,
    base_orb: chartParams.base_orb,
    orb_formula: chartParams.orb_formula,
    active_bodies: ['Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn','Uranus','Neptune','Pluto'],
    max_harmonic: 32,
    min_tightness_pct: 0,
    personal_only: true,
  };

  fetch('/harmonics', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload) })
    .then(function(r){ return r.ok ? r.json() : r.json().then(function(e){ throw new Error(e.detail); }); })
    .then(function(data){ renderHarmonics(data.ranked || []); })
    .catch(function(){ renderHarmonics([]); })
    .finally(function(){ if (loadingEl) loadingEl.style.display = 'none'; });
}

// ─── Harm-orb slider: live readout + debounced re-fetch ──────────────────────
(function(){
  var slider = document.getElementById('harm-base-orb');
  var readout = document.getElementById('harm-base-orb-val');
  if (!slider) return;

  slider.addEventListener('input', function(){
    if (readout) readout.textContent = slider.value + '°';
  });

  var refetchTimer = null;
  slider.addEventListener('change', function(){
    if (!LAST_DATA || !LAST_HARM_PARAMS) return;
    clearTimeout(refetchTimer);
    refetchTimer = setTimeout(function(){
      var p = Object.assign({}, LAST_HARM_PARAMS, { base_orb: parseFloat(slider.value) });
      fetchNatalHarmonics(LAST_DATA, p);
    }, 200);
  });
})();

// ─── Harm rank-by dropdown: re-sort client-side, no re-fetch ─────────────────
(function(){
  var sel = document.getElementById('harm-rank-by');
  if (!sel) return;
  sel.addEventListener('change', function(){ renderHarmonicsList(); });
})();

// ─── Form submit ─────────────────────────────────────────────────────────────
(function(){
  var form       = document.getElementById('chart-form');
  var spinner    = document.getElementById('spinner');
  var errBar     = document.getElementById('error-bar');
  var btn        = document.getElementById('submit-btn');
  var natalEmpty = document.getElementById('natal-empty-state');
  var natalCont  = document.getElementById('natal-content');

  // Show the natal empty state on first load (no chart yet).
  if (natalEmpty) natalEmpty.style.display = 'flex';
  if (natalCont)  natalCont.style.display  = 'none';

  form.addEventListener('submit', function(e){
    e.preventDefault();
    errBar.style.display = 'none';
    if (natalEmpty) natalEmpty.style.display = 'none';
    spinner.style.display = 'block';
    btn.disabled = true;

    // Unknown-time mode: assume noon, hide Angles/Points
    var unknownTime = document.getElementById('unknown-time') && document.getElementById('unknown-time').checked;
    var timeVal = unknownTime ? '12:00' : document.getElementById('birth-time').value;
    if (unknownTime) {
      BODY_DISPLAY.Angles = false;
      BODY_DISPLAY.Points = false;
      UNKNOWN_TIME_MOON_RANGE = null;
    }

    // Shared location/time fields used by both requests below.
    var birth_datetime = document.getElementById('birth-date').value + 'T' + timeVal + ':00';
    var location       = document.getElementById('location').value.trim();
    var zodiac_system  = document.getElementById('zodiac').value;
    var house_system   = document.getElementById('house-system').value;

    // Natal wheel aspects: use a generous fixed orb so every aspect type
    // shares the same OrbLimit. This lets the filter-panel major/minor
    // sliders filter uniformly — moving the slider has the same effect
    // on trines, squares, sextiles, etc., not just conjunctions.
    var chartReq = {
      birth_datetime: birth_datetime,
      location: location,
      zodiac_system: zodiac_system,
      house_system: house_system,
      base_orb: 10.0,
      orb_formula: 'fixed',
      website: document.getElementById('hp-website').value,
    };

    // Natal harmonic resonance: orb is user-adjustable via #harm-base-orb.
    var harmOrbEl = document.getElementById('harm-base-orb');
    var harmParams = {
      birth_datetime: birth_datetime,
      location: location,
      zodiac_system: zodiac_system,
      house_system: house_system,
      base_orb: harmOrbEl ? parseFloat(harmOrbEl.value) : 8.0,
      orb_formula: 'sqrt',
    };

    fetch('/chart', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(chartReq) })
      .then(function(r){
        if (!r.ok) return r.json().then(function(d){ throw new Error(d.detail || 'Failed'); });
        return r.json();
      })
      .then(function(d){
        spinner.style.display = 'none'; btn.disabled = false;
        LAST_DATA = d;
        LAST_HARM_PARAMS = harmParams;
        buildMeta(d);
        buildInfoBox(d);
        renderWordCloud(d);
        if (natalCont) natalCont.style.display = 'block';

        if (unknownTime) {
          // Fetch midnight chart to get moon range for the full day
          var dateStr = document.getElementById('birth-date').value;
          var midnightDt = dateStr + 'T00:00:00';
          var midnightReq = { birth_datetime: midnightDt, location: location,
            zodiac_system: zodiac_system, house_system: house_system,
            base_orb: 10.0, orb_formula: 'fixed', website: '' };
          fetch('/chart', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(midnightReq) })
            .then(function(r){ return r.ok ? r.json() : null; })
            .then(function(md) {
              if (md) {
                var moonNoon = (d.bodies.find(function(b){ return b.Body === 'Moon'; }) || {})['Longitude (°)'] || 0;
                var moonMid  = (md.bodies.find(function(b){ return b.Body === 'Moon'; }) || {})['Longitude (°)'] || 0;
                // Linear: noon is 12h after midnight; project to 24h end
                var span = ((moonNoon - moonMid) + 360) % 360;
                if (span > 180) span -= 360; // handle wrap
                var moonEnd = (moonNoon + span + 360) % 360;
                UNKNOWN_TIME_MOON_RANGE = { start: moonMid, end: moonEnd };
              }
              requestAnimationFrame(redrawAll);
            })
            .catch(function(){ requestAnimationFrame(redrawAll); });
        } else {
          UNKNOWN_TIME_MOON_RANGE = null;
          requestAnimationFrame(redrawAll);
        }

        fetchNatalHarmonics(d, harmParams);
      })
      .catch(function(ex){
        spinner.style.display = 'none'; btn.disabled = false;
        errBar.textContent = ex.message || 'Network error';
        errBar.style.display = 'block';
        if (natalEmpty && !LAST_DATA) natalEmpty.style.display = 'flex';
      });
  });
})();

// ─── Synastry tab ─────────────────────────────────────────────────────────────

var LAST_SYN_DATA = null;
var LAST_SYN_HARM_PARAMS = null;

// Composite filter state
var COMP_MAJOR_ORB = 8;
var COMP_MINOR_ORB = 4;
var COMP_ASP_FILTER = {};
var COMP_BODY = {};

function initCompFilters() {
  ASP_TYPES.forEach(function(a) {
    if (!(a.name in COMP_ASP_FILTER)) COMP_ASP_FILTER[a.name] = a.defaultOn;
  });

  document.querySelectorAll('.comp-disp').forEach(function(cb) {
    COMP_BODY[cb.dataset.body] = cb.checked;
    cb.addEventListener('change', function() {
      COMP_BODY[cb.dataset.body] = cb.checked;
      compRedraw();
    });
  });

  var majSl = document.getElementById('comp-major-orb');
  var majRd = document.getElementById('comp-major-orb-readout');
  var minSl = document.getElementById('comp-minor-orb');
  var minRd = document.getElementById('comp-minor-orb-readout');
  if (majSl) majSl.addEventListener('input', function() {
    COMP_MAJOR_ORB = parseFloat(majSl.value);
    if (majRd) majRd.textContent = COMP_MAJOR_ORB.toFixed(1) + '°';
    compRedraw();
  });
  if (minSl) minSl.addEventListener('input', function() {
    COMP_MINOR_ORB = parseFloat(minSl.value);
    if (minRd) minRd.textContent = COMP_MINOR_ORB.toFixed(1) + '°';
    compRedraw();
  });

  var gear = document.getElementById('comp-gear-btn');
  var panel = document.getElementById('comp-filter-panel');
  if (gear && panel) {
    gear.addEventListener('click', function() {
      panel.classList.toggle('closed');
      setTimeout(compRedraw, 280);
    });
  }

  var aspList = document.getElementById('comp-asp-list');
  if (aspList) {
    ASP_TYPES.filter(function(a) { return a.inAspPanel; }).forEach(function(a) {
      var lbl = document.createElement('label');
      var cb  = document.createElement('input');
      cb.type = 'checkbox';
      cb.dataset.compAsp = a.name;
      cb.checked = a.defaultOn;
      COMP_ASP_FILTER[a.name] = a.defaultOn;
      cb.addEventListener('change', function() {
        COMP_ASP_FILTER[a.name] = cb.checked;
        compRedraw();
      });
      lbl.appendChild(cb);
      lbl.appendChild(document.createTextNode(' ' + a.name + ' ' + a.sym));
      aspList.appendChild(lbl);
    });
  }
}

function compBulkBody(state) {
  document.querySelectorAll('.comp-disp').forEach(function(cb) {
    cb.checked = (state === 'all');
    COMP_BODY[cb.dataset.body] = cb.checked;
  });
  compRedraw();
}

function compBulkAsp(state) {
  document.querySelectorAll('[data-comp-asp]').forEach(function(cb) {
    var a = ASP_TYPES.find(function(x){ return x.name === cb.dataset.compAsp; });
    cb.checked = state === 'all' ? true : state === 'none' ? false : (a && a.major);
    COMP_ASP_FILTER[cb.dataset.compAsp] = cb.checked;
  });
  compRedraw();
}

function compRedraw() {
  if (!LAST_SYN_DATA) return;
  drawCompositeWheel(LAST_SYN_DATA.composite_bodies, LAST_SYN_DATA.composite_aspects);
}

// Synastry filter state
var SYN_MAJOR_ORB = 8;
var SYN_MINOR_ORB = 4;
var SYN_ASP_FILTER = {};  // aspect name → bool, populated in initSynFilters
var SYN_BODY_A = {};      // body name → bool
var SYN_BODY_B = {};

function initSynFilters() {
  // Aspect filter defaults: same as natal wheel
  ASP_TYPES.forEach(function(a) {
    if (!(a.name in SYN_ASP_FILTER)) SYN_ASP_FILTER[a.name] = a.defaultOn;
  });

  // Body defaults: all checked bodies
  document.querySelectorAll('.syn-disp-a').forEach(function(cb) {
    SYN_BODY_A[cb.dataset.body] = cb.checked;
    cb.addEventListener('change', function() {
      SYN_BODY_A[cb.dataset.body] = cb.checked;
      synRedrawBiWheel();
    });
  });
  document.querySelectorAll('.syn-disp-b').forEach(function(cb) {
    SYN_BODY_B[cb.dataset.body] = cb.checked;
    cb.addEventListener('change', function() {
      SYN_BODY_B[cb.dataset.body] = cb.checked;
      synRedrawBiWheel();
    });
  });

  // Orb sliders
  var majSl = document.getElementById('syn-major-orb');
  var majRd = document.getElementById('syn-major-orb-readout');
  var minSl = document.getElementById('syn-minor-orb');
  var minRd = document.getElementById('syn-minor-orb-readout');
  if (majSl) majSl.addEventListener('input', function() {
    SYN_MAJOR_ORB = parseFloat(majSl.value);
    majRd.textContent = SYN_MAJOR_ORB.toFixed(1) + '°';
    synRedrawBiWheel();
  });
  if (minSl) minSl.addEventListener('input', function() {
    SYN_MINOR_ORB = parseFloat(minSl.value);
    minRd.textContent = SYN_MINOR_ORB.toFixed(1) + '°';
    synRedrawBiWheel();
  });

  // Gear button — toggle filter, redraw after CSS transition finishes
  var gear = document.getElementById('syn-gear-btn');
  var panel = document.getElementById('syn-filter-panel');
  if (gear && panel) {
    gear.addEventListener('click', function() {
      panel.classList.toggle('closed');
      setTimeout(synRedrawBiWheel, 280);
    });
  }

  // Build aspect checkboxes in #syn-asp-list
  var aspList = document.getElementById('syn-asp-list');
  if (aspList) {
    ASP_TYPES.filter(function(a) { return a.inAspPanel; }).forEach(function(a) {
      var lbl = document.createElement('label');
      var cb  = document.createElement('input');
      cb.type = 'checkbox';
      cb.dataset.synAsp = a.name;
      cb.checked = a.defaultOn;
      SYN_ASP_FILTER[a.name] = a.defaultOn;
      cb.addEventListener('change', function() {
        SYN_ASP_FILTER[a.name] = cb.checked;
        synRedrawBiWheel();
      });
      lbl.appendChild(cb);
      lbl.appendChild(document.createTextNode(' ' + a.name + ' ' + a.sym));
      aspList.appendChild(lbl);
    });
  }
}

function synBulkBody(person, state) {
  var cls = person === 'a' ? '.syn-disp-a' : '.syn-disp-b';
  var map = person === 'a' ? SYN_BODY_A : SYN_BODY_B;
  document.querySelectorAll(cls).forEach(function(cb) {
    cb.checked = (state === 'all');
    map[cb.dataset.body] = cb.checked;
  });
  synRedrawBiWheel();
}

function synBulkAsp(state) {
  document.querySelectorAll('[data-syn-asp]').forEach(function(cb) {
    var a = ASP_TYPES.find(function(x){ return x.name === cb.dataset.synAsp; });
    cb.checked = state === 'all' ? true : state === 'none' ? false : (a && a.major);
    SYN_ASP_FILTER[cb.dataset.synAsp] = cb.checked;
  });
  synRedrawBiWheel();
}

function synRedrawBiWheel() {
  if (!LAST_SYN_DATA) return;
  drawBiWheel(
    LAST_SYN_DATA.chart_a, LAST_SYN_DATA.chart_b,
    LAST_SYN_DATA.cross_aspects,
    LAST_SYN_DATA._nameA, LAST_SYN_DATA._nameB
  );
}

document.addEventListener('DOMContentLoaded', function() {
  // Unknown birth time toggle
  var unknownCb = document.getElementById('unknown-time');
  var timeInput = document.getElementById('birth-time');
  if (unknownCb && timeInput) {
    unknownCb.addEventListener('change', function() {
      timeInput.disabled = unknownCb.checked;
      // Sync filter-panel checkboxes for Angles and Points
      var angCb = document.querySelector('[data-disp="Angles"]');
      var ptCb  = document.querySelector('[data-disp="Points"]');
      if (unknownCb.checked) {
        timeInput.dataset.savedVal = timeInput.value;
        timeInput.value = '12:00';
        if (angCb) { angCb.checked = false; angCb.disabled = true; BODY_DISPLAY.Angles = false; }
        if (ptCb)  { ptCb.checked  = false; ptCb.disabled  = true; BODY_DISPLAY.Points = false; }
      } else {
        timeInput.value = timeInput.dataset.savedVal || timeInput.value;
        if (angCb) { angCb.disabled = false; }
        if (ptCb)  { ptCb.disabled  = false; }
        UNKNOWN_TIME_MOON_RANGE = null;
        if (LAST_DATA) requestAnimationFrame(redrawAll);
      }
    });
  }

  // Toolbar orb slider readout for synastry
  var sl = document.getElementById('syn-orb-val');
  var rd = document.getElementById('syn-orb-readout');
  if (sl && rd) sl.addEventListener('input', function() { rd.textContent = parseFloat(sl.value).toFixed(1) + '°'; });

  var sl2 = document.getElementById('syn-harm-orb');
  var rd2 = document.getElementById('syn-harm-orb-val');
  if (sl2 && rd2) {
    sl2.addEventListener('input', function() {
      rd2.textContent = parseFloat(sl2.value).toFixed(0) + '°';
      if (LAST_SYN_HARM_PARAMS) synFetchHarmonics(parseFloat(sl2.value));
    });
  }
  var synRankSel = document.getElementById('syn-harm-rank-by');
  if (synRankSel) synRankSel.addEventListener('change', synRenderHarmonicsList);
  initSynFilters();
  initCompFilters();
});

function synCompute() {
  var aDate = document.getElementById('syn-a-date').value;
  var aTime = document.getElementById('syn-a-time').value;
  var aLoc  = document.getElementById('syn-a-loc').value.trim();
  var bDate = document.getElementById('syn-b-date').value;
  var bTime = document.getElementById('syn-b-time').value;
  var bLoc  = document.getElementById('syn-b-loc').value.trim();

  if (!aDate || !aTime || !aLoc || !bDate || !bTime || !bLoc) {
    alert('Please fill in all birth details for both people.');
    return;
  }

  var aName = document.getElementById('syn-a-name').value.trim() || 'Person A';
  var bName = document.getElementById('syn-b-name').value.trim() || 'Person B';
  var baseOrb = parseFloat(document.getElementById('syn-orb-val').value) || 8.0;
  var zodiacSys  = document.getElementById('syn-zodiac').value;
  var houseSys   = document.getElementById('syn-house').value;

  var payload = {
    person_a: {
      birth_datetime: aDate + 'T' + aTime + ':00',
      location: aLoc,
      zodiac_system: zodiacSys,
      house_system: houseSys,
      name: aName,
    },
    person_b: {
      birth_datetime: bDate + 'T' + bTime + ':00',
      location: bLoc,
      zodiac_system: zodiacSys,
      house_system: houseSys,
      name: bName,
    },
    base_orb: baseOrb,
    orb_formula: 'fixed',
  };

  var btn = document.getElementById('syn-compute-btn');
  btn.disabled = true;
  document.getElementById('syn-empty').style.display = 'none';
  document.getElementById('syn-results').style.display = 'none';
  document.getElementById('syn-spinner').style.display = 'block';

  fetch('/synastry', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) })
    .then(function(r) {
      if (!r.ok) return r.json().then(function(e){ throw new Error(e.detail || 'Server error'); });
      return r.json();
    })
    .then(function(data) {
      LAST_SYN_DATA = data;
      LAST_SYN_DATA._nameA = aName;
      LAST_SYN_DATA._nameB = bName;
      LAST_SYN_DATA._baseOrb = baseOrb;
      LAST_SYN_HARM_PARAMS = {
        person_a: payload.person_a,
        person_b: payload.person_b,
        base_orb: 8.0,
        orb_formula: 'sqrt',
      };
      document.getElementById('syn-spinner').style.display = 'none';
      document.getElementById('syn-results').style.display = 'block';
      synRender(data, aName, bName);
      synFetchHarmonics(8.0);
    })
    .catch(function(err) {
      document.getElementById('syn-spinner').style.display = 'none';
      document.getElementById('syn-empty').textContent = 'Error: ' + err.message;
      document.getElementById('syn-empty').style.display = 'block';
    })
    .finally(function() { btn.disabled = false; });
}

function synRender(data, nameA, nameB) {
  // Update legend names
  var legA = document.getElementById('syn-leg-a-name');
  var legB = document.getElementById('syn-leg-b-name');
  if (legA) legA.textContent = nameA;
  if (legB) legB.textContent = nameB;

  // Score
  var sc = data.score || {};
  var overall = sc.overall != null ? sc.overall : 50;
  var circle = document.getElementById('syn-score-circle');
  circle.textContent = Math.round(overall) + '%';
  circle.style.background = overall >= 65 ? '#27ae60' : overall >= 45 ? '#e67e22' : '#c0392b';
  document.getElementById('syn-score-summary').textContent = sc.summary || '';
  document.getElementById('syn-score-breakdown').innerHTML =
    '<div class="syn-score-row"><span>Harmonious</span><span>' + (sc.harmony || 0).toFixed(1) + '</span></div>' +
    '<div class="syn-score-row"><span>Tense</span><span>' + (sc.tension || 0).toFixed(1) + '</span></div>' +
    '<div class="syn-score-row"><span>Conjunctions</span><span>' + (sc.conjunction || 0).toFixed(1) + '</span></div>' +
    '<div class="syn-score-row"><span>Total cross-aspects</span><span>' + (sc.total_aspects || 0) + '</span></div>';

  // Cross-aspects table
  var tbody = document.getElementById('syn-cross-asp-tbody');
  tbody.innerHTML = '';
  var crossAsp = (data.cross_aspects || []).slice().sort(function(a, b){ return b.Closeness - a.Closeness; });
  document.getElementById('syn-asp-count').textContent = crossAsp.length + ' aspects';
  crossAsp.forEach(function(asp) {
    var closePct = Math.round((asp.Closeness || 0) * 100);
    var orb = Math.abs((asp.Angle || 0) - (asp.Degrees || 0)).toFixed(1);
    var tr = document.createElement('tr');
    tr.innerHTML =
      '<td><b>' + asp.Body1 + '</b></td>' +
      '<td style="text-align:center;color:' + (asp.Color || '#888') + '">' +
        (asp.aspect_symbol || '') + ' <span style="font-size:10px">' + asp.Aspect + '</span></td>' +
      '<td><b>' + asp.Body2 + '</b></td>' +
      '<td class="num">' + orb + '°</td>' +
      '<td class="num"><div style="display:flex;align-items:center;gap:4px;justify-content:flex-end">' +
        '<div style="width:36px;height:5px;background:#f5efe6;border-radius:2px;overflow:hidden">' +
          '<div style="width:' + closePct + '%;height:100%;background:' + (asp.Color || '#8b7355') + '"></div>' +
        '</div>' + closePct + '%</div></td>';
    tbody.appendChild(tr);
  });

  // Wheels
  drawBiWheel(data.chart_a, data.chart_b, data.cross_aspects, nameA, nameB);
  drawCompositeWheel(data.composite_bodies, data.composite_aspects);
}

function synFetchHarmonics(baseOrb) {
  if (!LAST_SYN_HARM_PARAMS) return;
  var p = LAST_SYN_HARM_PARAMS;
  var payload = {
    person_a: p.person_a,
    person_b: p.person_b,
    active_bodies: ['Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn','Uranus','Neptune','Pluto'],
    max_harmonic: 32,
    base_orb: baseOrb,
    orb_formula: 'sqrt',
    min_tightness_pct: 0,
  };
  LAST_SYN_HARM_PARAMS.base_orb = baseOrb;

  document.getElementById('syn-harm-loading').style.display = 'inline';
  document.getElementById('syn-harm-empty').style.display = 'flex';
  document.getElementById('syn-harm-content').style.display = 'none';

  fetch('/synastry/harmonics', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) })
    .then(function(r){ return r.json(); })
    .then(function(data){ synRenderHarmonics(data); })
    .catch(function(){})
    .finally(function(){ document.getElementById('syn-harm-loading').style.display = 'none'; });
}

var LAST_SYN_HARMONICS = null;
var SELECTED_SYN_HARMONIC = null;

function synRenderHarmonics(data) {
  LAST_SYN_HARMONICS = (data.ranked || []).filter(function(r){ return r.PairCount > 0; });
  SELECTED_SYN_HARMONIC = null;
  document.getElementById('syn-harm-empty').style.display = 'none';
  document.getElementById('syn-harm-content').style.display = 'block';
  synRenderHarmonicsList();
}

function synRenderHarmonicsList() {
  if (!LAST_SYN_HARMONICS) return;
  var listEl = document.getElementById('syn-harm-list');
  var hdrEl  = document.getElementById('syn-harm-list-hdr');
  var detailEl = document.getElementById('syn-harm-detail');
  var rankBy = (document.getElementById('syn-harm-rank-by') || {}).value || 'pairs';

  var LABELS = {
    pairs:    'Ranked by pair count',
    sumclose: 'Ranked by total resonance',
    adjusted: 'Ranked by noise-adjusted score',
  };
  if (hdrEl) hdrEl.textContent = (LABELS[rankBy] || LABELS.pairs) + ' · click for meaning';
  if (detailEl) detailEl.innerHTML = '<div class="harm-hint">Select a harmonic to see its meaning.</div>';

  if (!LAST_SYN_HARMONICS.length) {
    listEl.innerHTML = '<div class="harm-empty" style="font-size:11px">No cross-chart resonances found.</div>';
    return;
  }

  var sorted = sortHarmonics(LAST_SYN_HARMONICS, rankBy);
  var metricKey = { pairs: 'PairCount', sumclose: 'SumClose', adjusted: 'SumCloseAdj' }[rankBy];
  var maxVal = sorted.length ? (sorted[0][metricKey] || 1) : 1;

  listEl.innerHTML = sorted.map(function(r, i) {
    var val = r[metricKey] || 0;
    var barW = Math.max(4, Math.round((val / maxVal) * 100));
    var label = 'H' + r.Harmonic + (r.Name && r.Name !== '—' ? ' · ' + r.Name : '');
    var metaStr = rankBy === 'pairs'
      ? r.PairCount + ' pairs · ' + (r.Tightest || 0).toFixed(3) + '°'
      : (rankBy === 'sumclose' ? 'Σ' : 'adj') + ' ' + val.toFixed(2) + ' · ' + r.PairCount + ' pairs';
    return (
      '<div class="harm-row' + (SELECTED_SYN_HARMONIC === r.Harmonic ? ' sel' : '') +
           '" data-harm="' + r.Harmonic + '" style="cursor:pointer">' +
        '<div class="harm-row-num">' + (i+1) + '</div>' +
        '<div class="harm-row-name">' + label + '</div>' +
        '<div class="harm-row-bar-bg"><div class="harm-row-bar" style="width:' + barW + '%"></div></div>' +
        '<div class="harm-row-meta">' + metaStr + '</div>' +
      '</div>'
    );
  }).join('');

  listEl.querySelectorAll('.harm-row').forEach(function(row) {
    row.addEventListener('click', function() {
      synRenderHarmDetail(parseInt(row.dataset.harm, 10));
    });
  });
}

function synRenderHarmDetail(harmonic) {
  if (!LAST_SYN_HARMONICS) return;
  SELECTED_SYN_HARMONIC = harmonic;

  document.querySelectorAll('#syn-harm-list .harm-row').forEach(function(r) {
    r.classList.toggle('sel', parseInt(r.dataset.harm, 10) === harmonic);
  });

  var row = LAST_SYN_HARMONICS.find(function(r) { return r.Harmonic === harmonic; });
  var detailEl = document.getElementById('syn-harm-detail');
  if (!row || !detailEl) return;

  var name = row.Name && row.Name !== '—' ? row.Name : 'H' + harmonic;
  var factors = row.Factors ? ' <span style="font-size:10px;color:#9b9185;font-weight:400">(' + row.Factors + ')</span>' : '';
  var html = '<div class="harm-title">H' + harmonic + ' · ' + name + factors + '</div>';

  var meaning = row.NatalMeaning && row.NatalMeaning !== 'nan' ? row.NatalMeaning : '';
  if (meaning) html += '<div class="harm-meaning">' + meaning + '</div>';

  if (row.Pairs) {
    var pairs = row.Pairs.split(',  ').map(function(p){ return p.trim(); }).filter(Boolean);
    html += '<div class="harm-asp-label">' + row.PairCount + ' resonating pair' + (row.PairCount===1?'':'s') + '</div>';
    html += pairs.map(function(p) {
      var m = p.match(/^(.*?)\s+([\d.]+)°?$/);
      var pairName = m ? m[1] : p;
      var orb = m ? m[2] + '°' : '';
      return '<div class="harm-asp-item"><div class="harm-asp-head">' + pairName +
        (orb ? ' <span class="asp-close">&middot; ' + orb + ' off exact</span>' : '') +
        '</div></div>';
    }).join('');
  }

  if (row.Source && row.Source !== 'nan') {
    html += '<div style="font-size:9px;color:#b09e82;margin-top:8px;font-style:italic">' + row.Source + '</div>';
  }

  detailEl.innerHTML = html;
}

function copySynAspects() {
  var rows = Array.from(document.querySelectorAll('#syn-cross-asp-tbody tr'));
  var txt = rows.map(function(tr) {
    return Array.from(tr.querySelectorAll('td')).map(function(td){ return td.textContent.trim(); }).join('\t');
  }).join('\n');
  navigator.clipboard.writeText(txt).then(function() {
    var b = document.getElementById('syn-copy-asp-btn');
    if (b) { b.textContent = 'Copied!'; setTimeout(function(){ b.textContent = 'Copy'; }, 1500); }
  });
}

function copyCompAspects() {
  if (!LAST_SYN_DATA || !LAST_SYN_DATA.composite_aspects) return;
  var txt = LAST_SYN_DATA.composite_aspects.map(function(a) {
    var orb = (a.Angle != null && a.Degrees != null) ? Math.abs(a.Angle - a.Degrees).toFixed(2) + '°' : '';
    return [a.Body1, (a.aspect_symbol || a.Aspect), a.Body2, a.Aspect, orb ? 'orb ' + orb : ''].filter(Boolean).join('\t');
  }).join('\n');
  navigator.clipboard.writeText(txt).then(function() {
    var b = document.getElementById('comp-copy-asp-btn');
    if (b) { b.textContent = 'Copied!'; setTimeout(function(){ b.textContent = 'Copy'; }, 1500); }
  });
}

// ─── Bi-wheel ─────────────────────────────────────────────────────────────────

function drawBiWheel(dataA, dataB, crossAspects, nameA, nameB) {
  var cvs = document.getElementById('syn-biwheel-canvas');
  if (!cvs) return;
  var parent = cvs.parentElement;
  var dpr = window.devicePixelRatio || 1;
  var S = Math.min(parent.clientWidth || 500, 700);
  var W = S, H = S;
  cvs.width = W * dpr; cvs.height = H * dpr;
  cvs.style.width = W + 'px'; cvs.style.height = H + 'px';

  var ctx = cvs.getContext('2d');
  ctx.setTransform(1,0,0,1,0,0);
  ctx.scale(dpr, dpr);

  var cx = W / 2, cy = H / 2;
  var R = Math.min(cx, cy) - 10;

  var rZodOut  = R;
  var rZodIn   = R * 0.82;
  var rAOuter  = rZodIn * 0.99;   // Person A planet ring
  var rAInner  = rZodIn * 0.88;
  var rBOuter  = rZodIn * 0.85;   // Person B planet ring
  var rBInner  = rZodIn * 0.73;
  var rAspOut  = rBInner * 0.97;  // aspect circle

  // Rotation: Person A's Descendant at 3 o'clock
  var descA = 0;
  var bodiesA = dataA.bodies || [];
  for (var i = 0; i < bodiesA.length; i++) {
    if (bodiesA[i].Body === 'Desc') { descA = bodiesA[i]['Longitude (°)'] || 0; break; }
  }
  function lon2a(lon) { return -((lon - descA) * Math.PI / 180); }

  // White background (natal style)
  ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, W, H);

  // Zodiac band — white cells, hairline separators, element-colored sign names (natal style)
  for (var s = 0; s < 12; s++) {
    var aStart = lon2a(s * 30), aEnd = lon2a(s * 30 + 30);
    ctx.beginPath();
    ctx.moveTo(cx + rZodIn * Math.cos(aStart), cy + rZodIn * Math.sin(aStart));
    ctx.arc(cx, cy, rZodOut, aStart, aEnd, true);
    ctx.arc(cx, cy, rZodIn, aEnd, aStart, false);
    ctx.closePath();
    ctx.fillStyle = '#fff'; ctx.fill();
    ctx.strokeStyle = '#888'; ctx.lineWidth = 0.6; ctx.stroke();
    var midA = lon2a(s * 30 + 15);
    var tr = (rZodIn + rZodOut) / 2;
    ctx.save();
    ctx.translate(cx + tr * Math.cos(midA), cy + tr * Math.sin(midA));
    ctx.rotate(midA + Math.PI / 2);
    ctx.fillStyle = SIGN_GLYPH_COLS[s];
    ctx.font = '600 ' + Math.round(R * 0.055) + 'px sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(SIGN_ABBR_W[s], 0, 0);
    ctx.restore();
  }

  // Degree tick marks (natal style — every degree, heavier at 5° and 10°)
  for (var dt = 0; dt < 360; dt++) {
    var ta = lon2a(dt);
    var inner = (dt % 10 === 0) ? rZodOut - R*0.025
              : (dt % 5  === 0) ? rZodOut - R*0.014
                                 : rZodOut - R*0.007;
    ctx.beginPath();
    ctx.moveTo(cx + inner * Math.cos(ta), cy + inner * Math.sin(ta));
    ctx.lineTo(cx + rZodOut * Math.cos(ta), cy + rZodOut * Math.sin(ta));
    ctx.strokeStyle = (dt % 10 === 0) ? '#444' : (dt % 5 === 0 ? '#888' : '#ccc');
    ctx.lineWidth   = (dt % 10 === 0) ? 0.7   : 0.4;
    ctx.stroke();
  }

  // Ring borders
  ctx.beginPath(); ctx.arc(cx, cy, rZodOut, 0, 2*Math.PI); ctx.strokeStyle = '#666'; ctx.lineWidth = 1; ctx.stroke();
  ctx.beginPath(); ctx.arc(cx, cy, rZodIn,  0, 2*Math.PI); ctx.strokeStyle = '#999'; ctx.lineWidth = 0.7; ctx.stroke();
  ctx.beginPath(); ctx.arc(cx, cy, rBOuter, 0, 2*Math.PI); ctx.strokeStyle = '#bbb'; ctx.lineWidth = 0.5; ctx.stroke();
  ctx.beginPath(); ctx.arc(cx, cy, rBInner, 0, 2*Math.PI); ctx.strokeStyle = '#bbb'; ctx.lineWidth = 0.5; ctx.stroke();
  ctx.beginPath(); ctx.arc(cx, cy, rAspOut, 0, 2*Math.PI); ctx.strokeStyle = '#ccc'; ctx.lineWidth = 0.4; ctx.stroke();

  // House cusps (Person A, dashed)
  var houseCusps = bodiesA.filter(function(b){ return b.Body && b.Body.indexOf('House Cusp') === 0; });
  houseCusps.forEach(function(h) {
    var a = lon2a(h['Longitude (°)']);
    ctx.beginPath();
    ctx.moveTo(cx + rZodIn * Math.cos(a), cy + rZodIn * Math.sin(a));
    ctx.lineTo(cx + rBInner * 0.85 * Math.cos(a), cy + rBInner * 0.85 * Math.sin(a));
    ctx.strokeStyle = '#bbb'; ctx.lineWidth = 0.5; ctx.setLineDash([2,3]); ctx.stroke();
    ctx.setLineDash([]);
  });

  // Build planet position maps — both anchored at rAspOut (innermost circle) for traditional aspect lines
  var planetPosA = {}, planetPosB = {};

  var bodiesAFiltered = bodiesA.filter(function(b){ return b.Body && b.Body.indexOf('House Cusp') < 0; });
  bodiesAFiltered.forEach(function(b) {
    var a = lon2a(b['Longitude (°)']);
    planetPosA[b.Body] = { x: cx + rAspOut * Math.cos(a), y: cy + rAspOut * Math.sin(a), a: a };
  });

  var bodiesB = dataB.bodies || [];
  var bodiesBFiltered = bodiesB.filter(function(b){ return b.Body && b.Body.indexOf('House Cusp') < 0; });
  bodiesBFiltered.forEach(function(b) {
    var a = lon2a(b['Longitude (°)']);
    planetPosB[b.Body] = { x: cx + rAspOut * Math.cos(a), y: cy + rAspOut * Math.sin(a), a: a };
  });

  // Helper: is a body visible given filter state?
  function bodyVisA(name) {
    if (name === 'Desc') return SYN_BODY_A['Asc'] !== false;
    if (name === 'IC')   return SYN_BODY_A['MC']  !== false;
    if (name === 'South Node') return SYN_BODY_A['North Node'] !== false;
    return SYN_BODY_A[name] !== false;
  }
  function bodyVisB(name) {
    if (name === 'Desc') return SYN_BODY_B['Asc'] !== false;
    if (name === 'IC')   return SYN_BODY_B['MC']  !== false;
    if (name === 'South Node') return SYN_BODY_B['North Node'] !== false;
    return SYN_BODY_B[name] !== false;
  }

  // Cross-aspect lines — filtered by aspect type, orb, and body visibility
  (crossAspects || []).forEach(function(asp) {
    if (!SYN_ASP_FILTER[asp.Aspect]) return;
    if (!bodyVisA(asp.Body1) || !bodyVisB(asp.Body2)) return;
    var posA = planetPosA[asp.Body1], posB = planetPosB[asp.Body2];
    if (!posA || !posB) return;
    // Orb filter: major aspects use SYN_MAJOR_ORB, minor use SYN_MINOR_ORB
    var aspMeta = ASP_TYPES.find(function(x){ return x.name === asp.Aspect; });
    var orbLimit = (aspMeta && aspMeta.major) ? SYN_MAJOR_ORB : SYN_MINOR_ORB;
    var orb = Math.abs((asp.Angle || 0) - (asp.Degrees || 0));
    if (orb > orbLimit) return;

    ctx.save();
    ctx.globalAlpha = 0.12 + (asp.Closeness || 0) * 0.55;
    ctx.beginPath();
    ctx.moveTo(posA.x, posA.y);
    ctx.lineTo(posB.x, posB.y);
    ctx.strokeStyle = asp.Color || '#aaa';
    ctx.lineWidth = 0.5 + (asp.Closeness || 0) * 1.5;
    ctx.stroke();
    ctx.restore();
  });

  // Person A planets (outer ring, earth tones)
  var ANGLE_SET = {Asc:1, Desc:1, MC:1, IC:1};
  bodiesAFiltered.forEach(function(b) {
    if (ANGLE_SET[b.Body]) return;
    if (!bodyVisA(b.Body)) return;
    var a = lon2a(b['Longitude (°)']);
    var r = (rAInner + rAOuter) / 2;
    ctx.save();
    ctx.translate(cx + r * Math.cos(a), cy + r * Math.sin(a));
    ctx.rotate(a + Math.PI / 2);
    ctx.fillStyle = '#8b4513';
    ctx.font = 'bold 14px serif'; ctx.textAlign = 'center';
    ctx.fillText(b.Symbol || b.Body[0], 0, 5);
    ctx.restore();
  });

  // Angle spokes for Person A (respects Asc/MC toggles)
  ['Asc','Desc','MC','IC'].forEach(function(ang) {
    if (!bodyVisA(ang)) return;
    var b = bodiesAFiltered.find(function(x){ return x.Body === ang; });
    if (!b) return;
    var a = lon2a(b['Longitude (°)']);
    ctx.beginPath();
    ctx.moveTo(cx + rZodIn * Math.cos(a), cy + rZodIn * Math.sin(a));
    ctx.lineTo(cx + rAspOut * 0.9 * Math.cos(a), cy + rAspOut * 0.9 * Math.sin(a));
    ctx.strokeStyle = '#8b4513'; ctx.lineWidth = 0.8; ctx.stroke();
    ctx.save();
    ctx.translate(cx + rAOuter * 0.97 * Math.cos(a), cy + rAOuter * 0.97 * Math.sin(a));
    ctx.rotate(a + Math.PI/2);
    ctx.fillStyle = '#8b4513'; ctx.font = 'bold 7px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText(ang, 0, 3);
    ctx.restore();
  });

  // Person B planets (inner ring, blue)
  bodiesBFiltered.forEach(function(b) {
    if (ANGLE_SET[b.Body]) return;
    if (!bodyVisB(b.Body)) return;
    var a = lon2a(b['Longitude (°)']);
    var r = (rBInner + rBOuter) / 2;
    ctx.save();
    ctx.translate(cx + r * Math.cos(a), cy + r * Math.sin(a));
    ctx.rotate(a + Math.PI / 2);
    ctx.fillStyle = '#2471a3';
    ctx.font = 'bold 13px serif'; ctx.textAlign = 'center';
    ctx.fillText(b.Symbol || b.Body[0], 0, 5);
    ctx.restore();
  });

  // Name labels
  ctx.font = 'bold 10px sans-serif'; ctx.textAlign = 'left';
  ctx.fillStyle = '#8b4513'; ctx.fillText(nameA, 8, 16);
  ctx.fillStyle = '#2471a3'; ctx.fillText(nameB, 8, 30);
}

// ─── Composite wheel ──────────────────────────────────────────────────────────

function drawCompositeWheel(compositeBodies, compositeAspects) {
  var cvs = document.getElementById('syn-composite-canvas');
  if (!cvs) return;
  var parent = cvs.parentElement;
  var dpr = window.devicePixelRatio || 1;
  var S = Math.min(parent.clientWidth || 480, 680);
  var W = S, H = S;
  cvs.width = W * dpr; cvs.height = H * dpr;
  cvs.style.width = W + 'px'; cvs.style.height = H + 'px';

  var ctx = cvs.getContext('2d');
  ctx.setTransform(1,0,0,1,0,0);
  ctx.scale(dpr, dpr);

  var cx = W / 2, cy = H / 2;
  var R = Math.min(cx, cy) - 10;

  var rZodOut = R, rZodIn = R * 0.82;
  var rPlanet = rZodIn * 0.91;
  var rAsp    = rZodIn * 0.75;

  var descLon = 0;
  (compositeBodies || []).forEach(function(b) {
    if (b.Body === 'Desc') descLon = b['Longitude (°)'] || 0;
  });
  function lon2a(lon) { return -((lon - descLon) * Math.PI / 180); }

  // White background + natal-style zodiac band
  ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, W, H);

  for (var s = 0; s < 12; s++) {
    var aStart = lon2a(s * 30), aEnd = lon2a(s * 30 + 30);
    ctx.beginPath();
    ctx.moveTo(cx + rZodIn * Math.cos(aStart), cy + rZodIn * Math.sin(aStart));
    ctx.arc(cx, cy, rZodOut, aStart, aEnd, true);
    ctx.arc(cx, cy, rZodIn, aEnd, aStart, false);
    ctx.closePath();
    ctx.fillStyle = '#fff'; ctx.fill();
    ctx.strokeStyle = '#888'; ctx.lineWidth = 0.6; ctx.stroke();
    var midA = lon2a(s * 30 + 15);
    var tr = (rZodIn + rZodOut) / 2;
    ctx.save();
    ctx.translate(cx + tr * Math.cos(midA), cy + tr * Math.sin(midA));
    ctx.rotate(midA + Math.PI/2);
    ctx.fillStyle = SIGN_GLYPH_COLS[s];
    ctx.font = '600 ' + Math.round(R * 0.055) + 'px sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(SIGN_ABBR_W[s], 0, 0);
    ctx.restore();
  }

  // Degree tick marks
  for (var dt = 0; dt < 360; dt++) {
    var ta = lon2a(dt);
    var inner = (dt % 10 === 0) ? rZodOut - R*0.025 : (dt % 5 === 0) ? rZodOut - R*0.014 : rZodOut - R*0.007;
    ctx.beginPath();
    ctx.moveTo(cx + inner * Math.cos(ta), cy + inner * Math.sin(ta));
    ctx.lineTo(cx + rZodOut * Math.cos(ta), cy + rZodOut * Math.sin(ta));
    ctx.strokeStyle = (dt % 10 === 0) ? '#444' : (dt % 5 === 0 ? '#888' : '#ccc');
    ctx.lineWidth = (dt % 10 === 0) ? 0.7 : 0.4;
    ctx.stroke();
  }

  ctx.beginPath(); ctx.arc(cx, cy, rZodOut, 0, 2*Math.PI); ctx.strokeStyle = '#666'; ctx.lineWidth = 1; ctx.stroke();
  ctx.beginPath(); ctx.arc(cx, cy, rZodIn,  0, 2*Math.PI); ctx.strokeStyle = '#999'; ctx.lineWidth = 0.7; ctx.stroke();
  ctx.beginPath(); ctx.arc(cx, cy, rAsp,    0, 2*Math.PI); ctx.strokeStyle = '#ccc'; ctx.lineWidth = 0.4; ctx.stroke();

  function compBodyVis(name) {
    if (name === 'Desc') return COMP_BODY['Asc'] !== false;
    if (name === 'IC')   return COMP_BODY['MC']  !== false;
    if (name === 'South Node') return COMP_BODY['North Node'] !== false;
    return COMP_BODY[name] !== false;
  }

  // Aspect lines
  var posMap = {};
  (compositeBodies || []).forEach(function(b) {
    if (!b.Body || b.Body.indexOf('House Cusp') >= 0) return;
    if (!compBodyVis(b.Body)) return;
    posMap[b.Body] = lon2a(b['Longitude (°)']);
  });
  (compositeAspects || []).forEach(function(asp) {
    if (!COMP_ASP_FILTER[asp.Aspect]) return;
    var aA = posMap[asp.Body1], aB = posMap[asp.Body2];
    if (aA == null || aB == null) return;
    var aspMeta = ASP_TYPES.find(function(x){ return x.name === asp.Aspect; });
    var orbLimit = (aspMeta && aspMeta.major) ? COMP_MAJOR_ORB : COMP_MINOR_ORB;
    var orb = Math.abs((asp.Angle || 0) - (asp.Degrees || 0));
    if (orb > orbLimit) return;
    ctx.save();
    ctx.globalAlpha = 0.2 + (asp.Closeness || 0) * 0.5;
    ctx.beginPath();
    ctx.moveTo(cx + rAsp * Math.cos(aA), cy + rAsp * Math.sin(aA));
    ctx.lineTo(cx + rAsp * Math.cos(aB), cy + rAsp * Math.sin(aB));
    ctx.strokeStyle = asp.Color || '#aaa';
    ctx.lineWidth = 0.5 + (asp.Closeness || 0) * 1.0;
    ctx.stroke();
    ctx.restore();
  });

  // Planets + angles
  var ANGLE_SET = {Asc:1, Desc:1, MC:1, IC:1};
  (compositeBodies || []).forEach(function(b) {
    if (!b.Body || b.Body.indexOf('House Cusp') >= 0) return;
    if (!compBodyVis(b.Body)) return;
    var a = lon2a(b['Longitude (°)']);
    if (ANGLE_SET[b.Body]) {
      ctx.beginPath();
      ctx.moveTo(cx + rZodIn * Math.cos(a), cy + rZodIn * Math.sin(a));
      ctx.lineTo(cx + rAsp * 0.96 * Math.cos(a), cy + rAsp * 0.96 * Math.sin(a));
      ctx.strokeStyle = '#8b7355'; ctx.lineWidth = 0.8; ctx.stroke();
      ctx.save();
      ctx.translate(cx + (rZodIn - 8) * Math.cos(a), cy + (rZodIn - 8) * Math.sin(a));
      ctx.rotate(a + Math.PI/2);
      ctx.fillStyle = '#5a4e3c'; ctx.font = 'bold 7px sans-serif'; ctx.textAlign = 'center';
      ctx.fillText(b.Body, 0, 3);
      ctx.restore();
      return;
    }
    ctx.save();
    ctx.translate(cx + rPlanet * Math.cos(a), cy + rPlanet * Math.sin(a));
    ctx.rotate(a + Math.PI/2);
    ctx.fillStyle = '#111';
    ctx.font = 'bold 12px serif'; ctx.textAlign = 'center';
    ctx.fillText(b.Symbol || b.Body[0], 0, 4);
    ctx.restore();
  });

  // Title
  ctx.font = 'bold 10px sans-serif'; ctx.fillStyle = '#8b7355'; ctx.textAlign = 'center';
  ctx.fillText('Composite', cx, 14);
}

// ─── Synastry tab ────────────────────────────────────────────────────────────

var SYN_DATA = null;
var SYN_HARM_DATA = null;

// Slider readout
(function () {
  var sl = document.getElementById('syn-orb-val');
  var rd = document.getElementById('syn-orb-readout');
  if (sl && rd) {
    sl.addEventListener('input', function () { rd.textContent = parseFloat(sl.value).toFixed(1) + '°'; });
  }
})();

