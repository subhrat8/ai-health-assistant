@app.route("/analyze", methods=["POST"])
def analyze():

    city = request.form.get("city")
    symptoms = request.form.get("symptoms")
    language = request.form.get("language", "en-US")

    lang = language_name(language)

    ai_text = ""

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
Patient symptoms:
{symptoms}

Reply ONLY in {lang}.
Keep it simple and safe.

Explain briefly:
- possible cause
- basic home care
- when to see a doctor

At the end strictly write in this format:

Doctor: <specialist>
Reason: <short reason>
"""

        response = model.generate_content(prompt)

        # ✅ SAFE RESPONSE HANDLING
        if response and hasattr(response, "text") and response.text:
            ai_text = response.text
        else:
            raise ValueError("Empty Gemini response")

    except Exception as e:
        print("Gemini error:", e)

        ai_text = (
            "Based on the symptoms, basic medical guidance is advised.\n"
            "Please maintain hydration and adequate rest.\n"
            "If symptoms persist or worsen, seek medical help.\n\n"
            "Doctor: General Physician\n"
            "Reason: Initial evaluation required."
        )

    # ---------------- PARSING ----------------
    health = ""
    doctor = "General Physician"
    reason = "Initial consultation recommended."

    for line in ai_text.splitlines():
        line_clean = line.strip()

        if line_clean.lower().startswith("doctor:"):
            doctor = line_clean.split(":", 1)[1].strip()

        elif line_clean.lower().startswith("reason:"):
            reason = line_clean.split(":", 1)[1].strip()

        else:
            health += line_clean + " "

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
