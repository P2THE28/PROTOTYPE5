/* ======================= SHORTCUT ======================= */
const el = (id) => document.getElementById(id);

/* ======================= FIREBASE CONFIG ======================= */
const firebaseConfig = {
  apiKey: "AIzaSyDhMJIwXMjuIOkwKgsp2x2C4llteWvie1E",
  authDomain: "ai-startup-success-predi-bdfa8.firebaseapp.com",
  projectId: "ai-startup-success-predi-bdfa8",
};
firebase.initializeApp(firebaseConfig);

const auth = firebase.auth();

/* ======================= LOGIN FUNCTION ======================= */
async function handleGoogleLogin() {
  const provider = new firebase.auth.GoogleAuthProvider();

  try {
    const result = await auth.signInWithPopup(provider);
    const idToken = await result.user.getIdToken();

    await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",   // 🔥 MUST
      body: JSON.stringify({ token: idToken }) // ✅ FIXED
    });

    updateAuthUI();
  } catch (err) {
    console.error("Login error:", err);
    alert("Login failed");
  }
}

/* ======================= LOGOUT FUNCTION ======================= */
async function handleLogout() {
  await fetch("/api/logout", {
    method: "POST",
    credentials: "include"
  });
  await auth.signOut();
  updateAuthUI();
}


/* ======================= UPDATE LOGIN UI ======================= */
async function updateAuthUI() {
  const openGoogle = el("openGoogle");
  const userSection = el("userSection");
  const userPhoto = el("userPhoto");
  const userDropdown = el("userDropdown");
  const userName = el("userName");
  const userEmail = el("userEmail");

  try {
    const res = await fetch("/api/me", {
  credentials: "include"   // 🔥 MOST IMPORTANT
});

    const j = await res.json();

    if (j.authenticated) {
      // (A) HIDE LOGIN BUTTON
      openGoogle.classList.add("hidden");

      // (B) SHOW PROFILE SECTION
      userSection.classList.remove("hidden");
      userName.textContent = j.name || "User";
      userEmail.textContent = j.email || "";
      userPhoto.src = j.picture || "https://i.imgur.com/4ZQZ4ZQ.png";

      el("openDeep").disabled = false;
    } else {
      // (A) SHOW LOGIN
      openGoogle.classList.remove("hidden");

      // (B) HIDE PROFILE
      userSection.classList.add("hidden");

      openGoogle.onclick = handleGoogleLogin;
      el("openDeep").disabled = true;
    }
  } catch (e) {
    console.warn("Auth check failed:", e);
  }
}
updateAuthUI();

/* ======================= DROPDOWN TOGGLE ======================= */
el("userSection").addEventListener("click", () => {
  el("userDropdown").classList.toggle("hidden");
});

document.addEventListener("click", (e) => {
  if (!el("userSection").contains(e.target)) {
    el("userDropdown").classList.add("hidden");
  }
});

/* ======================= SMOOTH SCROLL TO CARDS ======================= */
document.querySelectorAll("#openFast, #openDeep").forEach((btn) => {
  btn.addEventListener("click", () => {
    document
      .getElementById("analysisSection")
      .scrollIntoView({ behavior: "smooth" });
  });
});

/* ======================= OPEN MODAL ======================= */
function openModal(mode) {
  el("inputModal").classList.remove("hidden");
  el("modalTitle").textContent =
    mode === "deep" ? "Start Deep Analysis" : "Start Fast Analysis";
  el("analyzeBtn").dataset.mode = mode;
  el("formStatus").textContent = "";
}

/* Fast Analysis Card Button */
document.querySelectorAll(".start").forEach((b) => {
  b.addEventListener("click", () => {
    openModal(b.dataset.mode);
  });
});

/* Deep Button Auth Guard */
el("openDeep").addEventListener("click", async () => {
  const me = await fetch("/api/me", { credentials: "include" })
                  .then(r => r.json());

  if (!me.authenticated) {
    alert("Please login first.");
    return;
  }
});


/* Close Modal */
el("closeModal").onclick = () => el("inputModal").classList.add("hidden");
el("cancelBtn").onclick = () => el("inputModal").classList.add("hidden");

/* ======================= ANALYZE ======================= */
el("analyzeBtn").addEventListener("click", async function () {
  const mode = this.dataset.mode;

  const name = el("name").value.trim();
  const pitch = el("pitch").value.trim();
  const description = el("description").value.trim();
  const industry = el("industry").value.trim();

  if (!name && !pitch && !description) {
    el("formStatus").textContent = "Please fill at least one field.";
    return;
  }

  el("formStatus").textContent = "Running AI analysis...";

  try {
    const resp = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        pitch,
        description,
        industry,
        mode,
      }),
    });

    const j = await resp.json();

    if (!resp.ok) {
      el("formStatus").textContent = j.error || "Error!";
      return;
    }

    const id = j.id;

    el("formStatus").innerHTML = `
      Analysis Ready 🎉 <br>
      <a href="/api/doc/${id}" target="_blank">View JSON</a> •
      <a href="/api/pdf/${id}" target="_blank">Download TXT</a>
    `;

    fetchHistory();
  } catch (err) {
    el("formStatus").textContent = "Network error.";
  }
});

/* ======================= HISTORY LOADER ======================= */
async function fetchHistory() {
  const historyList = el("historyList");

  try {
    historyList.innerHTML = "Loading...";

    const r = await fetch("/api/history");
    const j = await r.json();

    historyList.innerHTML = "";

    if (!j.items || j.items.length === 0) {
      historyList.innerHTML = '<div class="muted">No recent analyses</div>';
      return;
    }

    j.items.forEach((it) => {
      const div = document.createElement("div");
      div.className = "history-item";

      div.innerHTML = `
        <strong>${it.name || it.pitch || "Unnamed"}</strong>
        <span class="muted">(${it.industry || "General"})</span>
        <div class="small muted">
          Mode: ${it.mode} • 
          <a href="/api/doc/${it.id}" target="_blank">json</a> •
          <a href="/api/pdf/${it.id}" target="_blank">txt</a>
        </div>
      `;

      historyList.appendChild(div);
    });
  } catch (e) {
    console.error(e);
  }
}

fetchHistory();
