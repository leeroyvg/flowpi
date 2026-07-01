function normalizeBase(base) {
    return base.replace(/\/$/, "");
}

function getApiCandidates() {
    const params = new URLSearchParams(window.location.search);
    const candidates = [];
    const configuredBase = params.get("api") || window.FLOWPI_API_BASE || localStorage.getItem("flowpi.apiBase");
    const { protocol, hostname, origin, pathname } = window.location;

    if (configuredBase) {
        candidates.push(normalizeBase(configuredBase));
    }

    if (protocol === "http:" || protocol === "https:") {
        candidates.push(origin);
        candidates.push(`${origin}/app`);

        const pathParts = pathname.split("/").filter(Boolean);
        if (pathParts.length > 0) {
            const parentPath = pathParts.slice(0, -1).join("/");
            if (parentPath) {
                candidates.push(`${origin}/${parentPath}`);
            }
        }

        if (hostname) {
            candidates.push(`${protocol}//${hostname}:5000`);
            candidates.push(`${protocol}//${hostname}:5000/app`);
        }
    }

    candidates.push("http://127.0.0.1:5000", "http://localhost:5000");

    return [...new Set(candidates.map(normalizeBase))];
}

let apiBasePromise = null;

async function resolveApiBase() {
    if (apiBasePromise) {
        return apiBasePromise;
    }

    apiBasePromise = (async () => {
        const candidates = getApiCandidates();

        for (const base of candidates) {
            try {
                const response = await fetch(`${base}/health`, {
                    headers: { "Accept": "application/json" }
                });

                if (response.ok) {
                    localStorage.setItem("flowpi.apiBase", base);
                    setText("apiStatus", `Connected to ${base}`);
                    return base;
                }
            } catch (error) {
                console.debug("health probe failed", base, error);
            }
        }

        localStorage.removeItem("flowpi.apiBase");

        throw new Error(`No backend reachable. Tried: ${candidates.join(", ")}`);
    })();

    return apiBasePromise;
}

let activeUserId = null;

function toLiters(ml) {
    return Number(ml || 0) / 1000;
}

function formatLiters(ml) {
    return `${toLiters(ml).toFixed(2)} L`;
}

function setText(id, value) {
    document.getElementById(id).innerText = value;
}

function showApiError(context, error) {
    console.error(context, error);
    setText("apiStatus", "Backend unavailable");
}

async function fetchJson(path, options = {}) {
    const apiBase = await resolveApiBase();
    const res = await fetch(`${apiBase}${path}`, {
        headers: {
            "Accept": "application/json",
            ...(options.headers || {})
        },
        ...options
    });

    if (!res.ok) {
        throw new Error(`${path} failed with status ${res.status}`);
    }

    return res.json();
}

async function loadStatus() {
    try {
        const data = await fetchJson("/status");

        setText(
            "tapStatus",
            data.tap_open ? "🟢 TAP OPEN" : "🔴 TAP CLOSED"
        );

        activeUserId = data.user;
        const flowLMin = Number(data.flow_l_min || 0);
        const flowLS = Number(data.flow_ml_s || 0) / 1000;

        setText("activeUser", "User " + activeUserId);
        setText("flowSpeed", `${flowLMin.toFixed(2)} L/min`);
        setText("flowSpeedLs", `${flowLS.toFixed(2)} L/s`);
        setText("apiStatus", "Connected");
    } catch (err) {
        showApiError("status", err);
    }
}

async function loadTotal() {
    try {
        const data = await fetchJson("/user_total");

        setText("user_total", formatLiters(data.total_ml));
    } catch (err) {
        showApiError("user_total", err);
    }
}

async function loadTotals() {
    const container = document.getElementById("user_totals");
    try {
        const data = await fetchJson("/user_totals");
        const sortedUsers = [...data].sort((a, b) => Number(b.ml || 0) - Number(a.ml || 0));

        const previousPositions = new Map();
        Array.from(container.children).forEach(card => {
            previousPositions.set(card.dataset.userId, card.getBoundingClientRect());
        });

        sortedUsers.forEach(u => {
            const key = String(u.id);
            let card = container.querySelector(`.user-card[data-user-id="${key}"]`);

            if (!card) {
                card = document.createElement("button");
                card.className = "user-card new-card";
                card.type = "button";
                card.dataset.userId = key;
                card.onclick = async () => {
                    try {
                        await fetchJson(`/set_user/${u.id}`, { method: "POST" });
                        await loadStatus();
                        await loadTotals();
                    } catch (err) {
                        showApiError("set_user", err);
                    }
                };
            }

            card.classList.toggle("active", u.id === activeUserId);
            card.innerHTML = `
                <div class="user-row">
                    <div class="user-name">${u.name}</div>
                    <div class="user-volume">${formatLiters(u.ml)}</div>
                </div>
            `;

            container.appendChild(card);
        });

        const validIds = new Set(sortedUsers.map(u => String(u.id)));
        Array.from(container.children).forEach(card => {
            if (!validIds.has(card.dataset.userId)) {
                card.remove();
            }
        });

        Array.from(container.children).forEach(card => {
            const oldRect = previousPositions.get(card.dataset.userId);
            if (!oldRect) {
                setTimeout(() => card.classList.remove("new-card"), 250);
                return;
            }

            const newRect = card.getBoundingClientRect();
            const dx = oldRect.left - newRect.left;
            const dy = oldRect.top - newRect.top;

            if (dx || dy) {
                card.style.transform = `translate(${dx}px, ${dy}px)`;
                requestAnimationFrame(() => {
                    card.style.transform = "";
                });
            }
        });
    } catch (err) {
        container.innerHTML = "";
        showApiError("user_totals", err);
    }
}

function refresh() {
    void loadStatus();
    void loadTotal();
    void loadTotals();
}

setInterval(refresh, 2000);

refresh();
