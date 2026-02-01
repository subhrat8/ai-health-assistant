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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROK_API_KEY = os.getenv("GROK_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

# ================= LANGUAGE =================
def language_name(code):
    return {
        "en-US": "English",
        "hi-IN": "Hindi",
        "te-IN": "Telugu",
        "ta-IN": "Tamil"
    }.get(code, "English")


# ================= LOCAL MEDICAL FALLBACK =================
COMMON_MEDICAL_ADVICE = {
    "fever": (
        "Fever may be related to infection or seasonal illness. Rest well, stay hydrated, and monitor body temperature.",
        "General Physician",
        "Evaluation of infection recommended"
    ),
    "headache": (
        "Headache may occur due to stress, dehydration, eye strain, or lack of sleep.",
        "General Physician",
        "Basic medical assessment"
    ),
    "stomach": (
        "Stomach pain may be related to indigestion, acidity, or food-related infection.",
        "Gastroenterologist",
        "Digestive system evaluation"
    ),
    "cough": (
        "Cough is commonly linked to cold, throat irritation, or respiratory infection.",
        "General Physician",
        "Respiratory assessment"
    ),
    "pain": (
        "Body pain may occur due to fatigue, viral illness, or muscle strain.",
        "General Physician",
        "Physical examination recommended"
    ),
}


# ================= LOCATION =================
def get_coordinates(city):
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "medassist-app"}

    try:
        res = requests.get(
            url,
            params={"q": city, "format": "json", "limit": 1},
            headers=headers,
            timeout=10
        )

        data = res.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"]), data[0]["display_name"]
    except:
        pass

    return 20.5937, 78.9629, "India (approximate location)"


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


# ================= GROK =================
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
Do NOT diagnose.
Do NOT prescribe medicines or dosage.

Explain briefly:
- possible cause (may be related to)
- basic home care
- when to see a doctor

End strictly with:

Doctor: <specialist>
Reason: <short reason>
"""

    # ===== TRY GEMINI =====
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        ai_text = response.text.strip()

    # ===== TRY GROK =====
    except:
        try:
            ai_text = ask_grok(prompt)
        except:
            ai_text = ""

    # ===== FALLBACK =====
    if not ai_text:
        symptoms_lower = symptoms.lower()
        for key in COMMON_MEDICAL_ADVICE
