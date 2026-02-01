import os
import math
import requests
from flask import Flask, render_template, request
from dotenv import load_dotenv
import google.generativeai as genai

# ================= LOAD ENV =================
load_dotenv()

app = Flask(__name__)

# ================= GEMINI CONFIG =================
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

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
    "fever": {
        "text": "Fever may be related to infection or seasonal illness. Rest well, drink fluids, and monitor temperature regularly.",
        "doctor": "General Physician",
        "reason": "Evaluation of infection recommended"
    },
    "headache": {
        "text": "Headache may be caused by stress, dehydration, eye strain, or lack of sleep.",
        "doctor": "General Physician",
        "reason": "Basic medical assessment"
    },
    "stomach": {
        "text": "Stomach pain may occur due to indigestion, acidity, or food-related infection.",
        "doctor": "Gastroenterologist",
        "reason": "Digestive system evaluation"
    },
    "cough": {
        "text": "Cough is commonly related to cold, throat irritation, or respiratory infection.",
        "doctor": "General Physician",
        "reason": "Respiratory assessment"
    },
    "pain": {
        "text": "Body pain may occur due to fatigue, viral infection, or muscle strain.",
        "doctor": "General Physician",
        "reason": "Physical examination recommended"
    }
}


# ================= LOCATION =================
def get_coordinates(city):
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "medassist-app"}

    try:
        params = {"q": city, "format": "json", "limit": 1}
        res = requests.get(url, params=params, headers=headers, timeout=10)
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

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)


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
            h_lat = item.get("lat")
            h_lon = item.get("lon")

            if name and h_lat and h_lon:
                hospitals.append({
                    "name": name,
                    "distance": calculate_distance(lat, lon, h_lat, h_lon),
                    "map": f"https://www.google.com/maps?q={h_lat},{h_lon}"
                })

    except:
        pass

    return hospitals[:5]


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

    # ================= GEMINI AI =================
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={
                "temperature": 0.4,
                "max_output_tokens": 300
            }
        )

        prompt = f"""
You are a medical information assistant.

Patient symptoms:
{symptoms}

Reply ONLY in {lang}.

Give general medical information only.
Do NOT give dosage.
Do NOT prescribe medicines.
Do NOT confirm disease.

Explain briefly:
- possible cause (use words like may be related to)
- basic home care
- when to see a doctor

End strictly with:

Doctor: <specialist>
Reason: <short reason>
"""

        response = model.generate_content(prompt)
        ai_text = response.text.strip()

        for line in ai_text.splitlines():
            line = line.strip()

            if line.lower().startswith("doctor:"):
                doctor = line.split(":", 1)[1].strip()

            elif line.lower().startswith("reason:"):
                reason = line.split(":", 1)[1].strip()

            else:
                health += line + " "

    # ================= FALLBACK SYSTEM =================
    except Exception as e:
        print("Gemini error:", e)

        symptoms_lower = symptoms.lower()
        matched = False

        for key in COMMON_MEDICAL_ADVICE:
            if key in symptoms_lower:
                advice = COMMON_MEDICAL_ADVICE[key]
                health = advice["text"]
                doctor = advice["doctor"]
                reason = advice["reason"]
                matched = True
                break

        if not matched:
            health = (
                "Based on your symptoms, general medical guidance is advised. "
                "Please rest, stay hydrated, and monitor your condition carefully."
            )

    # ================= LOCATION =================
    lat, lon, location_used = get_coordinates(city)
    hospitals = get_nearby_hospitals(lat, lon)

    return render_template(
        "result.html",
        health=health.strip(),
        doctor=doctor,
        reason=reason,
        hospitals=hospitals,
        searched_city=city,
        searched_symptoms=symptoms
    )


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
