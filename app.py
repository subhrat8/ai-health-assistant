import os
import math
import re
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

# ================= BASIC SETUP =================
load_dotenv()
app = Flask(__name__)

API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini once (Render-safe)
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
        r = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=query,
            timeout=15
        )
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

            specialty = (
                tags.get("healthcare:speciality")
                or tags.get("medical_specialty")
                or "General Care"
            )

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
        response = model.generate_content(prompt)
        if response and response.candidates:
            return response.candidates[0].content.parts[0].text.strip()
    except Exception as e:
        print("Gemini error:", e)
        return None
    return None

# ================= ROUTES =================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        city = request.form.get("city", "")
        symptoms = request.form.get("symptoms", "")

        prompt = f"""
You are a medical assistant.

Symptoms:
{symptoms}

Explain in simple language:
- Possible cause (general only)
- Basic home care
- When to see a doctor

End with:
Doctor: <specialist>
Reason: <short reason>

Rules:
- No diagnosis
- No dosage
"""

        ai_text = generate_ai_response(prompt)

        if not ai_text:
            ai_text = (
                "Your symptoms may be related to a common health issue. "
                "Ensure rest, hydration, and basic care. "
                "If symptoms worsen or persist, consult a doctor.\n\n"
                "Doctor: General Physician\n"
                "Reason: Initial consultation recommended"
            )

        health = ""
        doctor = "General Physician"
        reason = "Initial consultation recommended"

        for line in ai_text.splitlines():
            line = line.strip()
            if line.lower().startswith("doctor:"):
                doctor = line.split(":", 1)[1].strip()
            elif line.lower().startswith("reason:"):
                reason = line.split(":", 1)[1].strip()
            else:
                health += line + " "

        health = re.sub(r"\s+", " ", health).strip()

        lat, lon = get_coordinates(city)
        medical_places = get_nearby_medical_places(lat, lon, city)

        return render_template(
            "result.html",
            health=health,
            doctor=doctor,
            reason=reason,
            medical_places=medical_places,
            hospitals=medical_places,      # backward compatibility
            searched_city=city,
            searched_symptoms=symptoms
        )

    except Exception as e:
        print("Analyze error:", e)
        return "Something went wrong. Please try again."

# ================= HUMAN-LIKE CHAT ASSISTANT =================
conversation_memory = []

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json or {}
        user_msg = data.get("message", "").strip()

        if not user_msg:
            return jsonify({"reply": "Please ask something 😊"})

        # Keep last 6 messages only
        conversation_memory.append(f"User: {user_msg}")
        if len(conversation_memory) > 6:
            conversation_memory.pop(0)

        context = "\n".join(conversation_memory)

        prompt = f"""
You are MedAssist Help Assistant.

Speak like a calm, friendly human.
Be supportive and natural.
Do not repeat generic sentences.
Do not diagnose diseases.
Do not give dosage.

Conversation so far:
{context}

Respond clearly and helpfully.
"""

        reply = generate_ai_response(prompt)

        if reply:
            conversation_memory.append(f"Assistant: {reply}")
            return jsonify({"reply": reply})

        # Smart fallback (never robotic)
        fallback = f"I understand you're asking about '{user_msg}'. Could you explain a bit more so I can help you better?"

        return jsonify({"reply": fallback})

    except Exception as e:
        print("Chat error:", e)
        return jsonify({"reply": "I'm having trouble responding right now. Please try again."})

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
