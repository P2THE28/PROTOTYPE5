---
title: "AI Startup Success Predictor"
emoji: "🚀"
colorFrom: "indigo"
colorTo: "purple"
sdk: "docker"
pinned: false
---
# StartupAI front + run with existing app.py

Place files `index.html`, `style.css`, `script.js` in same folder as your existing `app.py` (the one you uploaded).

Install Python deps:
```bash
python -m venv venv
source venv/bin/activate   # windows: venv\Scripts\activate
pip install -r requirements.txt
# optionally install firebase-admin if you'll use Firestore
pip install firebase-admin

