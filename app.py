import os
import math
import re
import requests
from flask import Flask, render_template, request
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

# ================= FALLBACK MEDICAL SYSTEM =================
COMMON_MEDICAL_ADVICE = {
    "fever": (
        "Fever may be related to infection or seasonal illness. Rest well, stay hydrated, and monitor body temperature.",
        "General Physician",
        "Evaluation of infection recommended"
    ),
    "headache": (
        "Headache may occur due to stress, dehydration, or lack of sleep.",
        "General Physician",
        "Basic medical assessment"
    ),
    "stomach": (
        "Stomach discomfort may be related to indigestion or food-related infection.",
        "Gastroenterologist",
        "Digestive system evaluation"
    ),
    "cough": (
        "Cough may be related to cold, throat irritation, or respiratory infection.",
        "General Physician",
        "Respiratory assessment"
    ),
}

# ================= LOCATION =================
def get_coordinates(city):
    try:
        res = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": city, "format": "json", "limit": 1},
            headers={"User-Agent": "medassist-app"},
            timeout=10
        )
        data = res.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except:
        pass
    return 20.5937, 78.9629

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

def get_nearby_hospitals(lat, lon):
    hospitals = []
    query = f"""
    [out:json];
    (
      node["amenity"="hospital"](around:30000,{lat},{lon});
      node["amenity"="clinic"](around:30000,{lat},{lon});
    );
    out;
    """
    try:
        res = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=query,
            timeout=15
        )
        data = res.json()
        for item in data.get("elements", []):
            name = item.get("tags", {}).get("name")
            if name and item.get("lat") and item.get("lon"):
                hospitals.append({
                    "name": name,
                    "distance": calculate_distance(lat, lon, item["lat"], item["lon"]),
                    "map": f"https://www.google.com/maps?q={item['lat']},{item['lon']}"
                })
    except:
        pass
    return hospitals[:5]

# ================= GROK SAFE CALL =================
def ask_grok(prompt):
    if not GROK_API_KEY:
        return ""
    try:
        res = requests.post(
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
        data = res.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except:
        return ""

# ================= ROUTES =================
@app.route("/", methods=["GET"])
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

Patient symptoms:
{symptoms}

Reply ONLY in {lang}.
Do NOT diagnose disease.
Do NOT prescribe medicine or dosage.

Explain briefly:
- possible cause (use 'may be related to')
- basic home care
- when to see a doctor

End strictly with:

Doctor: <specialist>
Reason: <short reason>
"""

    ai_text = ""

    # ===== GEMINI MULTI-KEY =====
    for key in GEMINI_KEYS:
        if not key:
            continue
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            ai_text = (getattr(response, "text", "") or "").strip()
            if ai_text:
                break
        except:
            continue

    # ===== GROK FALLBACK =====
    if not ai_text:
        ai_text = ask_grok(prompt)

    # ===== LOCAL FALLBACK =====
    if not ai_text:
        s = symptoms.lower()
        for key in COMMON_MEDICAL_ADVICE:
            if key in s:
                health, doctor, reason = COMMON_MEDICAL_ADVICE[key]
                break
        else:
            health = (
                "Based on your symptoms, general medical guidance is advised. "
                "Please rest, stay hydrated, and monitor your condition carefully."
            )

    # ===== PARSE AI =====
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
    health = re.sub(r'\s+', ' ', health)

    lat, lon = get_coordinates(city)
    hospitals = get_nearby_hospitals(lat, lon)

    return render_template(
        "result.html",
        health=health.strip(),
        doctor=doctor,
        reason=reason,
        hospitals=hospitals
    )

if __name__ == "__main__":
    app.run(debug=True)
