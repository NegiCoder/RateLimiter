const $ = (selector) => document.querySelector(selector);

const state = {
  capacity: 10,
  refillRate: 1,
  busy: false,
};

function setBusy(value) {
  state.busy = value;
  $("#single-request").disabled = value;
  $("#burst-request").disabled = value;
  $("#reset-bucket").disabled = value;
}

function addLog(status, message) {
  const template = $("#log-row-template").content.cloneNode(true);
  const row = template.querySelector(".log-row");
  row.classList.add(status >= 400 ? "log-row--blocked" : "log-row--ok");
  row.querySelector(".log-row__status").textContent = status;
  row.querySelector(".log-row__message").textContent = message;
  row.querySelector(".log-row__time").textContent = new Date().toLocaleTimeString();
  $("#request-log").prepend(row);
}

function renderBucket(data) {
  const bucket = data.bucket || {};
  const hasBucket = Object.keys(bucket).length > 0;
  const capacity = Number(bucket.capacity ?? state.capacity);
  const tokens = hasBucket ? Number(bucket.tokens) : capacity;
  const ttl = Number(data.ttl ?? -2);
  const percent = Math.max(0, Math.min(100, (tokens / capacity) * 100));

  $("#client-id").textContent = `Client: ${data.client_id || "-"}`;
  $("#tokens-left").textContent = Number.isFinite(tokens) ? tokens.toFixed(2) : "-";
  $("#token-meter").style.width = `${percent}%`;
  $("#token-meter").style.background = percent < 20
    ? "linear-gradient(90deg, #dc2626, #f97316)"
    : "linear-gradient(90deg, #059669, #22c55e)";
  $("#bucket-meta").textContent = !hasBucket
    ? "No bucket yet — first request will create one at full capacity."
    : ttl > 0
      ? `Bucket expires after ${ttl}s of inactivity.`
      : "Bucket is active.";
}

async function refreshHealth() {
  const res = await fetch("/health");
  const data = await res.json();
  state.capacity = Number(data.capacity || 10);
  state.refillRate = Number(data.refill_rate || 1);

  $("#redis-status").textContent = data.redis ? "Connected" : "Unavailable";
  $("#redis-status").style.color = data.redis ? "var(--success)" : "var(--danger)";
  $("#capacity").textContent = state.capacity;
  $("#refill-rate").textContent = state.refillRate;
}

async function refreshBucket() {
  try {
    const res = await fetch("/debug/me");
    if (!res.ok) throw new Error("bucket fetch failed");
    renderBucket(await res.json());
  } catch {
    $("#bucket-meta").textContent = "Could not load bucket state.";
  }
}

async function sendTestRequest({ manageBusy = true } = {}) {
  if (manageBusy) setBusy(true);
  try {
    const res = await fetch("/test");
    const limit = res.headers.get("X-RateLimit-Limit") || state.capacity;
    const remaining = res.headers.get("X-RateLimit-Remaining") ?? "-";
    const body = await res.json().catch(() => ({}));
    const message = res.ok
      ? `Allowed by middleware. Remaining: ${remaining}/${limit}`
      : `${body.detail || "Rate limit exceeded"}. Remaining: ${remaining}/${limit}`;

    addLog(res.status, message);
    await refreshBucket();
  } finally {
    if (manageBusy) setBusy(false);
  }
}

async function runBurst() {
  setBusy(true);
  try {
    for (let i = 0; i < 12; i += 1) {
      await sendTestRequest({ manageBusy: false });
      await new Promise((resolve) => setTimeout(resolve, 140));
    }
  } finally {
    setBusy(false);
  }
}

async function resetBucket() {
  setBusy(true);
  try {
    const res = await fetch("/debug/reset", { method: "POST" });
    const data = await res.json();
    addLog(200, data.deleted ? "Bucket reset for this client." : "No bucket existed for this client.");
    await refreshBucket();
  } finally {
    setBusy(false);
  }
}

async function init() {
  $("#single-request").addEventListener("click", sendTestRequest);
  $("#burst-request").addEventListener("click", runBurst);
  $("#reset-bucket").addEventListener("click", resetBucket);
  $("#clear-log").addEventListener("click", () => {
    $("#request-log").innerHTML = "";
  });

  try {
    await refreshHealth();
    await refreshBucket();
  } catch (err) {
    $("#redis-status").textContent = "Unavailable";
    $("#redis-status").style.color = "var(--danger)";
    addLog(503, "Could not reach API or Redis. Check REDIS_URL and server logs.");
  }

  setInterval(refreshBucket, 3000);
}

init();
