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
let sortMode = localStorage.getItem("flowpi.sortMode") || "ranking";
const userNamesById = new Map();

function getStoredTheme() {
    return localStorage.getItem("flowpi.theme") === "dark" ? "dark" : "light";
}

function applyTheme(theme) {
    const root = document.documentElement;
    root.setAttribute("data-theme", theme);

    const toggle = document.getElementById("themeToggle");
    if (toggle) {
        const darkEnabled = theme === "dark";
        toggle.innerText = darkEnabled ? "Theme: Dark" : "Theme: Light";
        toggle.setAttribute("aria-pressed", String(darkEnabled));
    }
}

function setupThemeToggle() {
    const toggle = document.getElementById("themeToggle");
    const currentTheme = getStoredTheme();
    applyTheme(currentTheme);

    if (!toggle) {
        return;
    }

    toggle.onclick = () => {
        const nextTheme = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
        localStorage.setItem("flowpi.theme", nextTheme);
        applyTheme(nextTheme);
    };
}

function getUserNameById(userId) {
    if (userId === null || userId === undefined || userId === "") {
        return "-";
    }
    return userNamesById.get(String(userId)) || "Unknown user";
}

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

function applySortControlsState() {
    const rankingBtn = document.getElementById("sortRankingBtn");
    const nameBtn = document.getElementById("sortNameBtn");
    if (!rankingBtn || !nameBtn) {
        return;
    }

    const rankingActive = sortMode === "ranking";
    rankingBtn.classList.toggle("active", rankingActive);
    nameBtn.classList.toggle("active", !rankingActive);
    rankingBtn.setAttribute("aria-pressed", String(rankingActive));
    nameBtn.setAttribute("aria-pressed", String(!rankingActive));
}

function setupSortControls() {
    const rankingBtn = document.getElementById("sortRankingBtn");
    const nameBtn = document.getElementById("sortNameBtn");
    if (!rankingBtn || !nameBtn) {
        return;
    }

    rankingBtn.onclick = () => {
        if (sortMode === "ranking") {
            return;
        }
        sortMode = "ranking";
        localStorage.setItem("flowpi.sortMode", sortMode);
        applySortControlsState();
        void loadTotals();
    };

    nameBtn.onclick = () => {
        if (sortMode === "name") {
            return;
        }
        sortMode = "name";
        localStorage.setItem("flowpi.sortMode", sortMode);
        applySortControlsState();
        void loadTotals();
    };

    applySortControlsState();
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
            data.tap_open ? "🟢 Tap open" : "🔴 Tap closed"
        );

        activeUserId = data.user;
        const flowLMin = Number(data.flow_l_min || 0);
        const flowLS = Number(data.flow_ml_s || 0) / 1000;
        const activeUserName = getUserNameById(activeUserId);

        setText("activeUser", activeUserName);
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

        userNamesById.clear();
        data.forEach(u => {
            userNamesById.set(String(u.id), String(u.name || "Unknown user"));
        });

        if (activeUserId !== null && activeUserId !== undefined) {
            const activeUserName = getUserNameById(activeUserId);
            setText("activeUser", activeUserName);
        }

        const byVolume = [...data].sort((a, b) => {
            const diff = Number(b.ml || 0) - Number(a.ml || 0);
            if (diff !== 0) {
                return diff;
            }
            return Number(a.id || 0) - Number(b.id || 0);
        });

        const volumeRanks = new Map();
        let previousRankKey = null;
        let rank = 0;

        byVolume.forEach((u, idx) => {
            const currentMl = Number(u.ml || 0);
            const rankKey = formatLiters(currentMl);
            if (previousRankKey === null || rankKey !== previousRankKey) {
                rank = idx + 1;
                previousRankKey = rankKey;
            }
            volumeRanks.set(String(u.id), rank);
        });

        const sortedUsers = [...data].sort((a, b) => {
            if (sortMode === "name") {
                return String(a.name || "").localeCompare(String(b.name || ""));
            }
            return Number(b.ml || 0) - Number(a.ml || 0);
        });

        const previousPositions = new Map();
        Array.from(container.children).forEach(card => {
            previousPositions.set(card.dataset.userId, card.getBoundingClientRect());
        });

        sortedUsers.forEach((u) => {
            const key = String(u.id);
            const rankByVolume = volumeRanks.get(key) || 0;
            let card = container.querySelector(`.user-card[data-user-id="${key}"]`);

            if (!card) {
                card = document.createElement("div");
                card.className = "user-card new-card";
                card.dataset.userId = key;
                card.setAttribute("role", "button");
                card.tabIndex = 0;
                card.onclick = async () => {
                    try {
                        await fetchJson(`/set_user/${u.id}`, { method: "POST" });
                        await loadStatus();
                        await loadTotals();
                    } catch (err) {
                        showApiError("set_user", err);
                    }
                };
                card.onkeydown = async (event) => {
                    if (event.key !== "Enter" && event.key !== " ") {
                        return;
                    }
                    event.preventDefault();
                    card.click();
                };
            }

            card.classList.toggle("active", u.id === activeUserId);
            card.innerHTML = `
                <div class="user-row">
                    <div class="user-name"><span class="user-rank">#${rankByVolume}</span><span>${u.name || "Unknown user"}</span></div>
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

function formatSessionTime(timestamp) {
    if (!timestamp) {
        return "in progress";
    }

    const normalized = String(timestamp).replace(" ", "T");
    const dt = new Date(normalized);
    if (Number.isNaN(dt.getTime())) {
        return timestamp;
    }
    return dt.toLocaleTimeString();
}

async function loadTapSessions() {
    const container = document.getElementById("tapSessions");
    if (!container) {
        return;
    }

    try {
        const sessions = await fetchJson("/tap_sessions");
        if (!Array.isArray(sessions) || sessions.length === 0) {
            container.innerHTML = '<div class="tap-session-item muted">No tap sessions yet.</div>';
            return;
        }

        container.innerHTML = sessions
            .map((session) => {
                const state = session.state === "closed" ? "Closed" : "Open";
                const stateClass = session.state === "closed" ? "is-closed" : "is-open";
                const liters = (Number(session.total_ml || 0) / 1000).toFixed(2);
                const stamp = formatSessionTime(session.closed_at || session.opened_at);
                const userName = String(session.user_name || getUserNameById(session.user_id));
                return `
                    <div class="tap-session-item ${stateClass}">
                        <div class="tap-session-main">${userName} • ${liters} L</div>
                        <div class="tap-session-meta">${state} • ${stamp}</div>
                    </div>
                `;
            })
            .join("");
    } catch (err) {
        container.innerHTML = '<div class="tap-session-item muted">Unable to load tap sessions.</div>';
        console.error("tap_sessions", err);
    }
}

function refresh() {
    void loadStatus();
    void loadTotal();
    void loadTotals();
    void loadTapSessions();
}

setInterval(refresh, 2000);

setupSortControls();
setupThemeToggle();
refresh();
