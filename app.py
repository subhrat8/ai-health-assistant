import os, math, requests, random
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
app = Flask(__name__)

API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY, transport="rest")

# ---------- DISTANCE ----------
def distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat/2)**2 +
        math.cos(math.radians(lat1)) *
        math.cos(math.radians(lat2)) *
        math.sin(dlon/2)**2
    )
    return round(2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a)), 2)

# ---------- GEOCODE ----------
def get_coordinates(city):
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": city, "format": "json", "limit": 1},
        headers={"User-Agent": "medassist"},
        timeout=8
    )
    d = r.json()
    if d:
        return float(d[0]["lat"]), float(d[0]["lon"])
    return None, None

# ---------- HOSPITAL SEARCH ----------
def get_nearby_medical_places(lat, lon, city):
    query = f"""
    [out:json];
    (
      node["amenity"="hospital"](around:30000,{lat},{lon});
      node["amenity"="clinic"](around:30000,{lat},{lon});
      node["amenity"="doctors"](around:30000,{lat},{lon});
    );
    out;
    """
    results = []
    r = requests.post("https://overpass-api.de/api/interpreter", data=query, timeout=15)

    for e in r.json().get("elements", []):
        tags = e.get("tags", {})
        name = tags.get("name")
        if not name:
            continue

        results.append({
            "name": name,
            "specialty": tags.get("healthcare:speciality", "General Care"),
            "distance": distance(lat, lon, e["lat"], e["lon"]),
            "rating": round(3.5 + (hash(name) % 15) / 10, 1),
            "map": f"https://www.google.com/maps?q={e['lat']},{e['lon']}",
            "booking": {
                "google": f"https://www.google.com/maps/search/{name}+{city}"
            }
        })

    return results

# ---------- AI ----------
def ai_response(prompt):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        res = model.generate_content(prompt)
        return res.candidates[0].content.parts[0].text.strip()
    except:
        return None

# ---------- ROUTES ----------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    city = request.form.get("city")
    symptoms = request.form.get("symptoms")
    lat = request.form.get("lat")
    lon = request.form.get("lon")

    if lat and lon:
        lat, lon = float(lat), float(lon)
    else:
        lat, lon = get_coordinates(city)

    prompt = f"""
Explain symptoms simply:
{symptoms}

Give general precautions.
"""
    health = ai_response(prompt) or "General health guidance. Take rest and stay hydrated."

    medical_places = get_nearby_medical_places(lat, lon, city)

    return render_template(
        "result.html",
        health=health,
        medical_places=medical_places
    )

@app.route("/chat", methods=["POST"])
def chat():
    msg = request.json.get("message", "")
    reply = ai_response(msg)
    return jsonify({"reply": reply or "How can I help you further?"})

if __name__ == "__main__":
    app.run(debug=True)
