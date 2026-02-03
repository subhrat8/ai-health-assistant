import os
import math
import re
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

# ================= LOAD ENV =================
load_dotenv()
app = Flask(__name__)

# ================= API KEYS =================
GEMINI_KEYS = [
    os.getenv("GEMINI_API_KEY"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
]
GROK_API_KEY = os.getenv("GROK_API_KEY")

# ================= LANGUAGE =================
def language_name(code):
    return {
        "en-US": "English",
        "hi-IN": "Hindi",
        "te-IN": "Telugu",
        "ta-IN": "Tamil"
    }.get(code, "English")

# ================= GEO =================
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

def calculate_distance(a, b, c, d):
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

# ================= BOOKING LINKS =================
def booking_links(name, city):
    q = f"{name} {city}".replace(" ", "+")
    return {
        "google": f"https://www.google.com/maps/search/?api=1&query={q}",
        "practo": f"https://www.practo.com/search/doctors?query={q}",
        "justdial": f"https://www.justdial.com/search?q={q}",
    }

# ================= MEDICAL PLACES =================
def get_nearby_medical_places(lat, lon, city):
    places = []

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
            amenity = tags.get("amenity", "Medical")
            specialty = (
                tags.get("healthcare:speciality")
                or tags.get("medical_specialty")
                or "General Practice"
            )

            if name and e.get("lat") and e.get("lon"):
                places.append({
                    "name": name,
                    "type": amenity.capitalize(),
                    "specialty": specialty,
                    "distance": calculate_distance(lat, lon, e["lat"], e["lon"]),
                    "map": f"https://www.google.com/maps?q={e['lat']},{e['lon']}",
                    "booking": booking_links(name, city),
                    "rating": round(3.5 + (sum(ord(c) for c in name) % 15) / 10, 1)
                })
    except Exception as e:
        print("Medical place error:", e)

    return sorted(places, key=lambda x: x["distance"])[:8]

# ================= GROK CHAT =================
def ask_grok(prompt):
    if not GROK_API_KEY:
        return "I can help explain results or guide next steps."

    try:
        r = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "grok-1",
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=25
        )
        return r.json()["choices"][0]["message"]["content"]
    except:
        return "I can help explain results or guide next steps."

# ================= ROUTES =================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    city = request.form.get("city", "")
    symptoms = request.form.get("symptoms", "")
    lang = language_name(request.form.get("language", "en-US"))

    health = ""
    doctor = "General Physician"
    reason = "Initial consultation recommended"

    prompt = f"""
You are a medical information assistant.

Symptoms:
{symptoms}

Reply ONLY in {lang}.
Do NOT diagnose diseases.
Do NOT give medicine dosage.

Include:
• Possible cause (may be related to)
• Basic home care
• When to see a doctor
• Commonly used medicines (names only)

End strictly with:
Doctor: <specialist>
Reason: <short reason>

Always add:
"A doctor decides suitability and dosage based on age and health."
"""

    ai_text = ""

    # ===== GEMINI MULTI KEY =====
    for key in GEMINI_KEYS:
        if not key:
            continue
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            res = model.generate_content(prompt)
            ai_text = (res.text or "").strip()
            if ai_text:
                break
        except:
            continue

    # ===== PARSE =====
    if ai_text:
        for line in ai_text.splitlines():
            line = line.strip()
            if line.lower().startswith("doctor:"):
                doctor = line.split(":", 1)[1].strip()
            elif line.lower().startswith("reason:"):
                reason = line.split(":", 1)[1].strip()
            else:
                health += line + " "

    health = re.sub(r"\s+", " ", health).strip()

    lat, lon = get_coordinates(city)
    medical_places = get_nearby_medical_places(lat, lon, city)

    return render_template(
        "result.html",
        health=health,
        doctor=doctor,
        reason=reason,
        medical_places=medical_places
    )

@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.json.get("message", "")

    prompt = f"""
You are MedAssist Help Assistant.

Rules:
- General medical info only
- Medicine names allowed, NO dosage
- Suggest next steps/tests/doctor visit
- Never diagnose diseases

User:
{user_msg}
"""

    reply = ask_grok(prompt)
    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(debug=True)
