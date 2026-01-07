import os
import math
import requests
from flask import Flask, render_template, request
from dotenv import load_dotenv
from google import genai

load_dotenv()

app = Flask(__name__)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ---------- LANGUAGE HELPER ----------
def language_name(lang_code):
    return {
        "en-US": "English",
        "hi-IN": "Hindi",
        "te-IN": "Telugu",
        "ta-IN": "Tamil"
    }.get(lang_code, "English")


# ---------- LOCATION ----------
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
        res = requests.post("https://overpass-api.de/api/interpreter", data=query, timeout=15)
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

    if len(hospitals) < 3:
        hospitals = [
            {"name": "Government District Hospital", "distance": "—", "map": None},
            {"name": "Community Health Centre", "distance": "—", "map": None},
            {"name": "Primary Health Clinic", "distance": "—", "map": None}
        ]

    for h in hospitals:
        if not h.get("map"):
            h["map"] = f"https://www.google.com/maps/search/{h['name']}"

    return hospitals[:5]


# ---------- MAIN ROUTE ----------
@app.route("/", methods=["GET", "POST"])
def index():
    health = ""
    doctor = ""
    reason = ""
    hospitals = []
    searched_city = ""
    searched_symptoms = ""
    location_used = ""
    selected_language = "en-US"

    if request.method == "POST":
        searched_city = request.form.get("city")
        searched_symptoms = request.form.get("symptoms")
        selected_language = request.form.get("language", "en-US")
        lang_name = language_name(selected_language)

        try:
            ai_prompt = f"""
            Patient symptoms: {searched_symptoms}

            Reply ONLY in {lang_name}.
            Do not mix languages.

            Explain briefly:
            possible cause,
            basic home care,
            when to see a doctor.

            Then give:
            Doctor: <specialist>
            Reason: <one line>
            """

            ai_resp = client.models.generate_content(
                model="models/gemini-flash-lite-latest",
                contents=ai_prompt
            )

            ai_text = ai_resp.text.replace("*", "").replace("#", "")
        except:
            ai_text = (
                f"AI service is temporarily unavailable. Please try again later.\n"
                f"Doctor: General Physician\n"
                f"Reason: Initial consultation is recommended."
            )

        for line in ai_text.splitlines():
            if line.lower().startswith("doctor:"):
                doctor = line.replace("Doctor:", "").strip()
            elif line.lower().startswith("reason:"):
                reason = line.replace("Reason:", "").strip()
            else:
                health += line + " "

        lat, lon, location_used = get_coordinates(searched_city)
        hospitals = get_nearby_hospitals(lat, lon)

    return render_template(
        "index.html",
        health=health,
        doctor=doctor,
        reason=reason,
        hospitals=hospitals,
        searched_city=searched_city,
        searched_symptoms=searched_symptoms,
        location_used=location_used,
        selected_language=selected_language
    )


if __name__ == "__main__":
    app.run(debug=True)
