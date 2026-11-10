/* ROOTS shared client: live connection (SSE) with automatic reconnect + polling fallback. */
(function () {
  function connect({ channel, token, onState, onStatus }) {
    let es = null, last = -1, pollT = null, retryT = null;
    const q = `channel=${channel}` + (token ? `&token=${encodeURIComponent(token)}` : "");
    const apply = (s) => { if (s.version >= last) { last = s.version; onState(s); } };
    const status = (x) => onStatus && onStatus(x);
    function poll() {
      fetch(`/api/state?${q}`, { cache: "no-store" }).then(r => r.ok ? r.json() : Promise.reject()).then(s => { apply(s); }).catch(() => {});
    }
    function open() {
      clearTimeout(retryT);
      try { es = new EventSource(`/api/events?${q}`); } catch (e) { status("offline"); retryT = setTimeout(open, 1500); return; }
      es.onopen = () => { last = -1; clearInterval(pollT); pollT = null; status("live"); };
      es.onmessage = (ev) => { try { apply(JSON.parse(ev.data)); } catch (e) { /* ignore bad frame */ } };
      es.onerror = () => {
        status("offline");
        if (!pollT) pollT = setInterval(poll, 2000);          // keep trying to fetch state while the stream is down
        if (es.readyState === 2) { es.close(); retryT = setTimeout(open, 1500); }   // browser gave up: reopen ourselves
      };
    }
    open();
    return { close() { es && es.close(); clearInterval(pollT); clearTimeout(retryT); } };
  }
  window.RC = { connect, esc: (s) => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])) };
})();
