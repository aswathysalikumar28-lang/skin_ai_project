from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer  # Added for password reset tokens
from datetime import datetime


# ================= SAFE AI IMPORT =================
from skin_detect import detect_skin_type


app = Flask(__name__)
app.secret_key = "super_secret_key"  # required for session

serializer = URLSafeTimedSerializer(app.secret_key)  # Added for password reset tokens


# ================= DATABASE =================
def get_db():
    conn = sqlite3.connect("userdb.db")
    conn.row_factory = sqlite3.Row
    return conn


# ================= CREATE USERS TABLE =================
def init_users_db():
    conn = sqlite3.connect("userdb.db")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT,
        password TEXT
    )
    """)
    conn.commit()
    conn.close()

init_users_db()


# ================= CREATE SKIN PATTERN TABLE =================
def init_skin_pattern_db():
    conn = sqlite3.connect("userdb.db")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS skin_pattern (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        date TEXT,
        pimples INTEGER,
        sleep_hours INTEGER,
        water_glasses INTEGER
    )
    """)
    conn.commit()
    conn.close()

init_skin_pattern_db()


# ================= CREATE FEEDBACK TABLE (ADDED) =================
def init_feedback_db():
    conn = sqlite3.connect("userdb.db")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        username TEXT,
        rating TEXT,
        comment TEXT
    )
    """)
    conn.commit()
    conn.close()

init_feedback_db()


# ================= HOME =================
@app.route("/")
def index():
    return render_template("index.html", user=session.get("user"), username=session.get("user"))


# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        conn.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, password)
        )
        conn.commit()
        conn.close()

        flash("Registration successful. Please log in.")  # ✅ ADD THIS LINE
        return redirect("/login")

    return render_template("register.html")


# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()

        if user and user["password"] == password:
            session["user"] = user["username"]
            session["email"] = user["email"]   # ADDED (to show email in sidebar)
            return redirect("/")
        else:
            flash("Invalid username or password")
            return render_template("login.html")

    return render_template("login.html")


# ================= FORGOT PASSWORD =================

@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        # Step 1: Check if username exists
        username = request.form.get("username").strip()
        if not username:
            flash("Please enter your username")
            return redirect("/reset_password")

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()

        if not user:
            flash("Username not found, please check again")
            return redirect("/reset_password")

        # Step 2: If new password is provided, update it
        new_password = request.form.get("password")
        if new_password:
            conn = get_db()
            conn.execute("UPDATE users SET password=? WHERE username=?", (new_password, username))
            conn.commit()
            conn.close()
            flash("Password updated successfully! Please log in.", "success")
            return redirect("/login")

        # Step 3: Show password input form for existing username
        return render_template("reset_password.html", username=username)

    # GET request: show initial form to enter username
    return render_template("reset_password.html", username=None)
# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")
    
@app.route("/")
def home():
    user = session.get("user")
    email = session.get("email")
    return render_template("index.html", user=user, email=email)    


@app.route("/profile")
def profile():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("userdb.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT username, email FROM users WHERE username = ?", (session["user"],))
    user = cursor.fetchone()

    conn.close()

    return render_template("profile.html", user=user)


@app.route("/delete_account", methods=["POST"])
def delete_account():
    username = session.get("user")

    if not username:
        flash("Login required")
        return redirect("/login")

    conn = sqlite3.connect("userdb.db")
    cursor = conn.cursor()

    # Delete related skin data first
    cursor.execute("DELETE FROM skin_pattern WHERE username = ?", (username,))

    # Delete user account
    cursor.execute("DELETE FROM users WHERE username = ?", (username,))

    conn.commit()
    conn.close()

    session.clear()
    flash("Your account has been deleted successfully.")
    return redirect("/")    


# ================= QUESTIONNAIRE AI =================
@app.route("/questionnaire", methods=["GET", "POST"])
def questionnaire():
    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":

        # ---------- SAFE SCORE FETCH ----------
        def score(name):
            return int(request.form.get(name, 0))

        # ---------- OILY FACTORS ----------
        oil = (
            score("oil_after_wash") +
            score("midday_shine") +
            score("acne_frequency") +
            score("pore_visibility")
        )

        # ---------- DRY FACTORS ----------
        # low_water_intake is inverted: more water = less dryness
        dry = (
            score("tightness") +
            score("flakiness") +
            (2 - score("low_water_intake")) +
            score("needs_heavy_moisturizer")
        )

        # ---------- SENSITIVE FACTORS ----------
        sensitive = (
            score("product_reaction") +
            score("redness") +
            score("itching")
        )

        # ---------- SKIN TYPE DECISION (CALIBRATED) ----------
        if oil >= 5 and dry <= 2:
            skin_type = "Oily Skin"
        elif dry >= 5 and oil <= 2:
            skin_type = "Dry Skin"
        elif oil >= 4 and dry >= 4:
            skin_type = "Combination Skin"
        elif oil <= 2 and dry <= 2:
            skin_type = "Normal Skin"
        else:
            skin_type = "Balanced Skin"

        if sensitive >= 4:
            skin_type += " (Sensitive)"

        # ---------- RECOMMENDATIONS ----------
        recommendations = {
            "Oily Skin": (
                "Use oil-free cleanser and avoid heavy creams.",
                "Morning: Foaming cleanser → Gel moisturizer → Sunscreen | "
                "Night: Cleanser → Niacinamide serum",
                ["Clean & Clear", "Niacinamide Serum", "Matte Sunscreen"],
                # 🌿 ADDED: Natural remedies
                [
                    "Apply aloe vera gel at night",
                    "Use multani mitti once a week",
                    "Use rose water as toner"
                ]
            ),
            "Dry Skin": (
                "Hydrate well and use rich moisturizers.",
                "Morning: Gentle cleanser → Moisturizer → Sunscreen | "
                "Night: Cleanser → Heavy cream",
                ["Cetaphil", "Nivea Cream", "Vaseline"],
                [
                    "Apply honey face mask weekly",
                    "Use coconut oil before sleep",
                    "Drink warm water regularly"
                ]
            ),
            "Combination Skin": (
                "Balance oil control and hydration.",
                "Morning: Cleanser → Gel moisturizer → Sunscreen | "
                "Night: Cleanser → Light cream",
                ["Cetaphil Oily Cleanser", "Aloe Vera Gel"],
                [
                    "Use multani mitti only on oily areas",
                    "Apply aloe vera on dry areas",
                    "Avoid harsh soaps"
                ]
            ),
            "Normal Skin": (
                "Maintain a consistent routine.",
                "Morning: Cleanser → Moisturizer → Sunscreen | "
                "Night: Cleanser → Light moisturizer",
                ["Simple Face Wash", "Pond’s Moisturizer"],
                [
                    "Use mild natural cleanser",
                    "Drink enough water daily",
                    "Avoid excessive product use"
                ]
            ),
            "Balanced Skin": (
                "Avoid over-treatment and stay hydrated.",
                "Morning: Gentle cleanser → Moisturizer → Sunscreen | "
                "Night: Cleanser → Light cream",
                ["Simple Cleanser", "Light Moisturizer"],
                [
                    "Use turmeric + yogurt mask occasionally",
                    "Maintain healthy diet",
                    "Keep skincare simple"
                ]
            )
        }

        # ✅ ADDED: Recommended Care Kit Names
        care_kits = {
    "Oily Skin": "Oil Control Kit: Cleanser + Niacinamide + Sunscreen",
    "Dry Skin": "Deep Hydration Kit: Gentle Cleanser + Rich Cream + SPF",
    "Combination Skin": "Balance Care Kit: Mild Cleanser + Gel Moisturizer + SPF",
    "Normal Skin": "Daily Glow Kit: Cleanser + Moisturizer + SPF",
    "Balanced Skin": "Maintenance Kit: Gentle Cleanser + Light Cream + SPF"
}  
        base_type = skin_type.replace(" (Sensitive)", "")
        kit_name = care_kits.get(base_type, "Basic Skincare Kit")
# ✅ Updated unpacking (only addition)
        recommendation, routine, products, natural_remedies = recommendations.get(base_type)


        

        # ---------- YOGA RECOMMENDATIONS ----------
        yoga_recommendations = {
            "Dry Skin": ["Anulom Vilom", "Child Pose"],
            "Oily Skin": ["Kapalbhati", "Surya Namaskar"],
            "Combination Skin": ["Twisting Pose", "Bridge Pose"],
            "Normal Skin": ["Meditation", "Stretching"],
            "Balanced Skin": ["Meditation", "Light Yoga"]
        }

        yoga = yoga_recommendations.get(base_type, [])

        return render_template(
        "result.html",
        skin_type=skin_type,
        recommendation=recommendation,
        routine=routine,
        yoga=yoga,
        products=products,
        natural_remedies=natural_remedies,  # ✅ ADDED
        kit_name=kit_name,
        oil_score=oil,              # optional (debug/future use)
        dry_score=dry,              # optional
        sensitive_score=sensitive   # optional
)

    return render_template("questionnaire.html")


# ================= HABITS =================
@app.route("/habits")
def habits():
    if "user" not in session:
        return redirect("/login")
    return render_template("habits.html")


# ================= HABIT RESULT =================
@app.route("/habit_result", methods=["POST"])
def habit_result():
    if "user" not in session:
        return redirect("/login")

    water = int(request.form.get("water"))
    sunscreen = int(request.form.get("sunscreen"))
    cleanser = int(request.form.get("cleanser"))
    sleep = int(request.form.get("sleep"))

    score = 0
    if water >= 6: score += 2
    if sunscreen == 1: score += 2
    if cleanser == 1: score += 2
    if sleep == 1: score += 2

    if score >= 7:
        status = "Excellent Skin Habits"
    elif score >= 4:
        status = "Average Skin Habits"
    else:
        status = "Poor Skin Habits – Improve Routine"

    return render_template("habit_result.html", score=score, status=status)


# ================= IMAGE AI SKIN DETECTION =================
@app.route("/upload_skin", methods=["GET", "POST"])
def upload_skin():
    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":
        if 'skin_image' not in request.files:
            return "No file part!", 400

        image = request.files['skin_image']
        if image.filename == "":
            return "No file selected!", 400

        filename = secure_filename(image.filename)
        os.makedirs("static/uploads", exist_ok=True)
        image_path = os.path.join("static/uploads", filename)
        image.save(image_path)

        # ------------------ NEW: Skin detection check ------------------
        import cv2
        import numpy as np

        img = cv2.imread(image_path)
        if img is None:
            return render_template("upload_skin.html", error="Invalid image!")

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower = np.array([0, 40, 60], dtype=np.uint8)
        upper = np.array([20, 150, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)
        skin_ratio = np.sum(mask > 0) / (img.shape[0] * img.shape[1])

        if skin_ratio < 0.05:  # less than 5% skin-colored pixels
            return render_template("upload_skin.html", error="This image does not appear to be skin!")

        # ------------------ Run ML prediction if it's skin ------------------
        skin_type = detect_skin_type(image_path)
        recommended_products = ["Face Wash", "Moisturizer", "Sunscreen"]

        return render_template("result.html",
                               skin_type=skin_type,
                               recommendation="AI detected skin type using Machine Learning model.",
                               routine="Follow dermatologist recommended routine.",
                               yoga=["Surya Namaskar", "Meditation"],
                               products=recommended_products)

    # GET request: show upload page
    return render_template("upload_skin.html")


# ================= AI PREDICTION FUNCTION =================
def predict_high_risk_days():
    conn = get_db()
    data = conn.execute("SELECT  pimples FROM skin_pattern").fetchall()
    conn.close()

    risky_days = []
    for row in data:
        if row["pimples"] >= 3:
            risky_days.append(row["cycle_day"])

    return list(set(risky_days))


# ===================== SKIN PATTERN ROUTES =====================

@app.route('/skin_pattern')
def skin_pattern():
    # Show the skin pattern form
    return render_template("skin_pattern.html")


@app.route('/save_skin_pattern', methods=['POST'])
def save_skin_pattern():
    username = session.get("user")
    if not username:
        flash("You must be logged in to save data.")
        return redirect("/login")

    date = request.form.get("date")
    cycle_start = request.form.get("cycle_start_date")
    cycle_end = request.form.get("cycle_end_date")
    pimples = request.form.get("pimples")
    pimple_occurrence = request.form.get("pimple_occurrence")
    sleep_hours = request.form.get("sleep_hours")
    water_glasses = request.form.get("water_glasses")

    if not all([date, cycle_start, pimples, pimple_occurrence, sleep_hours, water_glasses]):
        flash("All fields except cycle_end are required!")
        return redirect("/skin_pattern")

    # Calculate cycle day
    cycle_day = (datetime.strptime(date, "%Y-%m-%d") - datetime.strptime(cycle_start, "%Y-%m-%d")).days + 1
    if cycle_day < 1:
        cycle_day = 1

    conn = get_db()
    conn.execute("""
        INSERT INTO skin_pattern
        (username, date, cycle_start_date, cycle_end_date, cycle_day, pimples, pimple_occurrence, sleep_hours, water_glasses)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (username, date, cycle_start, cycle_end, cycle_day, pimples, pimple_occurrence, sleep_hours, water_glasses))
    conn.commit()
    conn.close()

    flash("Skin pattern data saved successfully! Go to 'View Skin Data' to see your updated records.")
    return redirect("/skin_pattern")

# ================= VIEW SAVED DATA =================
@app.route("/view_skin_data")
def view_skin_data():
    username = session.get("user")
    if not username:
        flash("Login required")
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    # Get all records for the user
    cursor.execute("""
        SELECT id, date, cycle_day, pimples, sleep_hours, water_glasses
        FROM skin_pattern
        WHERE username = ?
        ORDER BY date DESC
    """, (username,))
    rows = cursor.fetchall()

    # Convert to dict for template
    data = []
    for r in rows:
        data.append({
            "id": r[0],
            "date": r[1],
            "cycle_day": r[2],
            "pimples": int(r[3]),
            "sleep_hours": int(r[4]),
            "water_glasses": int(r[5])
        })

    # ---------------------------------
    # MONTHLY ANALYSIS (NEW LOGIC)
    # ---------------------------------
    from collections import defaultdict
    from datetime import datetime

    monthly_data = defaultdict(lambda: {"pimples": [], "sleep": [], "water": []})

    for r in rows:
        date_obj = datetime.strptime(r[1], "%Y-%m-%d")
        month_key = date_obj.strftime("%Y-%m")

        monthly_data[month_key]["pimples"].append(int(r[3]))
        monthly_data[month_key]["sleep"].append(int(r[4]))
        monthly_data[month_key]["water"].append(int(r[5]))

    sorted_months = sorted(monthly_data.keys(), reverse=True)

    improvement_message = ""

    if len(sorted_months) >= 2:
        current_month = sorted_months[0]
        previous_month = sorted_months[1]

        def avg(lst):
            return sum(lst) / len(lst) if lst else 0

        curr_pimples = avg(monthly_data[current_month]["pimples"])
        curr_sleep = avg(monthly_data[current_month]["sleep"])
        curr_water = avg(monthly_data[current_month]["water"])

        prev_pimples = avg(monthly_data[previous_month]["pimples"])
        prev_sleep = avg(monthly_data[previous_month]["sleep"])
        prev_water = avg(monthly_data[previous_month]["water"])

        messages = []

        if curr_water > prev_water:
            messages.append("Water intake improved compared to last month 👍")
        elif curr_water < prev_water:
            messages.append("Water intake reduced compared to last month ⚠")

        if curr_sleep > prev_sleep:
            messages.append("Sleep improved compared to last month 😴")
        elif curr_sleep < prev_sleep:
            messages.append("Sleep reduced compared to last month ⚠")

        if curr_pimples < prev_pimples:
            messages.append("Pimples reduced compared to last month 👍")
        elif curr_pimples > prev_pimples:
            messages.append("Pimples increased compared to last month ❗")

        if not messages:
            messages.append("No major changes compared to last month.")

        improvement_message = " | ".join(messages)

    elif len(sorted_months) == 1:
        improvement_message = "Add more monthly data to see progress comparison."

    # ---------------------------------
    # Personalized Tips (latest entry)
    # ---------------------------------
    personalized_tips = []

    if len(rows) >= 1:
        latest = rows[0]

        latest_pimples = int(latest[3])
        latest_sleep = int(latest[4])
        latest_water = int(latest[5])

        if latest_water < 5:
            personalized_tips.append("Increase water intake to at least 6–8 glasses daily.")

        if latest_sleep < 7:
            personalized_tips.append("Try to sleep at least 7–8 hours for better skin recovery.")

        if latest_pimples >= 3:
            personalized_tips.append("Consider reducing oily or sugary food intake.")

    # ---------------------------------
    # Graph Data (integrate progress_graphs)
    # ---------------------------------
    # We want ascending dates for graph
    cursor.execute("""
        SELECT date, sleep_hours, water_glasses, pimples 
        FROM skin_pattern
        WHERE username = ?
        ORDER BY date ASC
    """, (username,))
    graph_rows = cursor.fetchall()

    graph_data = {
        "dates": [r[0] for r in graph_rows],
        "sleep": [r[1] for r in graph_rows],
        "water": [r[2] for r in graph_rows],
        "pimples": [r[3] for r in graph_rows]
    }

    conn.close()
    return render_template(
        "view_skin_data.html",
        records=data,
        improvement=improvement_message,
        tips=personalized_tips,
        graph_data=graph_data  # Pass to template
    )


@app.route('/edit/<int:record_id>', methods=['GET', 'POST'])
def edit(record_id):

    username = session.get("user")
    if not username:
        flash("Login required")
        return redirect("/login")

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch existing record (only for logged in user)
    cursor.execute("""
        SELECT * FROM skin_pattern
        WHERE id = ? AND username = ?
    """, (record_id, username))

    record = cursor.fetchone()

    if not record:
        conn.close()
        return "Record not found"

    if request.method == 'POST':
        date = request.form['date']
        pimples = request.form['pimples']
        cycle_day = request.form['cycle_day']
        sleep = request.form['sleep']
        water = request.form['water']

        cursor.execute("""
            UPDATE skin_pattern
            SET date=?, pimples=?, cycle_day=?, sleep_hours=?, water_glasses=?
            WHERE id=? AND username=?
        """, (date, pimples, cycle_day, sleep, water, record_id, username))

        conn.commit()
        conn.close()

        return redirect('/view_skin_data')

    conn.close()
    return render_template('edit.html', record=record)

@app.route('/delete/<int:record_id>')
def delete(record_id):
    username = session.get("user")
    if not username:
        flash("Login required")
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    # Delete only if record belongs to logged in user
    cursor.execute("""
        DELETE FROM skin_pattern
        WHERE id = ? AND username = ?
    """, (record_id, username))

    conn.commit()
    conn.close()

    return redirect('/view_skin_data') 


@app.route("/dashboard")
def dashboard():
    conn = sqlite3.connect("userdb.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get average values from skin_pattern table
    cursor.execute("""
        SELECT 
            AVG(sleep_hours) AS avg_sleep,
            AVG(water_glasses) AS avg_water,
            AVG(pimples) AS avg_pimples
        FROM skin_pattern
    """)
    
    data = cursor.fetchone()

    # Get total number of entries
    cursor.execute("SELECT COUNT(*) AS total_entries FROM skin_pattern")
    total = cursor.fetchone()

    conn.close()

    # If table is empty, avoid None errors
    avg_sleep = round(data["avg_sleep"], 2) if data["avg_sleep"] else 0
    avg_water = round(data["avg_water"], 2) if data["avg_water"] else 0
    avg_pimples = round(data["avg_pimples"], 2) if data["avg_pimples"] else 0
    total_entries = total["total_entries"] if total["total_entries"] else 0

    return render_template(
        "dashboard.html",
        avg_sleep=avg_sleep,
        avg_water=avg_water,
        avg_pimples=avg_pimples,
        total_entries=total_entries
    )

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ================= FEEDBACK =================
@app.route("/feedback")
def feedback():
    if "user" not in session:
        return redirect("/login")
    return render_template("feedback.html")


# ================= SAVE FEEDBACK =================
@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    product = request.form["product"]
    rating = request.form["rating"]
    comment = request.form["comment"]

    # save data logic here

    return render_template(
        "feedback.html",
        success=True
    )


# ================= HOME LINKS API =================
@app.route("/home_links")
def home_links():
    if "user" not in session:
        return redirect("/login")

    links = {
        "Skin Pattern Tracker": "/skin_pattern",
        "Upload Skin Image": "/upload_skin",
        "Questionnaire AI": "/questionnaire",
        "Daily Habits Tracker": "/habits",
        "View Skin Data": "/view_skin_data",
        "Feedback": "/feedback",
        "Logout": "/logout"
    }

    return links


# ================= 404 ERROR PAGE =================
@app.errorhandler(404)
def page_not_found(e):
    return "<h2>404 - Page Not Found</h2><p>The page you requested does not exist.</p>", 404


# ================= RUN APP =================
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")