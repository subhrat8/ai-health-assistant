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
GEMINI_API_KEY_1 = os.getenv("GEMINI_API_KEY")
GEMINI_API_KEY_2 = os.getenv("GEMINI_API_KEY_2")
GROK_API_KEY = os.getenv("GROK_API_KEY")

# ================= LANGUAGE =================
def language_name(code):
    return {
        "en-US": "English",
        "hi-IN": "Hindi",
        "te-IN": "Telugu",
        "ta-IN": "Tamil"
    }.get(code, "English")

# ================= HOSPITAL RATING =================
def hospital_rating(name):
    return round(3.5 + (sum(ord(c) for c in name) % 15) / 10, 1)

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
                    "rating": hospital_rating(name),
                    "map": f"https://www.google.com/maps?q={item['lat']},{item['lon']}"
                })
    except:
        pass

    return hospitals[:5]

# ================= AI HELPERS =================
def ask_gemini(prompt, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text.strip()

def ask_grok(prompt):
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "grok-1",
        "messages": [{"role": "user", "content": prompt}]
    }
    res = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=25
    )
    data = res.json()
    return data["choices"][0]["message"]["content"]

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

Rules:
- Do NOT diagnose disease
- Do NOT give medicine dosage
- Use phrases like "may be related to"

Explain briefly:
- possible cause
- basic home care
- when to see a doctor

End strictly with:

Doctor: <specialist>
Reason: <short reason>
"""

    ai_text = ""

    # ===== GEMINI KEY 1 =====
    try:
        ai_text = ask_gemini(prompt, GEMINI_API_KEY_1)

    # ===== GEMINI KEY 2 =====
    except:
        try:
            ai_text = ask_gemini(prompt, GEMINI_API_KEY_2)

        # ===== GROK =====
        except:
            try:
                ai_text = ask_grok(prompt)
            except:
                ai_text = ""

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

    if not health:
        health = (
            "Based on your symptoms, general medical guidance is advised. "
            "Please rest, stay hydrated, and monitor your condition."
        )

    # Fix spacing
    health = re.sub(r'([a-z])([A-Z])', r'\1 \2', health)
    health = re.sub(r'\s+', ' ', health)

    lat, lon = get_coordinates(city)
    hospital_list = get_nearby_hospitals(lat, lon)

    return render_template(
        "result.html",
        health=health.strip(),
        doctor=doctor,
        reason=reason,
        hospitals=hospital_list,
        searched_city=city,
        searched_symptoms=symptoms
    )

if __name__ == "__main__":
    app.run(debug=True)
