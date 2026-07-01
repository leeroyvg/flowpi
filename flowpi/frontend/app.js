function resolveApiBase() {
    const configuredBase = window.FLOWPI_API_BASE || localStorage.getItem("flowpi.apiBase");
    if (configuredBase) {
        return configuredBase.replace(/\/$/, "");
    }

    const { protocol, hostname, port } = window.location;

    if (port === "5000") {
        return `${protocol}//${hostname}:5000`;
    }

    return `${protocol}//${hostname}:5000`;
}

const API = resolveApiBase();

let activeUserId = null;

function setText(id, value) {
    document.getElementById(id).innerText = value;
}

function showApiError(context, error) {
    console.error(context, error);
    setText("apiStatus", "Backend unavailable");
}

async function fetchJson(path, options = {}) {
    const res = await fetch(`${API}${path}`, {
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

        setText("activeUser", "User " + activeUserId);
        setText("apiStatus", "Connected");
    } catch (err) {
        showApiError("status", err);
    }
}

async function loadTotal() {
    try {
        const data = await fetchJson("/user_total");

        setText("user_total", data.total_ml.toFixed(1) + " ml");
    } catch (err) {
        showApiError("user_total", err);
    }
}

async function loadTotals() {
    const container = document.getElementById("user_totals");
    try {
        const data = await fetchJson("/user_totals");

        container.innerHTML = "";

        data.forEach(u => {
            const div = document.createElement("button");
            div.className = "user-card";
            div.type = "button";

            if (u.id === activeUserId) {
                div.classList.add("active");
            }

            div.innerHTML = `
                <div class="user-row">
                    <div class="user-name">${u.name}</div>
                    <div class="user-ml">${u.ml.toFixed(1)} ml</div>
                </div>
            `;

            div.onclick = async () => {
                try {
                    await fetchJson(`/set_user/${u.id}`, { method: "POST" });
                    await loadStatus();
                    await loadTotals();
                } catch (err) {
                    showApiError("set_user", err);
                }
            };

            container.appendChild(div);
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
