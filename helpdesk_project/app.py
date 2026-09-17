import datetime
import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from database import init_db, get_db_connection
from chatbot import get_chatbot_response

app = Flask(__name__)
app.secret_key = "smart_college_assistant_secret_key"

# Upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'py', 'zip', 'jpg', 'jpeg', 'png'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize database
try:
    init_db()
    print("Database initialized successfully.")
except Exception as e:
    print("Database initialization error:", e)


# ---------------- HOME & ALIASES ----------------
@app.route("/")
@app.route("/index")
@app.route("/home")
def home():
    if "username" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()

        if not username or not password:
            return render_template(
                "login.html",
                error="Please enter both username and password."
            )

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password)
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["name"] = user["name"]
            session["department"] = user["department"]
            session["semester"] = user["semester"]
            return redirect(url_for("dashboard"))
        else:
            return render_template(
                "login.html",
                error="Invalid username or password. Please try again."
            )

    if "username" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")


# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        department = (request.form.get("department") or "Computer Science").strip()
        semester = (request.form.get("semester") or "Sem 5").strip()

        if not (name and username and password):
            return render_template("register.html", error="Please fill all required fields.")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return render_template("register.html", error="Username is already taken. Please choose another.")

        cursor.execute(
            "INSERT INTO users (username, password, role, name, department, semester) VALUES (?, ?, 'student', ?, ?, ?)",
            (username, password, name, department, semester)
        )
        cursor.execute(
            "SELECT DISTINCT subject FROM timetable WHERE semester = ? OR semester = 'Sem 5'",
            (semester,)
        )
        attendance_subjects = cursor.fetchall()
        cursor.executemany(
            "INSERT INTO attendance (username, subject, total_classes, attended_classes) VALUES (?, ?, 0, 0)",
            [(username, row['subject']) for row in attendance_subjects]
        )
        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


def calculate_free_periods(today_classes):
    """Calculate free periods / break intervals between today's scheduled classes."""
    if not today_classes:
        return []

    parsed = []
    for row in today_classes:
        slot = str(row["time_slot"]).strip()
        parts = [p.strip() for p in slot.replace("to", "-").split("-")]
        if len(parts) == 2:
            def parse_time_str(val):
                val = val.strip().upper()
                for fmt in ("%I:%M %p", "%I %p", "%H:%M", "%I:%M"):
                    try:
                        return datetime.datetime.strptime(val, fmt).time()
                    except ValueError:
                        pass
                return None

            t1 = parse_time_str(parts[0])
            t2 = parse_time_str(parts[1])
            if t1 and t2:
                parsed.append((t1, t2, row["subject"]))

    if len(parsed) < 2:
        return []

    parsed.sort(key=lambda item: (item[0].hour, item[0].minute))
    free = []
    for i in range(len(parsed) - 1):
        end_curr = parsed[i][1]
        start_next = parsed[i + 1][0]
        end_mins = end_curr.hour * 60 + end_curr.minute
        start_mins = start_next.hour * 60 + start_next.minute
        gap = start_mins - end_mins
        if gap >= 10:
            start_str = datetime.time(end_curr.hour, end_curr.minute).strftime("%I:%M %p").lstrip("0")
            end_str = datetime.time(start_next.hour, start_next.minute).strftime("%I:%M %p").lstrip("0")
            free.append(f"{start_str} - {end_str} ({gap} min break between {parsed[i][2]} & {parsed[i+1][2]})")

    return free


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure user session profile details are loaded
    if not session.get("name") or not session.get("role"):
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        u = cursor.fetchone()
        if u:
            session["role"] = u["role"]
            session["name"] = u["name"]
            session["department"] = u["department"]
            session["semester"] = u["semester"]
        else:
            session["role"] = "admin" if username == "admin" else "student"
            session["name"] = username.capitalize()
            session["department"] = "Computer Science"
            session["semester"] = "Sem 5"

    role = session.get("role", "student")

    if role == "admin" or username == "admin":
        cursor.execute("SELECT * FROM users WHERE role = 'student'")
        students = cursor.fetchall()

        cursor.execute("SELECT * FROM faqs ORDER BY id DESC")
        faqs = cursor.fetchall()

        cursor.execute("SELECT * FROM complaints ORDER BY id DESC")
        complaints = cursor.fetchall()

        cursor.execute("SELECT * FROM queries ORDER BY id DESC")
        queries = cursor.fetchall()

        cursor.execute("SELECT * FROM announcements ORDER BY id DESC")
        announcements = cursor.fetchall()

        cursor.execute("SELECT * FROM timetable ORDER BY id ASC")
        timetable = cursor.fetchall()

        cursor.execute("""
            SELECT attendance.*, users.name
            FROM attendance
            LEFT JOIN users ON users.username = attendance.username
            ORDER BY attendance.username, attendance.subject
        """)
        attendance_records = cursor.fetchall()

        conn.close()
        return render_template(
            "admin_dashboard.html",
            username=username,
            students=students,
            faqs=faqs,
            complaints=complaints,
            queries=queries,
            announcements=announcements,
            timetable=timetable,
            attendance_records=attendance_records
        )
    else:
        user_sem = session.get("semester", "Sem 5")

        cursor.execute("SELECT * FROM timetable WHERE semester = ? OR semester = 'Sem 5' ORDER BY id ASC", (user_sem,))
        timetable = cursor.fetchall()
        if not timetable:
            cursor.execute("SELECT * FROM timetable ORDER BY id ASC")
            timetable = cursor.fetchall()

        today_name = datetime.datetime.now().strftime("%A")
        today_classes = [row for row in timetable if row["day"].strip().lower() == today_name.lower()]

        cursor.execute("SELECT * FROM timetable WHERE is_next = 1")
        upcoming_classes = cursor.fetchall()
        if not upcoming_classes and today_classes:
            upcoming_classes = today_classes[:3]
        elif not upcoming_classes and timetable:
            upcoming_classes = timetable[:3]

        free_periods = calculate_free_periods(today_classes)

        # Attendance calculation
        cursor.execute("SELECT * FROM attendance WHERE username = ?", (username,))
        attendance_rows = cursor.fetchall()

        target_attendance = 75
        attendance_details = []
        for att in attendance_rows:
            tot = att["total_classes"]
            att_cls = att["attended_classes"]
            pct = round((att_cls / tot) * 100) if tot > 0 else 0
            needed = 0
            if pct < target_attendance and (100 - target_attendance) > 0:
                needed = max(1, int(((target_attendance * tot) - (100 * att_cls)) / (100 - target_attendance) + 0.999))
            attendance_details.append({
                "record": att,
                "percentage": pct,
                "classes_needed": needed
            })

        cursor.execute("SELECT * FROM assignments ORDER BY id DESC")
        assignments = cursor.fetchall()

        cursor.execute("SELECT * FROM announcements ORDER BY id DESC")
        announcements = cursor.fetchall()

        cursor.execute("SELECT * FROM complaints WHERE username = ? ORDER BY id DESC", (username,))
        complaints = cursor.fetchall()

        cursor.execute("SELECT * FROM queries WHERE username = ? ORDER BY id DESC", (username,))
        queries = cursor.fetchall()

        cursor.execute("SELECT * FROM faqs ORDER BY id DESC")
        faqs = cursor.fetchall()

        # Fetch student's own submissions keyed by assignment_id
        cursor.execute(
            "SELECT * FROM assignment_submissions WHERE username = ? ORDER BY submitted_at DESC",
            (username,)
        )
        my_submissions_rows = cursor.fetchall()
        my_submissions = {row['assignment_id']: row for row in my_submissions_rows}

        conn.close()
        return render_template(
            "student_dashboard.html",
            username=username,
            timetable=timetable,
            today_name=today_name,
            today_classes=today_classes,
            free_periods=free_periods,
            upcoming_classes=upcoming_classes,
            attendance_details=attendance_details,
            target_attendance=target_attendance,
            assignments=assignments,
            announcements=announcements,
            complaints=complaints,
            queries=queries,
            faqs=faqs,
            my_submissions=my_submissions
        )


# ---------------- ADMIN ROUTE ALIAS ----------------
@app.route("/admin")
def admin():
    if "username" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))


# ---------------- FAQS MANAGEMENT ----------------
@app.route("/add_faq", methods=["POST"])
def add_faq():
    if "username" not in session or session.get("username") != "admin":
        return redirect(url_for("login"))
    question = (request.form.get("question") or "").strip()
    answer = (request.form.get("answer") or "").strip()
    tag = (request.form.get("tag") or "General").strip()
    if question and answer:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO faqs (question, answer, tag) VALUES (?, ?, ?)", (question, answer, tag))
        conn.commit()
        conn.close()
        try:
            from chatbot import _rag
            _rag.add_faq_entry(question, answer, tag)
        except Exception:
            pass
    return redirect(url_for("dashboard"))


@app.route("/delete_faq/<int:faq_id>", methods=["POST"])
def delete_faq(faq_id):
    if "username" not in session or session.get("username") != "admin":
        return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM faqs WHERE id = ?", (faq_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


# ---------------- COMPLAINTS MANAGEMENT & SUBMISSION ----------------
@app.route("/submit_complaint", methods=["POST"])
def submit_complaint():
    if "username" not in session:
        return redirect(url_for("login"))
    category = request.form.get("category", "General")
    description = (request.form.get("description") or "").strip()
    if description:
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO complaints (username, category, description, status, date, admin_response) VALUES (?, ?, ?, ?, ?, ?)",
            (session["username"], category, description, "Pending", today_str, "")
        )
        conn.commit()
        conn.close()
    return redirect(url_for("dashboard"))


@app.route("/update_complaint/<int:complaint_id>", methods=["POST"])
def update_complaint(complaint_id):
    if "username" not in session or session.get("username") != "admin":
        return redirect(url_for("login"))
    status = request.form.get("status", "Pending")
    admin_response = (request.form.get("admin_response") or "").strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE complaints SET status = ?, admin_response = ? WHERE id = ?",
        (status, admin_response, complaint_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


# ---------------- QUERIES MANAGEMENT & SUBMISSION ----------------
@app.route("/submit_query", methods=["POST"])
def submit_query():
    if "username" not in session:
        return redirect(url_for("login"))
    subject = (request.form.get("subject") or "").strip()
    question = (request.form.get("question") or "").strip()
    if question:
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO queries (username, subject, question, status, date, admin_response) VALUES (?, ?, ?, ?, ?, ?)",
            (session["username"], subject or "General Query", question, "Pending", today_str, "")
        )
        conn.commit()
        conn.close()
    return redirect(url_for("dashboard"))


@app.route("/update_query/<int:query_id>", methods=["POST"])
def update_query(query_id):
    if "username" not in session or session.get("username") != "admin":
        return redirect(url_for("login"))
    status = request.form.get("status", "Pending")
    admin_response = (request.form.get("admin_response") or "").strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE queries SET status = ?, admin_response = ? WHERE id = ?",
        (status, admin_response, query_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


# ---------------- ANNOUNCEMENTS ----------------
@app.route("/add_announcement", methods=["POST"])
def add_announcement():
    if "username" not in session or session.get("username") != "admin":
        return redirect(url_for("login"))
    title = (request.form.get("title") or "").strip()
    content = (request.form.get("content") or "").strip()
    category = (request.form.get("category") or "General").strip()
    if title and content:
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO announcements (title, content, date, category) VALUES (?, ?, ?, ?)",
            (title, content, today_str, category)
        )
        conn.commit()
        conn.close()
    return redirect(url_for("dashboard"))


# ---------------- ATTENDANCE MANAGEMENT ----------------
@app.route("/update_attendance/<int:attendance_id>", methods=["POST"])
def update_attendance(attendance_id):
    if "username" not in session or session.get("username") != "admin":
        return redirect(url_for("login"))

    try:
        total_classes = int(request.form.get("total_classes", "0"))
        attended_classes = int(request.form.get("attended_classes", "0"))
    except ValueError:
        return redirect(url_for("dashboard"))

    if total_classes < 0 or attended_classes < 0 or attended_classes > total_classes:
        return redirect(url_for("dashboard"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE attendance SET total_classes = ?, attended_classes = ? WHERE id = ?",
        (total_classes, attended_classes, attendance_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


# ---------------- TIMETABLE MANAGEMENT ----------------
@app.route("/add_timetable_entry", methods=["POST"])
def add_timetable_entry():
    if "username" not in session or session.get("username") != "admin":
        return redirect(url_for("login"))
    semester = request.form.get("semester", "")
    day = request.form.get("day", "")
    time_slot = request.form.get("time_slot", "")
    subject = request.form.get("subject", "")
    faculty = request.form.get("faculty", "")
    room = request.form.get("room", "")
    is_next = 1 if request.form.get("is_next") else 0

    if semester and day and subject:
        conn = get_db_connection()
        cursor = conn.cursor()
        if is_next:
            cursor.execute("UPDATE timetable SET is_next = 0 WHERE semester = ?", (semester,))
        cursor.execute(
            "INSERT INTO timetable (day, time_slot, subject, faculty, room, semester, is_next) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (day, time_slot, subject, faculty, room, semester, is_next)
        )
        conn.commit()
        conn.close()
    return redirect(url_for("dashboard"))


@app.route("/delete_timetable_entry/<int:entry_id>", methods=["POST"])
def delete_timetable_entry(entry_id):
    if "username" not in session or session.get("username") != "admin":
        return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM timetable WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/clear_timetable", methods=["POST"])
def clear_timetable():
    if "username" not in session or session.get("username") != "admin":
        return redirect(url_for("login"))
    semester = request.form.get("semester", "")
    conn = get_db_connection()
    cursor = conn.cursor()
    if semester and semester != "All":
        cursor.execute("DELETE FROM timetable WHERE semester = ?", (semester,))
    else:
        cursor.execute("DELETE FROM timetable")
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


# ---------------- ASSIGNMENT SUBMISSION ----------------
@app.route("/submit_assignment/<int:assignment_id>", methods=["POST"])
def submit_assignment(assignment_id):
    if "username" not in session or session.get("role") == "admin":
        return redirect(url_for("login"))

    username = session["username"]

    if "file" not in request.files:
        return redirect(url_for("dashboard") + "#assignments")

    file = request.files["file"]
    if file.filename == "":
        return redirect(url_for("dashboard") + "#assignments")

    if not allowed_file(file.filename):
        return redirect(url_for("dashboard") + "#assignments")

    original_filename = secure_filename(file.filename)
    ext = original_filename.rsplit(".", 1)[-1].lower()
    stored_filename = f"{username}_{assignment_id}_{uuid.uuid4().hex[:8]}.{ext}"
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], stored_filename))

    submitted_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if already submitted — update instead of duplicate
    cursor.execute(
        "SELECT id FROM assignment_submissions WHERE assignment_id = ? AND username = ?",
        (assignment_id, username)
    )
    existing = cursor.fetchone()

    if existing:
        # Delete old file first
        cursor.execute(
            "SELECT filename FROM assignment_submissions WHERE assignment_id = ? AND username = ?",
            (assignment_id, username)
        )
        old = cursor.fetchone()
        if old:
            old_path = os.path.join(app.config["UPLOAD_FOLDER"], old["filename"])
            if os.path.exists(old_path):
                os.remove(old_path)

        cursor.execute(
            """UPDATE assignment_submissions
               SET filename = ?, original_filename = ?, submitted_at = ?, status = 'Submitted', grade = '', feedback = ''
               WHERE assignment_id = ? AND username = ?""",
            (stored_filename, original_filename, submitted_at, assignment_id, username)
        )
    else:
        cursor.execute(
            """INSERT INTO assignment_submissions
               (assignment_id, username, filename, original_filename, submitted_at)
               VALUES (?, ?, ?, ?, ?)""",
            (assignment_id, username, stored_filename, original_filename, submitted_at)
        )

    conn.commit()
    conn.close()
    return redirect(url_for("dashboard") + "?tab=assignments")


@app.route("/download_submission/<int:submission_id>")
def download_submission(submission_id):
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM assignment_submissions WHERE id = ?", (submission_id,))
    sub = cursor.fetchone()
    conn.close()

    if not sub:
        return "File not found", 404

    # Only admin or the submitter can download
    if username != "admin" and sub["username"] != username:
        return "Unauthorized", 403

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        sub["filename"],
        as_attachment=True,
        download_name=sub["original_filename"]
    )


@app.route("/grade_submission/<int:submission_id>", methods=["POST"])
def grade_submission(submission_id):
    if "username" not in session or session.get("username") != "admin":
        return redirect(url_for("login"))

    grade = (request.form.get("grade") or "").strip()
    feedback = (request.form.get("feedback") or "").strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE assignment_submissions SET grade = ?, feedback = ?, status = 'Graded' WHERE id = ?",
        (grade, feedback, submission_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("view_submissions"))


@app.route("/submissions")
def view_submissions():
    if "username" not in session or session.get("username") != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, a.title AS assignment_title, a.subject
        FROM assignment_submissions s
        JOIN assignments a ON s.assignment_id = a.id
        ORDER BY s.submitted_at DESC
    """)
    submissions = cursor.fetchall()
    conn.close()
    return render_template("submissions.html", submissions=submissions)


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- CHATBOT APIS ----------------
@app.route("/api/chat", methods=["POST"])
def api_chat():
    try:
        data = request.get_json() or {}
        query = data.get("query") or data.get("question", "")
        query = query.strip()
        if not query:
            return jsonify({"response": "Please ask a question."})
        answer = get_chatbot_response(
            query,
            semester=session.get("semester"),
            username=session.get("username")
        )
        return jsonify({"response": answer, "answer": answer})
    except Exception as e:
        print("Chatbot API error:", e)
        return jsonify({"response": "Sorry, I am having trouble processing your query right now."}), 500


@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json() or {}
        question = data.get("question") or data.get("query", "")
        question = question.strip()
        if not question:
            return jsonify({"answer": "Please enter a question."})
        answer = get_chatbot_response(
            question,
            semester=session.get("semester"),
            username=session.get("username")
        )
        return jsonify({"answer": answer, "response": answer})
    except Exception as e:
        print("Chatbot error:", e)
        return jsonify({"answer": "Sorry, I couldn't process your question."}), 500


# ---------------- REDIRECT ALIASES ----------------
@app.route("/timetable")
@app.route("/assignments")
@app.route("/notices")
@app.route("/staff")
@app.route("/complaints", methods=["GET", "POST"])
@app.route("/chatbot")
def portal_aliases():
    return redirect(url_for("dashboard"))


# ---------------- RUN APPLICATION ----------------
if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )