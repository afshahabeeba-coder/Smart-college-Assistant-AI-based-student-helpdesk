import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "helpdesk.db")
DB_NAME = DB_PATH

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'student',
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        semester TEXT NOT NULL
    )
    ''')

    # FAQs / Knowledge Base
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS faqs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        tag TEXT NOT NULL
    )
    ''')

    # Timetable
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day TEXT NOT NULL,
        time_slot TEXT NOT NULL,
        subject TEXT NOT NULL,
        faculty TEXT NOT NULL,
        room TEXT NOT NULL,
        semester TEXT NOT NULL,
        is_next INTEGER NOT NULL DEFAULT 0
    )
    ''')

    timetable_columns = [row[1] for row in cursor.execute("PRAGMA table_info(timetable)").fetchall()]
    if 'is_next' not in timetable_columns:
        cursor.execute("ALTER TABLE timetable ADD COLUMN is_next INTEGER NOT NULL DEFAULT 0")

    # Attendance
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        subject TEXT NOT NULL,
        total_classes INTEGER NOT NULL,
        attended_classes INTEGER NOT NULL
    )
    ''')

    # Assignments
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        due_date TEXT NOT NULL,
        semester TEXT NOT NULL
    )
    ''')

    # Assignment Submissions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS assignment_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        filename TEXT NOT NULL,
        original_filename TEXT NOT NULL,
        submitted_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Submitted',
        grade TEXT NOT NULL DEFAULT '',
        feedback TEXT NOT NULL DEFAULT '',
        FOREIGN KEY (assignment_id) REFERENCES assignments(id)
    )
    ''')

    # Announcements
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        date TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'General'
    )
    ''')

    announcement_columns = [row[1] for row in cursor.execute("PRAGMA table_info(announcements)").fetchall()]
    if 'category' not in announcement_columns:
        cursor.execute("ALTER TABLE announcements ADD COLUMN category TEXT NOT NULL DEFAULT 'General'")

    # Complaints
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        date TEXT NOT NULL,
        admin_response TEXT NOT NULL DEFAULT ''
    )
    ''')

    complaint_columns = [row[1] for row in cursor.execute("PRAGMA table_info(complaints)").fetchall()]
    if 'admin_response' not in complaint_columns:
        cursor.execute("ALTER TABLE complaints ADD COLUMN admin_response TEXT NOT NULL DEFAULT ''")

    # Student queries
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS queries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        subject TEXT NOT NULL,
        question TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        date TEXT NOT NULL,
        admin_response TEXT NOT NULL DEFAULT ''
    )
    ''')

    conn.commit()

    # Seed Default Data if empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        # Seed users
        cursor.execute("INSERT INTO users (username, password, role, name, department, semester) VALUES (?, ?, ?, ?, ?, ?)",
                       ("student", "student123", "student", "Alex Smith", "Computer Science", "Sem 5"))
        cursor.execute("INSERT INTO users (username, password, role, name, department, semester) VALUES (?, ?, ?, ?, ?, ?)",
                       ("admin", "admin123", "admin", "Dr. Admin", "Administration", "All"))

    cursor.execute("SELECT COUNT(*) FROM faqs")
    if cursor.fetchone()[0] == 0:
        faqs = [("when are the holidays?","You will be having long holidays for Dussehra,Sankranthi and minimal days for small fests"),
            ("who is my faculty for DAA?","D.Venugopal"),       
            ("What are the college working hours?", "The college is open from 9:00 AM to 5:00 PM, Monday through Friday.", "timing"),
            ("When are the end semester exams scheduled?", "End semester examinations are scheduled to begin on November 15th.", "exam"),
            ("How can I check my attendance?", "You can check your attendance status under the 'Attendance' section in your dashboard.", "attendance"),
            ("Where is the library located?", "The central library is located in Block B, Ground Floor and is open until 8:00 PM.", "facility"),
            ("How do I submit an assignment?", "Assignments can be viewed in the 'Assignments' tab and submitted via the portal or directly to your professor.", "assignment"),
            ("How do I register a complaint or grievance?", "You can submit complaints using the 'Complaints' tab in your student dashboard. The administration reviews them within 48 hours.", "complaint"),
            ("Who is the Head of Computer Science Department?", "Dr. Robert Johnson is the Head of the Computer Science Department.", "faculty"),
            ("What documents are required for scholarship application?", "You need your semester fee receipt, previous year mark sheet, ID card, and income certificate.", "scholarship"),
            ("Is Wi-Fi available on campus?", "Yes, high-speed campus Wi-Fi is available. Connect to 'Campus-Secure' using your student credentials.", "facility"),
            ("How do I reset my password?", "Please contact the IT Helpdesk in Block C for password resets.", "accouunt")
        ]
        cursor.executemany("INSERT INTO faqs (question, answer, tag) VALUES (?, ?, ?)", faqs)

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS system_config (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')
    cursor.execute("SELECT value FROM system_config WHERE key = 'timetable_seeded'")
    seeded = cursor.fetchone()
    if not seeded:
        cursor.execute("SELECT COUNT(*) FROM timetable")
        if cursor.fetchone()[0] == 0:
            timetable = [
                ("Monday", "09:00 AM - 10:00 AM", "Artificial Intelligence", "Dr. Alan Turing", "Lab 3", "Sem 5"),
                ("Monday", "10:00 AM - 11:00 AM", "Database Management", "Prof. Edgar Codd", "Hall 102", "Sem 5"),
                ("Monday", "11:15 AM - 12:15 PM", "Web Development", "Tim Berners", "Lab 1", "Sem 5"),
                ("Tuesday", "09:00 AM - 10:00 AM", "Software Engineering", "Dr. Winston Royce", "Hall 104", "Sem 5"),
                ("Tuesday", "10:00 AM - 11:00 AM", "Artificial Intelligence", "Dr. Alan Turing", "Hall 102", "Sem 5"),
                ("Wednesday", "09:00 AM - 10:00 AM", "Computer Networks", "Dr. Vint Cerf", "Hall 101", "Sem 5"),
                ("Wednesday", "11:15 AM - 12:15 PM", "Database Management", "Prof. Edgar Codd", "Lab 2", "Sem 5"),
                ("Thursday", "10:00 AM - 11:00 AM", "Web Development", "Tim Berners", "Lab 1", "Sem 5"),
                ("Thursday", "02:00 PM - 04:00 PM", "AI Practical", "Dr. Alan Turing", "Lab 3", "Sem 5"),
                ("Friday", "09:00 AM - 11:00 AM", "Mini Project Workshop", "Prof. Grace Hopper", "Project Hall", "Sem 5")
            ]
            cursor.executemany("INSERT INTO timetable (day, time_slot, subject, faculty, room, semester) VALUES (?, ?, ?, ?, ?, ?)", timetable)
        cursor.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES ('timetable_seeded', '1')")

    cursor.execute("SELECT COUNT(*) FROM attendance")
    if cursor.fetchone()[0] == 0:
        attendance = [
            ("student", "`Artificial Intelligence`", 25, 20),
            ("student", "Database Management", 22, 10),
            ("student", "Web Development", 20, 19),
            ("student", "Software Engineering", 24, 24),
            ("student", "Computer Networks", 21, 7)
        ]
        cursor.executemany("INSERT INTO attendance (username, subject, total_classes, attended_classes) VALUES (?, ?, ?, ?)", attendance)

    cursor.execute("SELECT COUNT(*) FROM assignments")
    if cursor.fetchone()[0] == 0:
        assignments = [
            ("Artificial Intelligence", "Implement A* Search Algorithm", "Write a Python script implementing A* pathfinding on a grid.", "2026-09-25", "Sem 5"),
            ("Database Management", "Normalization & SQL Queries", "Complete normalization up to 3NF and write complex SQL joins.", "2026-09-30", "Sem 5"),
            ("Web Development", "Responsive Portfolio Website", "Build a fully responsive portfolio using Tailwind CSS and JavaScript.", "2026-10-05", "Sem 5")
        ]
        cursor.executemany("INSERT INTO assignments (subject, title, description, due_date, semester) VALUES (?, ?, ?, ?, ?)", assignments)

    cursor.execute("SELECT COUNT(*) FROM announcements")
    if cursor.fetchone()[0] == 0:
        announcements = [
            ("TechFest 2026 Registration Open", "Annual inter-college TechFest registration is now open. Participate in coding, robotics, and gaming events.", "2026-09-10"),
            ("Mid-Term Examination Schedule", "Mid-term examinations will commence from October 1st, 2026. Check notice boards for details.", "2026-09-08"),
            ("Library Timestamps Extended", "Central Library will remain open 24/7 during the examination week.", "2026-09-05")
        ]
        cursor.executemany("INSERT INTO announcements (title, content, date) VALUES (?, ?, ?)", announcements)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
