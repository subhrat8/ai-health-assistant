import os
import math
import re
import requests
from flask import Flask, render_template, request
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
app = Flask(__name__)

# ================= API KEYS =================
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
GROK_API_KEY = os.getenv("GROK_API_KEY")

# ================= LANGUAGE =================
def language_name(code):
    return {
        "en-US": "English",
        "hi-IN": "Hindi",
        "te-IN": "Telugu",
        "ta-IN": "Tamil"
    }.get(code, "English")

# ================= RATINGS =================
def rating(name):
    return round(3.5 + (sum(ord(c) for c in name) % 15) / 10, 1)

# ================= LOCATION =================
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
    return 20.5937, 78.9629

def distance(a,b,c,d):
    R = 6371
    dlat = math.radians(c-a)
    dlon = math.radians(d-b)
    x = math.sin(dlat/2)**2 + math.cos(math.radians(a))*math.cos(math.radians(c))*math.sin(dlon/2)**2
    return round(2*R*math.atan2(math.sqrt(x),math.sqrt(1-x)),2)

def hospitals(lat, lon):
    data = []
    query = f"""
    [out:json];
    (node["amenity"="hospital"](around:30000,{lat},{lon});
     node["amenity"="clinic"](around:30000,{lat},{lon}););
    out;
    """
    try:
        r = requests.post("https://overpass-api.de/api/interpreter", data=query, timeout=15)
        for i in r.json().get("elements",[]):
            if "name" in i.get("tags",{}):
                data.append({
                    "name": i["tags"]["name"],
                    "distance": distance(lat,lon,i["lat"],i["lon"]),
                    "rating": rating(i["tags"]["name"]),
                    "map": f"https://www.google.com/maps?q={i['lat']},{i['lon']}"
                })
    except:
        pass
    return data[:5]

# ================= ROUTES =================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    city = request.form.get("city","")
    symptoms = request.form.get("symptoms","")
    lang = language_name(request.form.get("language","en-US"))

    prompt = f"""
Patient symptoms:
{symptoms}

Reply ONLY in {lang}.
Do NOT diagnose.
Do NOT give dosage.

Explain:
- possible cause (may be related to)
- basic home care
- when to see a doctor

End with:
Doctor: <specialist>
Reason: <short reason>
"""

    health = ""
    doctor = "General Physician"
    reason = "Initial consultation recommended"

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        text = model.generate_content(prompt).text
    except:
        text = ""

    for line in text.splitlines():
        if line.lower().startswith("doctor:"):
            doctor = line.split(":",1)[1].strip()
        elif line.lower().startswith("reason:"):
            reason = line.split(":",1)[1].strip()
        else:
            health += line + " "

    health = re.sub(r'([a-z])([A-Z])', r'\1 \2', health)

    lat, lon = get_coordinates(city)
    hosp = hospitals(lat, lon)

    return render_template(
        "result.html",
        health=health,
        doctor=doctor,
        reason=reason,
        hospitals=hosp,
        symptoms=symptoms,
        city=city
    )

if __name__ == "__main__":
    app.run(debug=True)
