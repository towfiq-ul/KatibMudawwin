const ENGINE_BASE_URL = process.env.ENGINE_BASE_URL || 'http://127.0.0.1:8765';

async function request(pathname, options) {
  const res = await fetch(`${ENGINE_BASE_URL}${pathname}`, options);
  if (!res.ok) {
    throw new Error(`engine request to ${pathname} failed: ${res.status}`);
  }
  return res.json();
}

function getStatus() {
  return request('/status');
}

function start() {
  return request('/start', { method: 'POST' });
}

function stop() {
  return request('/stop', { method: 'POST' });
}

module.exports = { getStatus, start, stop };
