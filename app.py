import os
import math
import re
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

# ================= BASIC SETUP =================
load_dotenv()
app = Flask(__name__)

GEMINI_KEYS = [
    os.getenv("GEMINI_API_KEY"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
]

# ================= LANGUAGE =================
def language_name(code):
    return {
        "en-US": "English",
        "hi-IN": "Hindi",
        "te-IN": "Telugu",
        "ta-IN": "Tamil"
    }.get(code, "English")

# ================= LOCATION =================
def get_coordinates(city):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": city, "format": "json", "limit": 1},
            headers={"User-Agent": "medassist"},
            timeout=10
        )
        d = r.json()
        if d:
            return float(d[0]["lat"]), float(d[0]["lon"])
    except:
        pass
    return 20.5937, 78.9629  # India fallback

def distance(a, b, c, d):
    R = 6371
    dlat = math.radians(c - a)
    dlon = math.radians(d - b)
    x = (
        math.sin(dlat / 2) ** 2 +
        math.cos(math.radians(a)) *
        math.cos(math.radians(c)) *
        math.sin(dlon / 2) ** 2
    )
    return round(2 * R * math.atan2(math.sqrt(x), math.sqrt(1 - x)), 2)

# ================= MEDICAL PLACES =================
def get_nearby_medical_places(lat, lon, city):
    results = []

    query = f"""
    [out:json];
    (
      node["amenity"="hospital"](around:30000,{lat},{lon});
      node["amenity"="clinic"](around:30000,{lat},{lon});
      node["amenity"="doctors"](around:30000,{lat},{lon});
    );
    out;
    """

    try:
        r = requests.post("https://overpass-api.de/api/interpreter", data=query, timeout=15)
        data = r.json()

        for e in data.get("elements", []):
            tags = e.get("tags", {})
            name = tags.get("name")
            speciality = (
                tags.get("healthcare:speciality")
                or tags.get("medical_specialty")
                or "General Care"
            )

            if name and e.get("lat") and e.get("lon"):
                results.append({
                    "name": name,
                    "speciality": speciality,
                    "distance": distance(lat, lon, e["lat"], e["lon"]),
                    "map": f"https://www.google.com/maps?q={e['lat']},{e['lon']}"
                })
    except:
        pass

    return sorted(results, key=lambda x: x["distance"])[:6]

# ================= AI HEALTH GUIDANCE =================
def ai_health_guidance(symptoms, lang):
    prompt = f"""
You are a health information assistant.

Symptoms:
{symptoms}

Reply ONLY in {lang}.
Do NOT diagnose.
Do NOT give dosage.

Explain clearly:
- What these symptoms may be related to
- Basic home care
- When medical help is needed

End with:
Doctor: <specialist>
Reason: <short reason>
"""

    for key in GEMINI_KEYS:
        if not key:
            continue
        try:
            genai.configure(api_key=key, transport="rest")
            model = genai.GenerativeModel("gemini-1.5-flash")
            res = model.generate_content(prompt)

            if res and res.candidates:
                text = res.candidates[0].content.parts[0].text.strip()
                if len(text) > 80:
                    return text
        except:
            continue

    return (
        "Your symptoms may indicate a common health issue. "
        "Ensure rest, hydration, and basic care. "
        "If symptoms continue or worsen, consult a doctor.\n\n"
        "Doctor: General Physician\n"
        "Reason: Initial medical evaluation"
    )

# ================= ROUTES =================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    city = request.form.get("city", "")
    symptoms = request.form.get("symptoms", "")
    lang = language_name(request.form.get("language", "en-US"))

    ai_text = ai_health_guidance(symptoms, lang)

    health = ""
    doctor = "General Physician"
    reason = "Initial consultation recommended"

    for line in ai_text.splitlines():
        l = line.strip()
        if l.lower().startswith("doctor:"):
            doctor = l.split(":", 1)[1].strip()
        elif l.lower().startswith("reason:"):
            reason = l.split(":", 1)[1].strip()
        else:
            health += l + " "

    health = re.sub(r"\s+", " ", health).strip()

    lat, lon = get_coordinates(city)
    medical_places = get_nearby_medical_places(lat, lon, city)

    return render_template(
        "result.html",
        health=health,
        doctor=doctor,
        reason=reason,
        medical_places=medical_places,
        city=city,
        symptoms=symptoms
    )

# ================= WEBSITE ASSISTANT =================
@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.json.get("message", "")
    context = request.json.get("context", "")

    prompt = f"""
You are MedAssist Help Assistant.

Context:
{context}

User question:
{user_msg}

Rules:
- Friendly
- Explain results
- Suggest next steps
- No diagnosis
- No dosage
"""

    for key in GEMINI_KEYS:
        if not key:
            continue
        try:
            genai.configure(api_key=key, transport="rest")
            model = genai.GenerativeModel("gemini-1.5-flash")
            res = model.generate_content(prompt)

            if res and res.candidates:
                return jsonify({
                    "reply": res.candidates[0].content.parts[0].text.strip()
                })
        except:
            continue

    return jsonify({
        "reply": "I can help explain your results or guide you on next steps."
    })

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
