import os, json, tempfile
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore, auth as firebase_auth
import requests

# -------------------------------------------------------
# APP INIT
# -------------------------------------------------------
app = Flask(__name__, static_folder='.', template_folder='.')
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")
CORS(app, supports_credentials=True)

# -------------------------------------------------------
# FIREBASE INIT (SAFE FOR HF / ENV JSON)
# -------------------------------------------------------
db = None
firebase_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")

if firebase_json:
    try:
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            f.write(firebase_json)

        cred = credentials.Certificate(path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase initialized")

    except Exception as e:
        print("❌ Firebase init error:", e)
else:
    print("⚠️ FIREBASE_CREDENTIALS_JSON not set")

# -------------------------------------------------------
# GEMINI CONFIG
# -------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"

# -------------------------------------------------------
# SESSION HELPERS
# -------------------------------------------------------
def login_user(uid, email, name=None, picture=None):
    session["uid"] = uid
    session["email"] = email
    session["name"] = name
    session["picture"] = picture

def logout_user():
    session.clear()

def is_logged_in():
    return "uid" in session

# -------------------------------------------------------
# AUTH ROUTES
# -------------------------------------------------------
@app.route("/api/login", methods=["POST"])
def api_login():
    try:
        token = request.json.get("token")
        decoded = firebase_auth.verify_id_token(token)

        uid = decoded["uid"]
        email = decoded.get("email")
        name = decoded.get("name")
        picture = decoded.get("picture")

        login_user(uid, email, name, picture)

        if db:
            db.collection("users").document(uid).set({
                "email": email,
                "name": name,
                "picture": picture,
                "last_login": datetime.utcnow()
            }, merge=True)

        return jsonify({"ok": True})

    except Exception as e:
        print("❌ Login error:", e)
        return jsonify({"error": "Login failed"}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    logout_user()
    return jsonify({"ok": True})


@app.route("/api/me")
def api_me():
    if not is_logged_in():
        return jsonify({"authenticated": False})

    return jsonify({
        "authenticated": True,
        "id": session["uid"],
        "email": session.get("email"),
        "name": session.get("name"),
        "picture": session.get("picture")
    })

# -------------------------------------------------------
# ANALYSIS API
# -------------------------------------------------------
@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    if not db:
        return jsonify({"error": "Database not ready"}), 500

    data = request.json
    name = data.get("name")
    pitch = data.get("pitch")
    description = data.get("description")
    industry = data.get("industry")
    mode = data.get("mode", "fast")

    if not (name or pitch or description):
        return jsonify({"error": "Missing input"}), 400

    # Create Firestore doc
    doc_ref = db.collection("analyses").document()
    doc_id = doc_ref.id

    doc_ref.set({
        "name": name,
        "pitch": pitch,
        "description": description,
        "industry": industry,
        "mode": mode,
        "user_id": session.get("uid"),
        "status": "running",
        "created_at": datetime.utcnow()
    })

    try:
        # ---------------- GEMINI CALL ----------------
        if not GEMINI_API_KEY:
            result_text = "Mock analysis (GEMINI_API_KEY not set)"
        else:
            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"""
Analyze this startup idea and give insights.

Startup Name: {name}
Pitch: {pitch}
Description: {description}
Industry: {industry}
Mode: {mode}

Give:
1. Market fit
2. Strengths
3. Risks
4. Suggestions
5. Score out of 10
"""
                    }]
                }]
            }

            r = requests.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                json=payload,
                timeout=30
            )

            gem = r.json()
            print("Gemini response:", gem)

            if "candidates" not in gem:
                raise Exception(gem)

            result_text = gem["candidates"][0]["content"]["parts"][0]["text"]

        # Save result
        doc_ref.set({
            "status": "done",
            "completed_at": datetime.utcnow(),
            "result": result_text
        }, merge=True)

    except Exception as e:
        print("Gemini error:", e)
        doc_ref.set({
            "status": "failed",
            "error": str(e)
        }, merge=True)
        return jsonify({"error": "Gemini failed"}), 500

    return jsonify({"ok": True, "id": doc_id})

# -------------------------------------------------------
# DATA FETCH
# -------------------------------------------------------
@app.route("/api/doc/<docid>")
def api_doc(docid):
    d = db.collection("analyses").document(docid).get()
    if not d.exists:
        return jsonify({"error": "Not found"}), 404
    return jsonify(d.to_dict())


@app.route("/api/pdf/<docid>")
def api_pdf(docid):
    d = db.collection("analyses").document(docid).get()
    if not d.exists:
        return "Not found", 404

    content = json.dumps(d.to_dict(), indent=2, default=str)
    return (content, 200, {
        "Content-Type": "application/octet-stream",
        "Content-Disposition": f'attachment; filename="analysis_{docid}.txt"'
    })


@app.route("/api/history")
def api_history():
    q = db.collection("analyses").order_by(
        "created_at", direction=firestore.Query.DESCENDING
    ).limit(50)

    items = []
    for d in q.stream():
        x = d.to_dict()
        x["id"] = d.id
        items.append(x)

    return jsonify({"items": items})

# -------------------------------------------------------
# STATIC FILES
# -------------------------------------------------------
@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)

# -------------------------------------------------------
# RUN
# -------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
