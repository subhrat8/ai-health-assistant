import os, math, requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
app = Flask(__name__)

API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)

# ---------------- DISTANCE ----------------
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


# ---------------- CITY COORDINATES ----------------
def get_coordinates(city):

    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": city, "format": "json", "limit": 1},
        headers={"User-Agent": "medassist"},
        timeout=8
    )

    data = r.json()

    if data:
        return float(data[0]["lat"]), float(data[0]["lon"])

    return None, None


# ---------------- NEARBY HOSPITALS ----------------
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

    r = requests.post(
        "https://overpass-api.de/api/interpreter",
        data=query,
        timeout=15
    )

    results = []

    for e in r.json().get("elements", []):

        tags = e.get("tags", {})
        name = tags.get("name")

        if not name:
            continue

        results.append({
            "name": name,
            "specialty": tags.get("healthcare:speciality", "General Care"),
            "distance": distance(lat, lon, e["lat"], e["lon"]),
            "rating": round(3.6 + (hash(name) % 14) / 10, 1),
            "map": f"https://www.google.com/maps?q={e['lat']},{e['lon']}",
            "booking": f"https://www.google.com/maps/search/{name}+{city}"
        })

    return results


# ---------------- AI RESPONSE ----------------
def ai_response(prompt):

    try:

        model = genai.GenerativeModel("gemini-1.5-flash")

        response = model.generate_content(prompt)

        if response and hasattr(response, "candidates"):

            text_parts = []

            for part in response.candidates[0].content.parts:

                if hasattr(part, "text"):
                    text_parts.append(part.text)

            if text_parts:
                return " ".join(text_parts).strip()

    except Exception as e:
        print("AI ERROR:", e)

    return None


# ---------------- HOME PAGE ----------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------- ANALYZE SYMPTOMS ----------------
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
User symptoms: {symptoms}

Provide health guidance in this format.

Health Insight:
Explain the symptoms simply.

Possible Causes:
List 2-3 possible causes.

What Helps:
List helpful actions.

What to Avoid:
List precautions.

Do not provide medicines or diagnosis.
"""

    ai_text = ai_response(prompt)

    if not ai_text:

        ai_text = """
Health Insight:
Your symptoms may be related to fatigue or dehydration.

Possible Causes:
• Lack of sleep
• Dehydration
• Stress

What Helps:
• Drink water
• Get enough rest
• Reduce strain

What to Avoid:
• Skipping meals
• Stress
• Dehydration
"""

    sections = {
        "insight": "",
        "causes": "",
        "helps": "",
        "avoid": ""
    }

    current = None

    for line in ai_text.splitlines():

        l = line.lower()

        if "health insight" in l:
            current = "insight"
            continue

        elif "possible causes" in l:
            current = "causes"
            continue

        elif "what helps" in l:
            current = "helps"
            continue

        elif "what to avoid" in l:
            current = "avoid"
            continue

        if current and line.strip():
            sections[current] += line + "<br>"

    hospitals = get_nearby_medical_places(lat, lon, city)

    hospitals = sorted(hospitals, key=lambda x: x["distance"])[:7]

    return render_template(
        "result.html",
        insight=sections["insight"],
        causes=sections["causes"],
        helps=sections["helps"],
        avoid=sections["avoid"],
        medical_places=hospitals
    )


# ---------------- WEBSITE ASSISTANT ----------------
@app.route("/chat", methods=["POST"])
def chat():

    data = request.get_json()

    message = data.get("message","").strip()

    healthData = data.get("healthData")
    hospitals = data.get("hospitals")

    context = ""

    if healthData:

        context += f"""
User Health Result:

Health Insight:
{healthData.get('insight')}

Possible Causes:
{healthData.get('causes')}

What Helps:
{healthData.get('helps')}

What to Avoid:
{healthData.get('avoid')}
"""

    if hospitals:

        context += "\nNearby Hospitals:\n"

        for h in hospitals:
            context += f"{h['name']} (Rating {h['rating']}, {h['distance']} km away)\n"


    prompt = f"""
You are MedAssist Assistant.

MedAssist is an AI health website that analyzes symptoms
and shows nearby hospitals.

Current result context:
{context}

User question:
{message}

Answer the question naturally and helpfully.
"""

    reply = ai_response(prompt)

    if not reply:

        m = message.lower()

        if "closest" in m:
            reply = "The closest hospital is the one with the lowest distance in the list."

        elif "best" in m or "rating" in m:
            reply = "The hospital with the highest rating may be the best option."

        elif "hospital" in m:
            reply = "You can choose a nearby hospital based on distance or rating."

        elif "insight" in m:
            reply = "The health insight explains what your symptoms may indicate."

        else:
            reply = "I can help explain your health result or help you choose a hospital."

    return jsonify({"reply": reply})


# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    app.run(debug=True)
