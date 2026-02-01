import os
import math
import requests
from flask import Flask, render_template, request
from dotenv import load_dotenv
import google.generativeai as genai

# ---------------- LOAD ENV ----------------
load_dotenv()

# ---------------- FLASK APP ----------------
app = Flask(__name__)

# ---------------- GEMINI CONFIG ----------------
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ---------------- LANGUAGE ----------------
def language_name(code):
    return {
        "en-US": "English",
        "hi-IN": "Hindi",
        "te-IN": "Telugu",
        "ta-IN": "Tamil"
    }.get(code, "English")


# ---------------- LOCATION ----------------
def get_coordinates(city):
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "ai-health-app"}

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


# ---------------- HOME PAGE ----------------
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


# ---------------- ANALYZE ----------------
@app.route("/analyze", methods=["POST"])
def analyze():

    city = request.form.get("city")
    symptoms = request.form.get("symptoms")
    language = request.form.get("language", "en-US")

    lang = language_name(language)

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

Explain briefly:
- possible cause
- basic home care
- when to see a doctor

At the end strictly write:

Doctor: <specialist>
Reason: <short reason>
"""

        response = model.generate_content(prompt)
        ai_text = response.text.strip()

    except Exception as e:
        print("Gemini error:", e)

        ai_text = (
            "Based on the symptoms, basic medical guidance is advised. "
            "Please rest, stay hydrated, and monitor your condition.\n\n"
            "Doctor: General Physician\n"
            "Reason: Initial evaluation recommended."
        )

    # ---------------- PARSE ----------------
    health = ""
    doctor = "General Physician"
    reason = "Initial consultation recommended."

    for line in ai_text.splitlines():
        line = line.strip()

        if line.lower().startswith("doctor:"):
            doctor = line.split(":", 1)[1].strip()

        elif line.lower().startswith("reason:"):
            reason = line.split(":", 1)[1].strip()

        else:
            health += line + " "

    # ---------------- LOCATION ----------------
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


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
