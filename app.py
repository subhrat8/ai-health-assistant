# helpers above
# -----------------------

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    searched_city = request.form.get("city")
    searched_symptoms = request.form.get("symptoms")
    selected_language = request.form.get("language", "en-US")

    lang_name = language_name(selected_language)

    try:
        ai_prompt = f"""
        Patient symptoms: {searched_symptoms}

        Reply ONLY in {lang_name}.
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
            "AI service unavailable.\n"
            "Doctor: General Physician\n"
            "Reason: Initial consultation recommended."
        )

    health = ""
    doctor = ""
    reason = ""

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
        "result.html",
        health=health,
        doctor=doctor,
        reason=reason,
        hospitals=hospitals,
        searched_city=searched_city,
        searched_symptoms=searched_symptoms,
        location_used=location_used,
        selected_language=selected_language
    )
