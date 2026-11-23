(function () {
  const conn = document.getElementById('conn');
  const ts = document.getElementById('ts');
  const evm = document.getElementById('evm');
  const iqmeta = document.getElementById('iqmeta');
  const vnameta = document.getElementById('vnameta');
  const measuremeta = document.getElementById('measuremeta');
  const measure = document.getElementById('measure');

  function clearCanvas(id) {
    const c = document.getElementById(id);
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#0d0d0d';
    ctx.fillRect(0, 0, c.width, c.height);
    return { c, ctx };
  }

  function drawConstellation(points, meta) {
    const { c, ctx } = clearCanvas('constellation');
    ctx.strokeStyle = '#333';
    ctx.beginPath(); ctx.moveTo(c.width/2,0); ctx.lineTo(c.width/2,c.height); ctx.moveTo(0,c.height/2); ctx.lineTo(c.width,c.height/2); ctx.stroke();
    if (!points || !points.length) return;
    const maxAbs = Math.max(1e-6, ...points.map(p => Math.max(Math.abs(p[0]), Math.abs(p[1]))));
    const scale = (Math.min(c.width, c.height) * 0.4) / maxAbs;
    ctx.fillStyle = '#6cf';
    for (const p of points) {
      const x = c.width/2 + p[0]*scale;
      const y = c.height/2 - p[1]*scale;
      ctx.fillRect(x-2, y-2, 4, 4);
    }
    evm.textContent = `EVM: ${meta.evm_percent != null ? meta.evm_percent.toFixed(2)+'%' : '—'} n=${meta.n ?? '—'} SNR=${meta.snr_db_est != null ? meta.snr_db_est.toFixed(1)+' dB' : '—'}`;
  }

  function drawIQ(iq) {
    const { c, ctx } = clearCanvas('iq');
    if (!iq || !iq.length) return;
    const n = iq.length;
    const maxAbs = Math.max(1e-6, ...iq.map(p => Math.max(Math.abs(p[0]), Math.abs(p[1]))));
    ctx.strokeStyle = '#6cf'; ctx.beginPath();
    iq.forEach((p, idx) => { const x = idx/(n-1||1)*c.width; const y = c.height/2 - (p[0]/maxAbs)*(c.height*0.4); idx?ctx.lineTo(x,y):ctx.moveTo(x,y); });
    ctx.stroke();
    ctx.strokeStyle = '#fc6'; ctx.beginPath();
    iq.forEach((p, idx) => { const x = idx/(n-1||1)*c.width; const y = c.height/2 - (p[1]/maxAbs)*(c.height*0.4); idx?ctx.lineTo(x,y):ctx.moveTo(x,y); });
    ctx.stroke();
    iqmeta.textContent = `samples: ${n}`;
  }

  function drawVNA(records) {
    const { c, ctx } = clearCanvas('vna');
    if (!records || !records.length) return;
    const mags = records.map(r => 20*Math.log10(Math.sqrt((r.re||0)**2 + (r.im||0)**2) + 1e-18));
    const minF = records[0].freq_hz, maxF = records[records.length-1].freq_hz;
    const minM = Math.min(...mags), maxM = Math.max(...mags);
    ctx.strokeStyle = '#9f9'; ctx.beginPath();
    records.forEach((r, idx) => {
      const x = (r.freq_hz-minF)/(maxF-minF||1)*c.width;
      const y = c.height - (mags[idx]-minM)/(maxM-minM||1)*(c.height*0.8) - c.height*0.1;
      idx?ctx.lineTo(x,y):ctx.moveTo(x,y);
    });
    ctx.stroke();
    vnameta.textContent = `sweep: ${records.length} pts ${(minF/1e6).toFixed(3)}-${(maxF/1e6).toFixed(3)} MHz`;
  }

  function handleFrame(frame) {
    ts.textContent = frame.ts ? new Date(frame.ts*1000).toLocaleTimeString() : '';
    const p = frame.payload || {};
    if (frame.stream === 'constellation') drawConstellation(p.points || [], p.metrics || p);
    if (frame.stream === 'iq') drawIQ(p.iq || []);
    if (frame.stream === 'vna') drawVNA(p.records || []);
    if (frame.stream === 'omariglol.measure') {
      measuremeta.textContent = `parallelism: ${p.parallelism_ratio ? p.parallelism_ratio.toFixed(2)+'x' : '—'} overall=${p.overall_elapsed_ms ?? '—'}ms`;
      measure.textContent = JSON.stringify(p, null, 2);
    }
    if (frame.stream === 'status') {
      if (p.msg) conn.textContent = p.msg;
    }
  }

  function connect() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${location.host}/ws`);
    ws.onopen = () => { conn.textContent = 'connected'; };
    ws.onclose = () => { conn.textContent = 'disconnected (retrying)'; setTimeout(connect, 1500); };
    ws.onerror = () => { conn.textContent = 'error'; };
    ws.onmessage = (ev) => { try { handleFrame(JSON.parse(ev.data)); } catch (e) { console.error(e); } };
  }

  clearCanvas('constellation'); clearCanvas('iq'); clearCanvas('vna');
  connect();
})();