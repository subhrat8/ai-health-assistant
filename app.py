@app.route("/analyze", methods=["POST"])
def analyze():

    city = request.form.get("city")
    symptoms = request.form.get("symptoms")
    language = request.form.get("language", "en-US")

    lang = language_name(language)

    ai_text = ""

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
Do NOT refuse.
Do NOT say you are not a doctor.

Explain briefly:
- possible cause
- basic home care
- when to see a doctor

At the end strictly write exactly in this format:

Doctor: <specialist>
Reason: <short reason>
"""

        response = model.generate_content(prompt)

        # ✅ STRONG RESPONSE CHECK
        if (
            response
            and hasattr(response, "candidates")
            and response.candidates
            and response.candidates[0].content.parts
        ):
            ai_text = response.candidates[0].content.parts[0].text.strip()
        else:
            raise ValueError("Gemini returned empty content")

    except Exception as e:
        print("Gemini error:", e)

        ai_text = (
            "Based on the symptoms, basic medical guidance is advised. "
            "Please take adequate rest, drink fluids, and monitor your condition. "
            "If symptoms persist or worsen, seek medical attention.\n\n"
            "Doctor: General Physician\n"
            "Reason: Initial evaluation recommended."
        )

    # ---------------- PARSING ----------------
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
