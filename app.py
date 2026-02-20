import os
import math
import re
import requests
import random
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

# ================= BASIC SETUP =================
load_dotenv()
app = Flask(__name__)

API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY, transport="rest")

# ================= LOCATION =================
def get_coordinates(city):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": city, "format": "json", "limit": 1},
            headers={"User-Agent": "medassist"},
            timeout=8
        )
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except:
        pass
    return 20.5937, 78.9629  # India fallback

def distance(lat1, lon1, lat2, lon2):
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

# ================= NEARBY MEDICAL =================
def get_nearby_medical_places(lat, lon, city):
    results = []

    query = f"""
    [out:json];
    (
      node["amenity"="hospital"](around:30000,{lat},{lon});
      node["amenity"="clinic"](around:30000,{lat},{lon});
      node["amenity"="doctors"](around:30000,{lat},{lon});
    );
    out;
    """

    try:
        r = requests.post("https://overpass-api.de/api/interpreter", data=query, timeout=15)
        data = r.json()

        for e in data.get("elements", []):
            tags = e.get("tags", {})
            name = tags.get("name")
            if not name:
                continue

            address = ", ".join(filter(None, [
                tags.get("addr:street"),
                tags.get("addr:city"),
                tags.get("addr:state")
            ])) or "Address not available"

            specialty = tags.get("healthcare:speciality") or "General Care"

            if e.get("lat") and e.get("lon"):
                results.append({
                    "name": name,
                    "address": address,
                    "specialty": specialty,
                    "distance": distance(lat, lon, e["lat"], e["lon"]),
                    "map": f"https://www.google.com/maps?q={e['lat']},{e['lon']}",
                    "booking": {
                        "google": f"https://www.google.com/maps/search/{name}+{city}",
                        "practo": f"https://www.practo.com/search/doctors?query={name}+{city}",
                        "justdial": f"https://www.justdial.com/search?q={name}+{city}"
                    }
                })
    except Exception as e:
        print("Overpass error:", e)

    return sorted(results, key=lambda x: x["distance"])[:8]

# ================= AI CORE =================
def generate_ai_response(prompt):
    if not API_KEY:
        return None
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        res = model.generate_content(prompt)
        if res and res.candidates:
            return res.candidates[0].content.parts[0].text.strip()
    except Exception as e:
        print("Gemini error:", e)
    return None

# ================= ROUTES =================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    city = request.form.get("city", "")
    symptoms = request.form.get("symptoms", "")

    # 🟢 NEW: GPS SUPPORT
    lat = request.form.get("lat")
    lon = request.form.get("lon")

    if lat and lon:
        lat, lon = float(lat), float(lon)
    else:
        lat, lon = get_coordinates(city)

    prompt = f"""
Explain symptoms in simple terms:
{symptoms}

Include:
- What it may be related to
- Basic home care
- When to see a doctor

End with:
Doctor: <specialist>
Reason: <short reason>

No diagnosis. No dosage.
"""

    ai_text = generate_ai_response(prompt) or (
        "Your symptoms may be related to a common health issue. "
        "Ensure rest and hydration.\n\n"
        "Doctor: General Physician\n"
        "Reason: Initial consultation recommended"
    )

    health, doctor, reason = "", "General Physician", "Initial consultation recommended"

    for line in ai_text.splitlines():
        if line.lower().startswith("doctor:"):
            doctor = line.split(":", 1)[1].strip()
        elif line.lower().startswith("reason:"):
            reason = line.split(":", 1)[1].strip()
        else:
            health += line + " "

    medical_places = get_nearby_medical_places(lat, lon, city)

    return render_template(
        "result.html",
        health=health.strip(),
        doctor=doctor,
        reason=reason,
        medical_places=medical_places,
        hospitals=medical_places,
        searched_city=city,
        searched_symptoms=symptoms
    )

# ================= CHAT ASSISTANT =================
conversation_memory = []

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}
    msg = data.get("message", "").strip()
    health_context = data.get("health", "")

    if not msg:
        return jsonify({"reply": "Please type something 😊"})

    if msg.lower() in ["hi", "hello", "hey", "hii"]:
        return jsonify({"reply": "Hi 👋 I’m here to help. You can ask about your health result or what to do next."})

    conversation_memory.append(f"User: {msg}")
    if len(conversation_memory) > 6:
        conversation_memory.pop(0)

    prompt = f"""
You are a caring health assistant.

Health result:
{health_context}

Conversation:
{chr(10).join(conversation_memory)}

User question:
{msg}

Reply naturally. No diagnosis. No dosage.
"""

    reply = generate_ai_response(prompt)

    if reply:
        conversation_memory.append(f"Assistant: {reply}")
        return jsonify({"reply": reply})

    fallback_pool = [
        "I can explain your health result in simple terms. What would you like to understand?",
        "If you’re unsure what’s happening, I can walk you through it step by step.",
        "Would you like me to explain the possible cause or what to do next?"
    ]

    return jsonify({"reply": random.choice(fallback_pool)})

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
