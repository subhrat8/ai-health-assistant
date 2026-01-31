import os
import math
import requests
from flask import Flask, render_template, request
from dotenv import load_dotenv

# ---------------- LOAD ENV ----------------
load_dotenv()

app = Flask(__name__)

HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

# ---------------- LANGUAGE ----------------
def language_name(code):
    return {
        "en-US": "en",
        "hi-IN": "hi",
        "te-IN": "te",
        "ta-IN": "ta"
    }.get(code, "en")


# ---------------- TRANSLATION ----------------
def translate(text, source, target):
    if source == target:
        return text

    url = "https://libretranslate.de/translate"

    payload = {
        "q": text,
        "source": source,
        "target": target,
        "format": "text"
    }

    try:
        res = requests.post(url, data=payload, timeout=10)
        return res.json()["translatedText"]
    except:
        return text


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

    return 20.5937, 78.9629, "India"


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

    return hospitals[:5]


# ---------------- ROUTES ----------------
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():

    city = request.form.get("city")
    symptoms = request.form.get("symptoms")
    language = request.form.get("language", "en-US")

    user_lang = language_name(language)

    symptoms_en = translate(symptoms, user_lang, "en")

    prompt = f"""
    Patient symptoms: {symptoms_en}

    Explain briefly:
    possible cause,
    basic home care,
    when to see a doctor.

    Then give:
    Doctor: <specialist>
    Reason: <one line>
    """

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}"
    }

    payload = {
        "inputs": prompt
    }

    try:
        res = requests.post(
            "https://api-inference.huggingface.co/models/google/flan-t5-large?wait_for_model=true",
            headers=headers,
            json=payload,
            timeout=120
        )

        data = res.json()

        if isinstance(data, list):
            output = data[0].get("generated_text", "")
        else:
            output = "Unable to generate response at the moment."

    except:
        output = "Unable to generate response at the moment."

    output_final = translate(output, "en", user_lang)

    health = ""
    doctor = ""
    reason = ""

    for line in output_final.splitlines():
        if "doctor" in line.lower():
            doctor = line.split(":")[-1].strip()
        elif "reason" in line.lower():
            reason = line.split(":")[-1].strip()
        else:
            health += line + " "

    lat, lon, location_used = get_coordinates(city)
    hospitals = get_nearby_hospitals(lat, lon)

    return render_template(
        "result.html",
        health=health,
        doctor=doctor,
        reason=reason,
        hospitals=hospitals,
        searched_city=city,
        searched_symptoms=symptoms
    )


if __name__ == "__main__":
    app.run(debug=True)
