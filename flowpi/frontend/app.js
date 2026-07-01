const API = "http://192.168.137.168:5000";

let activeUserId = null;

async function loadStatus() {
    try {
        const res = await fetch(`${API}/status`);
        const data = await res.json();

        document.getElementById("tapStatus").innerText =
            data.tap_open ? "🟢 TAP OPEN" : "🔴 TAP CLOSED";

        activeUserId = data.user;

        document.getElementById("activeUser").innerText =
            "User " + activeUserId;
    } catch (err) {
        console.error("API ERROR", err);
    }
}

async function loadTotal() {
    const res = await fetch(`${API}/user_total`);
    const data = await res.json();

    document.getElementById("user_total").innerText =
        data.total_ml.toFixed(1) + " ml";
}

async function loadTotals() {
    const res = await fetch(`${API}/user_totals`);
    const data = await res.json();

    const container = document.getElementById("user_totals");
    container.innerHTML = "";

    data.forEach(u => {
        const div = document.createElement("div");
        div.className = "user-card";

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
            await fetch(`${API}/set_user/${u.id}`);

            await loadStatus();
            await loadTotals();
        };

        container.appendChild(div);
    });
}

function refresh() {
    loadStatus();
    loadTotal();
    loadTotals();
}

setInterval(refresh, 2000);

refresh();
