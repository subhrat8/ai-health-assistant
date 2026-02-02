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

# ================= LOCATION =================
def get_coordinates(city):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": city, "format": "json", "limit": 1},
            headers={"User-Agent": "medassist"},
            timeout=10
        )
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        print("Location error:", e)

    return 20.5937, 78.9629  # India fallback

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2 +
        math.cos(math.radians(lat1)) *
        math.cos(math.radians(lat2)) *
        math.sin(dlon / 2) ** 2
    )
    return round(2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)

# ================= MEDICAL PLACES (Hospitals + Clinics + Doctors) =================
def get_nearby_medical_places(lat, lon):
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
        r = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=query,
            timeout=15
        )
        data = r.json()

        for item in data.get("elements", []):
            tags = item.get("tags", {})
            name = tags.get("name")
            amenity = tags.get("amenity")
            specialty = (
                tags.get("healthcare:speciality")
                or tags.get("medical_specialty")
                or "General Practice"
            )

            if name and item.get("lat") and item.get("lon"):
                places.append({
                    "name": name,
                    "type": amenity.capitalize(),   # Hospital / Clinic / Doctors
                    "specialty": specialty,
                    "distance": calculate_distance(
                        lat, lon, item["lat"], item["lon"]
                    ),
                    "map": f"https://www.google.com/maps?q={item['lat']},{item['lon']}"
                })

    except Exception as e:
        print("Medical places error:", e)

    return places[:8]

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
        data = r.json()
        return data["choices"][0]["message"]["content"]

    except Exception as e:
        print("Grok error:", e)
        return "I can help explain results or guide next steps."

# ================= ROUTES =================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    city = request.form.get("city", "")
    symptoms = request.form.get("symptoms", "")
    language = request.form.get("language", "en-US")

    lang = language_name(language)

    health = ""
    doctor = "General Physician"
    reason = "Initial consultation recommended"

    prompt = f"""
You are a medical information assistant.

Symptoms:
{symptoms}

Reply ONLY in {lang}.

Rules:
- Do NOT diagnose diseases
- Do NOT give dosage
- Use wording like "may be related to"

Include:
• Possible cause
• Home care
• When to see a doctor
• Commonly used medicines (names only)

End strictly with:
Doctor: <specialist>
Reason: <short reason>

Always include:
"A doctor decides suitability and dosage based on age and health."
"""

    ai_text = ""

    # ===== GEMINI MULTI-KEY FALLBACK =====
    for key in GEMINI_KEYS:
        if not key:
            continue
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            ai_text = (response.text or "").strip()
            if ai_text:
                break
        except Exception as e:
            print("Gemini error:", e)

    # ===== PARSE AI RESPONSE =====
    if ai_text:
        for line in ai_text.splitlines():
            line = line.strip()
            if line.lower().startswith("doctor:"):
                doctor = line.split(":", 1)[1].strip()
            elif line.lower().startswith("reason:"):
                reason = line.split(":", 1)[1].strip()
            else:
                health += line + " "

    # ===== CLEAN TEXT =====
    health = re.sub(r'([a-z])([A-Z])', r'\1 \2', health)
    health = re.sub(r'\s+', ' ', health).strip()

    lat, lon = get_coordinates(city)

    # NEW: hospitals + private doctors + clinics
    medical_places = get_nearby_medical_places(lat, lon)

    return render_template(
        "result.html",
        health=health,
        doctor=doctor,
        reason=reason,
        medical_places=medical_places
    )

# ================= CHAT API =================
@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.json.get("message", "")

    prompt = f"""
You are MedAssist Help Assistant.

Rules:
- General medical information only
- Medicine names allowed (NO dosage)
- Suggest next steps, tests, doctor visit
- Never diagnose diseases

User question:
{user_msg}
"""

    reply = ask_grok(prompt)
    return jsonify({"reply": reply})

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
