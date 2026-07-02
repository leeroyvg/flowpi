function normalizeBase(base) {
    return String(base || "").replace(/\/$/, "");
}

function getApiCandidates() {
    const params = new URLSearchParams(window.location.search);
    const configuredBase = params.get("api") || localStorage.getItem("flowpi.apiBase");
    const { protocol, hostname, origin } = window.location;
    const candidates = [];

    if (configuredBase) {
        candidates.push(normalizeBase(configuredBase));
    }

    if (protocol === "http:" || protocol === "https:") {
        candidates.push(origin);
        if (hostname) {
            candidates.push(`${protocol}//${hostname}:5000`);
        }
    }

    candidates.push("http://127.0.0.1:5000", "http://localhost:5000");
    return [...new Set(candidates.map(normalizeBase))];
}

let apiBasePromise = null;
let adminSessionToken = localStorage.getItem("flowpi.adminSessionToken") || "";

function setStatus(text) {
    const el = document.getElementById("adminStatus");
    if (el) {
        el.innerText = text;
    }
}

async function resolveApiBase() {
    if (apiBasePromise) {
        return apiBasePromise;
    }

    apiBasePromise = (async () => {
        const candidates = getApiCandidates();

        for (const base of candidates) {
            try {
                const res = await fetch(`${base}/health`, {
                    headers: { Accept: "application/json" },
                });

                if (res.ok) {
                    localStorage.setItem("flowpi.apiBase", base);
                    return base;
                }
            } catch (error) {
                console.debug("health probe failed", base, error);
            }
        }

        throw new Error("Backend not reachable");
    })();

    return apiBasePromise;
}

async function fetchJson(path, options = {}) {
    const apiBase = await resolveApiBase();
    const headers = {
        Accept: "application/json",
        ...(options.headers || {}),
    };

    if (adminSessionToken) {
        headers["X-Admin-Session"] = adminSessionToken;
    }

    const response = await fetch(`${apiBase}${path}`, {
        ...options,
        headers,
    });

    if (!response.ok) {
        const text = await response.text();
        throw new Error(`${path} failed (${response.status}): ${text}`);
    }

    return response.json();
}

function setLoggedInState(isLoggedIn) {
    const loginCard = document.getElementById("loginCard");
    const editorCard = document.getElementById("editorCard");

    if (loginCard) {
        loginCard.classList.toggle("hidden", isLoggedIn);
    }

    if (editorCard) {
        editorCard.classList.toggle("hidden", !isLoggedIn);
    }

    setStatus(isLoggedIn ? "Admin session active" : "Please sign in");
}

async function checkSession() {
    if (!adminSessionToken) {
        setLoggedInState(false);
        return false;
    }

    try {
        const session = await fetchJson("/admin/session", { method: "GET" });
        if (!session.authenticated) {
            adminSessionToken = "";
            localStorage.removeItem("flowpi.adminSessionToken");
            setLoggedInState(false);
            return false;
        }

        setLoggedInState(true);
        return true;
    } catch (error) {
        console.error("session check failed", error);
        setLoggedInState(false);
        return false;
    }
}

function renderUsers(users) {
    const container = document.getElementById("adminUsers");
    if (!container) {
        return;
    }

    container.innerHTML = "";

    const sorted = [...users].sort((a, b) => Number(b.ml || 0) - Number(a.ml || 0));
    sorted.forEach((user) => {
        const row = document.createElement("div");
        row.className = "admin-user-row";
        row.innerHTML = `
            <input class="admin-name-input" type="text" maxlength="40" value="${String(user.name || "").replace(/"/g, "&quot;")}" aria-label="Name for ${user.name || "Unknown user"}">
            <div class="admin-user-input-wrap">
                <input class="admin-volume-input" type="number" min="0" step="0.01" value="${(Number(user.ml || 0) / 1000).toFixed(2)}" aria-label="Volume in liters for ${user.name}">
                <span class="admin-unit">L</span>
            </div>
            <div class="admin-actions">
                <button class="admin-save-btn" type="button">Save</button>
                <button class="admin-delete-btn" type="button">Delete</button>
            </div>
        `;

        const nameInput = row.querySelector(".admin-name-input");
        const input = row.querySelector(".admin-volume-input");
        const saveBtn = row.querySelector(".admin-save-btn");
        const deleteBtn = row.querySelector(".admin-delete-btn");

        saveBtn.onclick = async () => {
            const name = String(nameInput.value || "").trim();
            const liters = Number(input.value);
            if (!name) {
                setStatus("Use a valid name");
                return;
            }
            if (!Number.isFinite(liters) || liters < 0) {
                setStatus("Use a valid volume");
                return;
            }

            try {
                await fetchJson(`/admin/users/${user.id}/name`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ name }),
                });

                await fetchJson(`/admin/users/${user.id}/volume`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ total_ml: liters * 1000 }),
                });

                setStatus(`Updated ${name}`);
                await loadUsers();
            } catch (error) {
                console.error("volume update failed", error);
                if (String(error.message).includes("403")) {
                    adminSessionToken = "";
                    localStorage.removeItem("flowpi.adminSessionToken");
                    setLoggedInState(false);
                    setStatus("Session expired, sign in again");
                    return;
                }
                setStatus("Update failed");
            }
        };

        deleteBtn.onclick = async () => {
            const confirmed = window.confirm(`Delete ${nameInput.value || user.name}? This cannot be undone.`);
            if (!confirmed) {
                return;
            }

            try {
                await fetchJson(`/admin/users/${user.id}`, { method: "DELETE" });
                setStatus(`Deleted ${user.name}`);
                await loadUsers();
            } catch (error) {
                console.error("delete user failed", error);
                if (String(error.message).includes("403")) {
                    adminSessionToken = "";
                    localStorage.removeItem("flowpi.adminSessionToken");
                    setLoggedInState(false);
                    setStatus("Session expired, sign in again");
                    return;
                }
                setStatus("Delete failed");
            }
        };

        container.appendChild(row);
    });
}

function setupAddUserForm() {
    const form = document.getElementById("addUserForm");
    const input = document.getElementById("newUserName");
    if (!form || !input) {
        return;
    }

    form.onsubmit = async (event) => {
        event.preventDefault();
        const name = String(input.value || "").trim();
        if (!name) {
            setStatus("Enter a user name");
            return;
        }

        try {
            await fetchJson("/admin/users", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ name }),
            });
            input.value = "";
            setStatus(`Added ${name}`);
            await loadUsers();
        } catch (error) {
            console.error("add user failed", error);
            if (String(error.message).includes("403")) {
                adminSessionToken = "";
                localStorage.removeItem("flowpi.adminSessionToken");
                setLoggedInState(false);
                setStatus("Session expired, sign in again");
                return;
            }
            setStatus("Add user failed");
        }
    };
}

async function loadUsers() {
    try {
        const users = await fetchJson("/user_totals", { method: "GET" });
        renderUsers(users);
    } catch (error) {
        console.error("load users failed", error);
        setStatus("Failed to load users");
    }
}

function setupLoginForm() {
    const form = document.getElementById("loginForm");
    if (!form) {
        return;
    }

    form.onsubmit = async (event) => {
        event.preventDefault();

        const username = document.getElementById("adminUsername").value.trim();
        const password = document.getElementById("adminPassword").value;

        try {
            const response = await fetchJson("/admin/login", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ username, password }),
            });

            adminSessionToken = String(response.session_token || "");
            if (!adminSessionToken) {
                throw new Error("missing session token");
            }

            localStorage.setItem("flowpi.adminSessionToken", adminSessionToken);
            setLoggedInState(true);
            setStatus("Signed in");
            form.reset();
            await loadUsers();
        } catch (error) {
            console.error("login failed", error);
            const message = String(error.message || "");
            if (message.includes("503")) {
                setStatus("Admin login not configured on backend");
                return;
            }
            setStatus("Login failed");
        }
    };
}

function setupLogout() {
    const logoutBtn = document.getElementById("logoutBtn");
    if (!logoutBtn) {
        return;
    }

    logoutBtn.onclick = async () => {
        try {
            await fetchJson("/admin/logout", { method: "POST" });
        } catch (error) {
            console.debug("logout request failed", error);
        }

        adminSessionToken = "";
        localStorage.removeItem("flowpi.adminSessionToken");
        setLoggedInState(false);
    };
}

async function init() {
    setupLoginForm();
    setupLogout();
    setupAddUserForm();

    try {
        await resolveApiBase();
    } catch (error) {
        console.error(error);
        setStatus("Backend unavailable");
        setLoggedInState(false);
        return;
    }

    const authenticated = await checkSession();
    if (authenticated) {
        await loadUsers();
    }
}

void init();
