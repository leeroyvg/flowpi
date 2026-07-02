function normalizeBase(base) {
    return String(base || "").replace(/\/$/, "");
}

function getApiCandidates() {
    const params = new URLSearchParams(window.location.search);
    const configuredBase = params.get("api") || localStorage.getItem("flowpi.apiBase");
    const { protocol, hostname, origin, pathname } = window.location;
    const candidates = [];

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

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.innerText = value;
    }
}

function mlToLiters(ml) {
    return Number(ml || 0) / 1000;
}

function formatLiters(ml) {
    return `${mlToLiters(ml).toFixed(2)} L`;
}

function formatPercent(value) {
    return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

function setStatus(text) {
    setText("statsStatus", text);
}

async function resolveApiBase() {
    if (apiBasePromise) {
        return apiBasePromise;
    }

    apiBasePromise = (async () => {
        const candidates = getApiCandidates();

        for (const base of candidates) {
            try {
                const response = await fetch(`${base}/health`, {
                    headers: { Accept: "application/json" },
                });

                if (response.ok) {
                    localStorage.setItem("flowpi.apiBase", base);
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

async function fetchJson(path, options = {}) {
    const apiBase = await resolveApiBase();
    const response = await fetch(`${apiBase}${path}`, {
        headers: {
            Accept: "application/json",
            ...(options.headers || {}),
        },
        ...options,
    });

    if (!response.ok) {
        throw new Error(`${path} failed with status ${response.status}`);
    }

    return response.json();
}

function renderRows(users, totalMl) {
    const container = document.getElementById("statsRows");
    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (!users.length) {
        container.innerHTML = '<p class="metric-sub">No user data available yet.</p>';
        return;
    }

    let previousRankKey = null;
    let rank = 0;

    users.forEach((user, index) => {
        const userMl = Number(user.ml || 0);
        const share = totalMl > 0 ? userMl / totalMl : 0;
        const rankKey = formatLiters(userMl);

        if (previousRankKey === null || rankKey !== previousRankKey) {
            rank = index + 1;
            previousRankKey = rankKey;
        }

        const row = document.createElement("article");
        row.className = "stats-row";
        row.innerHTML = `
            <div class="stats-row-head">
                <div class="stats-row-rank">#${rank}</div>
                <div class="stats-row-name">${user.name}</div>
                <div class="stats-row-value">${formatLiters(userMl)}</div>
                <div class="stats-row-share">${formatPercent(share)}</div>
            </div>
            <div class="stats-row-bar-track">
                <div class="stats-row-bar" style="width:${(share * 100).toFixed(2)}%"></div>
            </div>
        `;

        container.appendChild(row);
    });
}

function renderHighlights(users, totalMl, status, tapStats) {
    const top = users[0];
    const second = users[1];
    const last = users[users.length - 1];

    if (!top) {
        setText("highlightTop", "Top user: -");
        setText("highlightClose", "Closest race: -");
        setText("highlightSpread", "Spread: -");
        setText("highlightAvgTap", "Average per tap: -");
        setText("highlightPulse", "Flow pulse: -");
        return;
    }

    const topShare = totalMl > 0 ? Number(top.ml || 0) / totalMl : 0;
    setText("highlightTop", `Top user: ${top.name} with ${formatPercent(topShare)}`);

    if (second) {
        const diffMl = Math.abs(Number(top.ml || 0) - Number(second.ml || 0));
        setText("highlightClose", `Closest race: ${top.name} vs ${second.name} (${formatLiters(diffMl)} difference)`);
    } else {
        setText("highlightClose", "Closest race: waiting for another user");
    }

    const spreadMl = Math.max(0, Number(top.ml || 0) - Number(last?.ml || 0));
    setText("highlightSpread", `Spread: ${formatLiters(spreadMl)} from top to bottom`);

    if (!tapStats) {
        setText("highlightAvgTap", "Average per tap: restart backend to enable");
    } else {
        const tapCount = Number(tapStats.tap_count || 0);
        const avgMlPerTap = Number(tapStats.avg_ml_per_tap || 0);
        if (tapCount > 0) {
            setText("highlightAvgTap", `Average per tap: ${formatLiters(avgMlPerTap)} across ${tapCount} taps`);
        } else {
            setText("highlightAvgTap", "Average per tap: waiting for tap data");
        }
    }

    const flowLMin = Number(status.flow_l_min || 0);
    const flowLS = Number(status.flow_ml_s || 0) / 1000;
    setText("highlightPulse", `Flow pulse: ${flowLMin.toFixed(2)} L/min (${flowLS.toFixed(2)} L/s)`);
}

function renderSummary(users, totalMl, status, tapStats) {
    const userCount = users.length;
    const leader = users[0];

    setText("statsTotal", formatLiters(totalMl));
    setText("statsAverage", formatLiters(userCount ? totalMl / userCount : 0));
    setText("statsUserCount", `${userCount} users`);

    if (leader) {
        const share = totalMl > 0 ? Number(leader.ml || 0) / totalMl : 0;
        setText("statsLeader", leader.name);
        setText("statsLeaderShare", `${formatPercent(share)} share`);
    } else {
        setText("statsLeader", "-");
        setText("statsLeaderShare", "0.0% share");
    }

    const isTapOpen = Boolean(status.tap_open);
    const usersById = new Map(users.map((u) => [String(u.id), String(u.name || "Unknown user")]));
    const activeUser = status.user === null || status.user === undefined
        ? "-"
        : (usersById.get(String(status.user)) || "Unknown user");

    if (!tapStats) {
        setText("statsAvgTap", "-");
        setText("statsTapCount", "restart backend to enable");
    } else {
        const tapCount = Number(tapStats.tap_count || 0);
        const avgMlPerTap = Number(tapStats.avg_ml_per_tap || 0);
        setText("statsAvgTap", formatLiters(avgMlPerTap));
        setText("statsTapCount", `${tapCount} taps`);
    }

    setText("statsTap", isTapOpen ? "🟢 Tap open" : "🔴 Tap closed");
    setText("statsActiveUser", `Active user: ${activeUser}`);
}

function updateTimestamp() {
    const stamp = new Date();
    setText("statsUpdatedAt", `Updated at ${stamp.toLocaleTimeString()}`);
}

async function loadStats() {
    try {
        const [users, status, tapStats] = await Promise.all([
            fetchJson("/user_totals"),
            fetchJson("/status"),
            fetchJson("/tap_stats").catch(() => null),
        ]);

        const sorted = [...users].sort((a, b) => Number(b.ml || 0) - Number(a.ml || 0));
        const totalMl = sorted.reduce((sum, user) => sum + Number(user.ml || 0), 0);

        renderSummary(sorted, totalMl, status, tapStats);
        renderRows(sorted, totalMl);
        renderHighlights(sorted, totalMl, status, tapStats);

        setStatus("Live data");
        updateTimestamp();
    } catch (error) {
        console.error("stats load failed", error);
        setStatus("Backend unavailable");
    }
}

setInterval(loadStats, 3000);
void loadStats();
