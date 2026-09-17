import json
import os
import re
import datetime
import urllib.error
import urllib.request
import urllib.parse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from database import get_db_connection
from rag import HelpdeskRAG

# Initialize RAG retriever and ingest knowledge base documents on startup
_rag = HelpdeskRAG()
_rag.ingest_documents(os.path.join(os.path.dirname(__file__), "knowledge_base"))

GENERAL_FALLBACK = (
    "I couldn't find a direct match in the college records. "
    "You can ask an administrator to add this topic, submit a query under the 'Queries' tab, "
    "or try asking with specific subject/topic keywords."
)


# ---------------- 1. DYNAMIC ANNOUNCEMENTS RETRIEVAL ----------------
def _get_announcements_response(user_query):
    query_lower = user_query.lower().strip()
    announcement_triggers = [
        'announcement', 'announcements', 'notice', 'notices',
        'event', 'events', 'circular', 'news', 'update', 'updates'
    ]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, content, date, category FROM announcements ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    # Check for specific announcement topic matches in query
    matched = []
    for row in rows:
        title_lower = row['title'].lower()
        content_lower = row['content'].lower()
        cat_lower = row['category'].lower()

        words = [w for w in title_lower.split() if len(w) > 3]
        if any(w in query_lower for w in words) or (cat_lower in query_lower and len(cat_lower) > 3):
            matched.append(row)

    if matched:
        formatted = ["Here are the matching college notices:"]
        for r in matched:
            formatted.append(f"• **{r['title']}** ({r['category']} - {r['date']}):<br>{r['content']}")
        return "<br><br>".join(formatted)

    # If general inquiry about notices/announcements
    if any(trigger in query_lower for trigger in announcement_triggers):
        formatted = ["Here are the latest college announcements:"]
        for r in rows[:4]:
            formatted.append(f"• **{r['title']}** ({r['category']} - {r['date']}):<br>{r['content']}")
        return "<br><br>".join(formatted)

    return None


# ---------------- 2. DYNAMIC FAQS RETRIEVAL (SQLITE + RAG) ----------------
def _get_faq_response(user_query):
    # Step A: Always check live database FAQs (covers newly added FAQs instantly)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT question, answer, tag FROM faqs")
    rows = cursor.fetchall()
    conn.close()

    best_sql_answer = None
    best_sql_score = 0.0

    if rows:
        questions = [row['question'] for row in rows]
        answers = [row['answer'] for row in rows]
        corpus = questions + [user_query]
        try:
            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = vectorizer.fit_transform(corpus)
            cosine_sim = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])
            best_idx = cosine_sim.argmax()
            best_sql_score = cosine_sim[0, best_idx]
            if best_sql_score >= 0.18:
                best_sql_answer = answers[best_idx]
        except Exception:
            pass

    # Step B: Query ChromaDB Vector Store with strict distance threshold
    retrieved_chunks = _rag.query(user_query, n_results=2, max_distance=1.15)

    # Return the highest confidence source
    if best_sql_answer and best_sql_score >= 0.35:
        return best_sql_answer

    if retrieved_chunks:
        return retrieved_chunks[0]

    if best_sql_answer and best_sql_score >= 0.18:
        return best_sql_answer

    return None


# ---------------- 3. GENERAL KNOWLEDGE & WEB LOOKUP ----------------
def _get_web_knowledge_response(user_query):
    # Strip common leading question phrases
    cleaned = re.sub(
        r'^(what is|who is|who was|tell me about|explain|define|how to|meaning of|what do you mean by)\s+',
        '',
        user_query.strip(),
        flags=re.I
    )
    cleaned = cleaned.rstrip('?').strip()
    if len(cleaned) < 2:
        return None

    try:
        # Search Wikipedia API
        search_url = (
            f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch="
            f"{urllib.parse.quote(cleaned)}&utf8=&format=json"
        )
        req = urllib.request.Request(search_url, headers={'User-Agent': 'SmartCollegeHelpdesk/1.0'})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            results = data.get('query', {}).get('search', [])
            if not results:
                return None
            title = results[0]['title']

        # Get summary extract
        sum_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
        req_sum = urllib.request.Request(sum_url, headers={'User-Agent': 'SmartCollegeHelpdesk/1.0'})
        with urllib.request.urlopen(req_sum, timeout=4) as resp_sum:
            data_sum = json.loads(resp_sum.read().decode('utf-8'))
            extract = data_sum.get('extract')
            if extract and len(extract) > 35:
                return f"**{title}**<br>{extract}"
    except Exception:
        return None

    return None


# ---------------- 4. BUILT-IN ACADEMIC FALLBACK KNOWLEDGE ----------------
def _get_academic_fallback(user_query):
    q = user_query.lower()

    if any(k in q for k in ['cgpa', 'sgpa', 'gpa', 'calculate marks', 'grading']):
        return (
            "**CGPA & SGPA Calculation Guide:**<br>"
            "• **SGPA (Semester GPA)** = Sum of (Course Credits × Grade Points) ÷ Total Semester Credits.<br>"
            "• **CGPA (Cumulative GPA)** = Average of all SGPAs across completed semesters.<br>"
            "• Standard Grade Points: O (10), A+ (9), A (8), B+ (7), B (6), C (5), F (0)."
        )

    if any(k in q for k in ['attendance criteria', 'minimum attendance', '75% attendance', '75 percent']):
        return (
            "**Attendance Policy:**<br>"
            "• Minimum mandatory attendance is **75%** per subject to be eligible for end-semester examinations.<br>"
            "• If your attendance is between 65% and 75%, medical certificates or official permissions must be submitted to the HOD.<br>"
            "• Below 65% results in detainment for that course."
        )

    if any(k in q for k in ['exam preparation', 'study tips', 'how to prepare for exams', 'prepare for semester']):
        return (
            "**Exam Preparation Tips:**<br>"
            "1. Review the syllabus and focus on high-weightage modules.<br>"
            "2. Solve previous year question papers (PYQs) from the college digital library.<br>"
            "3. Make concise summary notes and cheat sheets for formulas.<br>"
            "4. Form peer study groups and attend faculty revision sessions."
        )

    if any(k in q for k in ['internship', 'placement', 'training', 'job']):
        return (
            "**Internship & Placement Cell:**<br>"
            "• The Training and Placement Cell (T&P) is located in the Administrative Block, 2nd Floor.<br>"
            "• Students in Sem 5 and Sem 7 can register for campus interviews through the student portal.<br>"
            "• Mandatory summer internship certificates must be submitted to your departmental coordinator."
        )

    if any(k in q for k in ['resume', 'resumé', 'cv', 'curriculum vitae']):
        return (
            "**Documents for a Resume / CV:**<br>"
            "• Keep your latest academic marksheets and degree or provisional certificate details ready.<br>"
            "• Include relevant internship, project, workshop, training, and certification details with dates.<br>"
            "• Add a concise skills section, contact details, LinkedIn or portfolio link, and your preferred engineering stream.<br>"
            "• Keep supporting documents such as entrance scorecards, achievements, experience letters, and a recent photograph available when requested.<br>"
            "• Use accurate information and save the final resume as a PDF before submitting it."
        )

    return None


# ---------------- 5. OPTIONAL LLM API INTEGRATION ----------------
def _get_general_response(user_query):
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return None

    endpoint = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
    payload = json.dumps({
        'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
        'messages': [
            {
                'role': 'system',
                'content': (
                    'You are a concise, helpful assistant inside a college student helpdesk. '
                    'Answer questions clearly, academically, and helpfully. '
                    'Keep answers informative and relevant to college students.'
                )
            },
            {'role': 'user', 'content': user_query}
        ],
        'temperature': 0.3
    }).encode('utf-8')

    request = urllib.request.Request(
        endpoint + '/chat/completions',
        data=payload,
        headers={
            'Authorization': 'Bearer ' + api_key,
            'Content-Type': 'application/json'
        },
        method='POST'
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
        return result['choices'][0]['message']['content'].strip()
    except Exception:
        return None


# ---------------- 6. DYNAMIC TIMETABLE RETRIEVAL ----------------
def _get_timetable_response(user_query, semester=None):
    query_lower = user_query.lower().strip()

    timetable_words = [
        'timetable', 'forenoon', 'afternoon', 'schedule', 'class', 'classes',
        'lecture', 'subject', 'faculty', 'teacher', 'professor',
        'today', 'tomorrow',
        'monday', 'tuesday', 'wednesday', 'thursday',
        'friday', 'saturday', 'sunday',
        'first class', 'next class', 'free period', 'free periods',
        'break', 'breaks', 'free time', 'room', 'where'
    ]

    if not any(word in query_lower for word in timetable_words):
        return None

    conn = get_db_connection()
    cursor = conn.cursor()

    if semester:
        cursor.execute("""
            SELECT day, time_slot, subject, faculty, room, semester
            FROM timetable
            WHERE semester = ?
        """, (semester,))
    else:
        cursor.execute("""
            SELECT day, time_slot, subject, faculty, room, semester
            FROM timetable
        """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "No timetable information is currently available in the system."

    # ---------------------------------------------------------
    # 1. RESOLVE DAY
    # ---------------------------------------------------------
    today = datetime.date.today()

    if 'tomorrow' in query_lower:
        requested_day = (today + datetime.timedelta(days=1)).strftime('%A').lower()
    elif 'today' in query_lower:
        requested_day = today.strftime('%A').lower()
    else:
        requested_day = None
        days = [
            'monday', 'tuesday', 'wednesday', 'thursday',
            'friday', 'saturday', 'sunday'
        ]

        for day in days:
            if day in query_lower:
                requested_day = day
                break

    # ---------------------------------------------------------
    # 2. FACULTY / TEACHER QUERY
    # ---------------------------------------------------------
    faculty_query = any(
        phrase in query_lower
        for phrase in [
            'who is my faculty',
            'who is the faculty',
            'who is my teacher',
            'who is the teacher',
            'faculty for',
            'faculty of',
            'teacher for',
            'teacher of',
            'professor for',
            'professor of'
        ]
    )

    if faculty_query:

        # Find subject after "for" or "of"
        subject_match = re.search(
            r'(?:faculty|teacher|professor)\s+(?:for|of)\s+(.+?)(?:\?|$)',
            query_lower
        )

        if subject_match:
            requested_subject = subject_match.group(1).strip()
        else:
            requested_subject = query_lower

        faculty_names = []

        for row in rows:
            subject = str(row['subject']).strip().lower()
            faculty = str(row['faculty']).strip()

            if (
                requested_subject == subject
                or requested_subject in subject
                or subject in requested_subject
            ):
                if faculty and faculty not in faculty_names:
                    faculty_names.append(faculty)

        if faculty_names:
            return (
                f"**Your faculty for {requested_subject.upper()} is "
                f"{', '.join(faculty_names)}.**"
            )

        return (
            f"I couldn't find faculty information for "
            f"**{requested_subject.upper()}**."
        )

    # ---------------------------------------------------------
    # 3. ROOM / LOCATION QUERY
    # ---------------------------------------------------------
    room_query = any(
        phrase in query_lower
        for phrase in [
            'where is my class',
            'where is the class',
            'where is my',
            'which room',
            'what room',
            'classroom',
            'room for'
        ]
    )

    if room_query:

        matched_rooms = []

        for row in rows:
            subject = str(row['subject']).strip().lower()
            room = str(row['room']).strip()
            day = str(row['day']).strip().lower()

            day_match = (
                requested_day is None
                or day == requested_day
            )

            if day_match:
                # Look for subject name in question
                subject_words = [
                    w for w in subject.split()
                    if len(w) > 2
                ]

                if (
                    subject in query_lower
                    or any(w in query_lower for w in subject_words)
                ):
                    matched_rooms.append(row)

        if matched_rooms:
            if requested_day:
                r = matched_rooms[0]
                return (
                    f"Your **{r['subject']}** class on "
                    f"**{r['day'].capitalize()}** is in "
                    f"**{r['room']}**."
                )

            unique_rooms = []
            for r in matched_rooms:
                room = str(r['room']).strip()
                if room not in unique_rooms:
                    unique_rooms.append(room)

            return (
                f"The class is in **{', '.join(unique_rooms)}**."
            )

    # ---------------------------------------------------------
    # 4. FREE PERIOD / BREAK QUERY
    # ---------------------------------------------------------
    if any(
        phrase in query_lower
        for phrase in [
            'free period', 'free periods',
            'free time', 'break', 'breaks'
        ]
    ):

        target_day = (
            requested_day
            if requested_day
            else today.strftime('%A').lower()
        )

        day_classes = [
            r for r in rows
            if str(r['day']).strip().lower() == target_day
        ]

        if not day_classes:
            return (
                f"You have no classes scheduled on "
                f"**{target_day.capitalize()}**, so your entire day is free!"
            )

        parsed = []

        for r in day_classes:
            parts = [
                p.strip()
                for p in str(r['time_slot'])
                .replace(" to ", "-")
                .split("-")
            ]

            if len(parts) == 2:
                for fmt in (
                    "%I:%M %p",
                    "%I %p",
                    "%H:%M",
                    "%I:%M"
                ):
                    try:
                        t1 = datetime.datetime.strptime(
                            parts[0].strip().upper(), fmt
                        ).time()

                        t2 = datetime.datetime.strptime(
                            parts[1].strip().upper(), fmt
                        ).time()

                        parsed.append(
                            (t1, t2, r['subject'])
                        )
                        break
                    except ValueError:
                        pass

        parsed.sort(
            key=lambda x: (x[0].hour, x[0].minute)
        )

        free_slots = []

        for i in range(len(parsed) - 1):

            end_curr = parsed[i][1]
            start_next = parsed[i + 1][0]

            end_m = end_curr.hour * 60 + end_curr.minute
            start_m = start_next.hour * 60 + start_next.minute

            gap = start_m - end_m

            if gap >= 10:
                s_str = end_curr.strftime("%I:%M %p").lstrip("0")
                e_str = start_next.strftime("%I:%M %p").lstrip("0")

                free_slots.append(
                    f"• **{s_str} – {e_str}** "
                    f"({gap} min break)"
                )

        if free_slots:
            return (
                f"Here are your free periods for "
                f"**{target_day.capitalize()}**:<br>"
                + "<br>".join(free_slots)
            )

        return (
            f"You have continuous classes with no major "
            f"free-period breaks on **{target_day.capitalize()}**."
        )

    # ---------------------------------------------------------
    # 5. SPECIFIC TIME QUERY
    # ---------------------------------------------------------
    time_match = re.search(
        r'\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b',
        query_lower
    )

    if time_match:

        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        am_pm = time_match.group(3)

        # If AM/PM is explicitly given
        if am_pm == 'pm' and hour < 12:
            hour += 12
        elif am_pm == 'am' and hour == 12:
            hour = 0

        requested_minutes = hour * 60 + minute

        time_matches = []

        for row in rows:

            day = str(row['day']).strip().lower()

            if requested_day and day != requested_day:
                continue

            parts = [
                p.strip()
                for p in str(row['time_slot'])
                .replace(" to ", "-")
                .split("-")
            ]

            if len(parts) != 2:
                continue

            start_time = None
            end_time = None

            for fmt in (
                "%I:%M %p",
                "%I %p",
                "%H:%M",
                "%I:%M"
            ):
                try:
                    start_time = datetime.datetime.strptime(
                        parts[0].upper(), fmt
                    ).time()

                    end_time = datetime.datetime.strptime(
                        parts[1].upper(), fmt
                    ).time()

                    break
                except ValueError:
                    pass

            if not start_time or not end_time:
                continue

            start_minutes = (
                start_time.hour * 60 +
                start_time.minute
            )

            end_minutes = (
                end_time.hour * 60 +
                end_time.minute
            )

            # Match the requested time if it falls
            # inside the class period.
            if start_minutes <= requested_minutes < end_minutes:
                time_matches.append(row)

        if time_matches:

            formatted = []

            for r in time_matches:
                formatted.append(
                    f"**{r['day']}** ({r['time_slot']}): "
                    f"**{r['subject']}** with "
                    f"{r['faculty']} at {r['room']} "
                    f"({r['semester']})"
                )

            return "<br>".join(formatted)

        if requested_day:
            return (
                f"You don't have a class at "
                f"**{time_match.group(0).strip()}** on "
                f"**{requested_day.capitalize()}**."
            )

    # ---------------------------------------------------------
    # 6. SUBJECT QUERY
    # ---------------------------------------------------------
    matched = []

    for row in rows:

        day = str(row['day']).strip().lower()
        subject = str(row['subject']).strip().lower()
        faculty = str(row['faculty']).strip().lower()

        day_match = (
            requested_day is None
            or day == requested_day
        )

        subject_match = (
            subject in query_lower
            or any(
                word in query_lower
                for word in subject.split()
                if len(word) > 2
            )
        )

        faculty_match = (
            faculty in query_lower
        )

        if day_match and (subject_match or faculty_match):
            matched.append(row)

    # Return a targeted subject or faculty result before handling broad
    # requests for every class on a day.
    if matched:
        formatted = ["Here are the matching class details:"]
        for r in matched:
            formatted.append(
                f"• **{r['day']}** ({r['time_slot']}): "
                f"**{r['subject']}** with {r['faculty']} at {r['room']}"
            )
        return "<br>".join(formatted)

    # ---------------------------------------------------------
    # 7. GENERAL DAY QUERY
    # ---------------------------------------------------------
    if requested_day and (
        'class' in query_lower
        or 'classes' in query_lower
        or 'today' in query_lower
        or 'tomorrow' in query_lower
    ):

        day_rows = [
            r for r in rows
            if str(r['day']).strip().lower() == requested_day
        ]

        if day_rows:
            formatted = [
                f"Here is your timetable for "
                f"**{requested_day.capitalize()}**:"
            ]

            for r in day_rows:
                formatted.append(
                    f"• **{r['time_slot']}**: "
                    f"**{r['subject']}** with "
                    f"{r['faculty']} at {r['room']}"
                )

            return "<br>".join(formatted)

    # ---------------------------------------------------------
    # 8. FIRST CLASS
    # ---------------------------------------------------------
    if 'first class' in query_lower:

        target_day = (
            requested_day
            if requested_day
            else today.strftime('%A').lower()
        )

        day_rows = [
            r for r in rows
            if str(r['day']).strip().lower() == target_day
        ]

        if day_rows:

            def get_start_minutes(row):
                try:
                    first_part = (
                        str(row['time_slot'])
                        .replace(" to ", "-")
                        .split("-")[0]
                        .strip()
                    )

                    for fmt in (
                        "%I:%M %p",
                        "%I %p",
                        "%H:%M",
                        "%I:%M"
                    ):
                        try:
                            t = datetime.datetime.strptime(
                                first_part.upper(), fmt
                            ).time()

                            return t.hour * 60 + t.minute
                        except ValueError:
                            pass
                except Exception:
                    pass

                return 9999

            day_rows.sort(key=get_start_minutes)

            r = day_rows[0]

            return (
                f"Your first class on "
                f"**{target_day.capitalize()}** is "
                f"**{r['subject']}** from "
                f"**{r['time_slot']}** with "
                f"{r['faculty']} at {r['room']}."
            )

    # ---------------------------------------------------------
    # 9. NEXT CLASS
    # ---------------------------------------------------------
    if 'next class' in query_lower:

        target_day = (
            requested_day
            if requested_day
            else today.strftime('%A').lower()
        )

        day_rows = [
            r for r in rows
            if str(r['day']).strip().lower() == target_day
        ]

        if day_rows:

            def get_start(row):
                first_part = (
                    str(row['time_slot'])
                    .replace(" to ", "-")
                    .split("-")[0]
                    .strip()
                )

                for fmt in (
                    "%I:%M %p",
                    "%I %p",
                    "%H:%M",
                    "%I:%M"
                ):
                    try:
                        t = datetime.datetime.strptime(
                            first_part.upper(), fmt
                        ).time()

                        return t.hour * 60 + t.minute
                    except ValueError:
                        pass

                return 9999

            day_rows.sort(key=get_start)

            r = day_rows[0]

            return (
                f"Your next class on "
                f"**{target_day.capitalize()}** is "
                f"**{r['subject']}** from "
                f"**{r['time_slot']}** with "
                f"{r['faculty']} at {r['room']}."
            )

    # ---------------------------------------------------------
    # 10. GENERAL TIMETABLE REQUEST
    # ---------------------------------------------------------
    if any(
        phrase in query_lower
        for phrase in [
            'timetable',
            'schedule',
            'show timetable',
            'show my timetable',
            'my timetable'
        ]
    ):

        formatted = ["Here is your semester timetable:"]

        for r in rows:
            formatted.append(
                f"• **{r['day']}** ({r['time_slot']}): "
                f"**{r['subject']}** with "
                f"{r['faculty']} at {r['room']} "
                f"({r['semester']})"
            )

        return "<br>".join(formatted)

    return None
# ---------------- 7. DYNAMIC ASSIGNMENTS RETRIEVAL ----------------
def _get_assignment_response(user_query):
    query_lower = user_query.lower()
    if not any(word in query_lower for word in ['assignment', 'assignments', 'homework', 'due', 'submission', 'task', 'project']):
        return None

    # Let the FAQ/RAG pipeline answer process questions such as how to submit,
    # instead of replacing the answer with the live assignment list.
    process_terms = [
        'how do', 'how to', 'submit', 'upload', 'file', 'resubmit',
        're-submit', 'turn in', 'procedure', 'process', 'format'
    ]
    if any(term in query_lower for term in process_terms):
        return (
            "**How to submit an assignment:**<br>"
            "• Open the **Assignments** tab on your student dashboard.<br>"
            "• Select the assignment file; it is submitted automatically after selection.<br>"
            "• Supported formats are PDF, DOC, DOCX, TXT, PY, ZIP, JPG, JPEG, and PNG.<br>"
            "• The maximum file size is 16 MB. You can select another file later to re-submit."
        )

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT subject, title, description, due_date, semester FROM assignments ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "No assignment records are currently available in the portal."

    matched = []
    for row in rows:
        if row['subject'].lower() in query_lower or row['title'].lower() in query_lower or row['description'].lower() in query_lower:
            matched.append(row)

    if matched:
        formatted = ["Here are the matching assignment details:"]
        for r in matched:
            formatted.append(f"• **{r['title']}** ({r['subject']}): {r['description']} — Due: **{r['due_date']}**")
        return "<br>".join(formatted)

    if any(phrase in query_lower for phrase in ['assignment', 'assignments', 'homework', 'due dates', 'list assignments', 'show assignments']):
        formatted = ["Here are the current assignments:"]
        for r in rows:
            formatted.append(f"• **{r['title']}** ({r['subject']}): {r['description']} — Due: **{r['due_date']}**")
        return "<br>".join(formatted)

    return None


# ---------------- 8. MULTI-INTENT DAY PLANNING ----------------
def _get_day_plan_response(user_query, username=None, semester=None):
    query_lower = user_query.lower()
    planning_terms = ['plan my day', 'plan my week', 'what can i do', 'help me plan', 'organize my day']
    has_class_intent = any(word in query_lower for word in ['class', 'classes', 'timetable', 'schedule'])
    has_assignment_intent = any(word in query_lower for word in ['assignment', 'assignments', 'homework', 'due'])
    has_attendance_intent = 'attendance' in query_lower or 'attend' in query_lower

    if not (
        any(term in query_lower for term in planning_terms)
        or (has_class_intent and has_assignment_intent and has_attendance_intent)
    ):
        return None

    conn = get_db_connection()
    cursor = conn.cursor()
    target_day = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%A')
    target_semester = semester or 'Sem 5'

    cursor.execute(
        "SELECT day, time_slot, subject, faculty, room FROM timetable WHERE day = ? AND (semester = ? OR semester = 'Sem 5') ORDER BY id",
        (target_day, target_semester)
    )
    tomorrow_classes = cursor.fetchall()

    cursor.execute(
        "SELECT title, subject, description, due_date FROM assignments WHERE due_date >= ? ORDER BY due_date ASC LIMIT 5",
        (datetime.date.today().isoformat(),)
    )
    upcoming_assignments = cursor.fetchall()

    attendance_username = username or 'student'
    cursor.execute(
        "SELECT subject, total_classes, attended_classes FROM attendance WHERE username = ? ORDER BY subject",
        (attendance_username,)
    )
    attendance_rows = cursor.fetchall()
    conn.close()

    lines = ["**Your college day-planning summary:**"]
    if tomorrow_classes:
        lines.append(f"<br>**Tomorrow's classes ({target_day}):**")
        for row in tomorrow_classes:
            lines.append(f"• **{row['time_slot']}**: {row['subject']} with {row['faculty']} in {row['room']}")
    else:
        lines.append(f"<br>**Tomorrow's classes ({target_day}):** No classes are listed in the portal.")

    if upcoming_assignments:
        lines.append("<br>**Upcoming assignments:**")
        for row in upcoming_assignments:
            lines.append(f"• **{row['title']}** ({row['subject']}) is due **{row['due_date']}**. {row['description']}")
    else:
        lines.append("<br>**Upcoming assignments:** None are currently listed.")

    at_risk = []
    for row in attendance_rows:
        total = row['total_classes']
        attended = row['attended_classes']
        percentage = round((attended / total) * 100) if total else 0
        if percentage < 75:
            at_risk.append(f"{row['subject']} ({percentage}%, {attended}/{total})")

    if at_risk:
        lines.append("<br>**Attendance priority:**")
        lines.append("• Below the 75% target: " + ", ".join(at_risk) + ". Prioritize these classes and contact your department about any approved medical or attendance exception.")
    else:
        lines.append("<br>**Attendance priority:** No subject is currently below the 75% target in the portal.")

    lines.append("<br>**Suggested plan:** Attend tomorrow's classes, prioritize any subject below 75%, and reserve your next study block for the assignment with the nearest due date.")
    return "<br>".join(lines)


def _get_plan_submission_guidance(user_query):
    query_lower = user_query.lower()
    planning_words = [
        'plan', 'planning', 'organize', 'schedule', 'roadmap',
        'what should i do', 'how can i prepare', 'next steps'
    ]
    submission_words = [
        'submit', 'submission', 'upload', 'turn in', 'send',
        'register', 'apply', 'documents', 'certificate'
    ]
    topic_words = [
        'assignment', 'homework', 'complaint', 'grievance', 'query',
        'question', 'internship', 'placement', 'resume', 'cv',
        'certificate', 'project', 'attendance'
    ]

    is_planning_question = any(word in query_lower for word in planning_words)
    is_submission_question = any(word in query_lower for word in submission_words)
    has_topic = any(word in query_lower for word in topic_words)
    if not has_topic or not (is_planning_question or is_submission_question):
        return None

    sections = []
    if any(word in query_lower for word in ['assignment', 'homework', 'project']):
        sections.append(
            "**Assignment or project submission:** Open the Assignments tab, choose the file, and it will submit automatically. "
            "You can re-submit by selecting a replacement file. Supported formats include PDF, DOC, DOCX, TXT, PY, ZIP, JPG, JPEG, and PNG; the limit is 16 MB."
        )
    if any(word in query_lower for word in ['complaint', 'grievance']):
        sections.append(
            "**Complaint submission:** Open Complaints, choose a category, describe the issue, and submit it. "
            "Track the response and status from the same tab."
        )
    if any(word in query_lower for word in ['query', 'question']):
        sections.append(
            "**Query submission:** Open Queries, enter a subject and detailed question, then submit it. "
            "Include your semester, department, relevant dates, and supporting context so the administrator can respond accurately."
        )
    if any(word in query_lower for word in ['internship', 'placement', 'resume', 'cv', 'certificate']):
        sections.append(
            "**Placement, internship, or resume plan:** Keep marksheets, projects, internships, training certificates, skills, achievements, "
            "contact details, and relevant scorecards ready. Save the final resume as a PDF. For campus interviews, check the Training and Placement Cell for the current eligibility, deadline, and document checklist."
        )
    if 'attendance' in query_lower:
        sections.append(
            "**Attendance plan:** Check the Attendance tab, identify subjects below the 75% target, prioritize those classes, and contact your department about any approved attendance exception."
        )
    if is_planning_question:
        sections.append(
            "**Planning tip:** Start with the nearest deadline, reserve a study block, attend classes affecting your attendance, and use Queries for any college-specific rule that is not shown in the portal."
        )

    return "<br><br>".join(sections)


def _get_college_help_response(user_query):
    query_lower = user_query.lower()
    broad_questions = [
        'what can you help', 'what information can you provide',
        'college info', 'college information', 'college services',
        'help me with college', 'what do you know'
    ]
    if not any(phrase in query_lower for phrase in broad_questions):
        return None

    return (
        "**I can help with college information about:**<br>"
        "• Timetable: classes, days, times, faculty, rooms, and free periods.<br>"
        "• Attendance: subject percentages, classes attended, and attendance priorities.<br>"
        "• Assignments: titles, descriptions, due dates, file submission, re-submission, grades, and feedback.<br>"
        "• Complaints and queries: how to submit them and how to track responses.<br>"
        "• Announcements, exams, library, hostel, Wi-Fi, sports, placements, internships, resumes, certificates, and engineering admission documents.<br><br>"
        "Ask a specific question such as **'What classes do I have tomorrow?'**, **'How do I submit an assignment?'**, or **'What documents are needed for an internship?'**. "
        "For a college rule, deadline, or detail not shown in the portal, submit a question under the Queries tab or ask an administrator to add an FAQ."
    )


def _get_leave_attendance_response(user_query, username=None, semester=None):
    query_lower = user_query.lower()
    leave_words = ['leave', 'absent', 'skip', 'miss', 'not attend']
    attendance_words = ['attendance', 'attend']
    if 'tomorrow' not in query_lower or not any(word in query_lower for word in leave_words):
        return None
    if not any(word in query_lower for word in attendance_words):
        return None

    conn = get_db_connection()
    cursor = conn.cursor()
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    tomorrow_name = tomorrow.strftime('%A')
    target_semester = semester or 'Sem 5'
    cursor.execute(
        "SELECT DISTINCT subject FROM timetable WHERE day = ? AND (semester = ? OR semester = 'Sem 5')",
        (tomorrow_name, target_semester)
    )
    subjects = [row['subject'] for row in cursor.fetchall()]
    attendance_username = username or 'student'
    attendance_by_subject = {}
    if subjects:
        placeholders = ','.join('?' for _ in subjects)
        cursor.execute(
            f"SELECT subject, total_classes, attended_classes FROM attendance WHERE username = ? AND subject IN ({placeholders})",
            [attendance_username, *subjects]
        )
        attendance_by_subject = {row['subject'].strip().lower(): row for row in cursor.fetchall()}
    conn.close()

    if not subjects:
        return f"There are no classes listed for tomorrow ({tomorrow_name}), so missing a scheduled class should not affect your recorded attendance. Follow the college's leave approval process for any other obligation."

    lines = [f"**Leave and attendance check for tomorrow ({tomorrow_name}):**"]
    risk_found = False
    for subject in subjects:
        record = attendance_by_subject.get(subject.strip().lower())
        if not record or record['total_classes'] <= 0:
            lines.append(f"• **{subject}**: attendance data is not available, so I cannot confirm whether leave is safe.")
            risk_found = True
            continue
        total = record['total_classes']
        attended = record['attended_classes']
        current = round((attended / total) * 100)
        projected = round((attended / (total + 1)) * 100)
        if projected < 75:
            risk_found = True
            advice = f"missing tomorrow would project {projected}% ({attended}/{total + 1}), below the 75% target"
        else:
            advice = f"missing tomorrow would project about {projected}% ({attended}/{total + 1})"
        lines.append(f"• **{subject}**: currently {current}% ({attended}/{total}); {advice}.")

    if risk_found:
        lines.append("<br>**Recommendation:** Avoid taking leave without approved permission because at least one subject is unknown or may fall below the 75% target. Contact your faculty or department if the leave is necessary.")
    else:
        lines.append("<br>**Recommendation:** Your recorded attendance remains at or above 75% after one missed class, but leave still requires approval under college rules.")
    return "<br>".join(lines)


# ---------------- MAIN CHATBOT PIPELINE ----------------
def get_chatbot_response(user_query, semester=None, username=None):
    cleaned_query = ' '.join(user_query.split())
    if not cleaned_query:
        return 'Please enter a question so I can help.'

    # 1. Check leave requests against tomorrow's live classes and attendance.
    leave_resp = _get_leave_attendance_response(cleaned_query, username, semester)
    if leave_resp:
        return leave_resp

    # 2. Combine multiple live portal signals for planning questions.
    day_plan_resp = _get_day_plan_response(cleaned_query, username, semester)
    if day_plan_resp:
        return day_plan_resp

    # 2. General planning and submission guidance.
    guidance_resp = _get_plan_submission_guidance(cleaned_query)
    if guidance_resp:
        return guidance_resp

    broad_help_resp = _get_college_help_response(cleaned_query)
    if broad_help_resp:
        return broad_help_resp

    # 3. Timetable query (live SQLite)
    timetable_resp = _get_timetable_response(cleaned_query, semester)
    if timetable_resp:
        return timetable_resp

    # 3. Assignments query (live SQLite)
    assignment_resp = _get_assignment_response(cleaned_query)
    if assignment_resp:
        return assignment_resp

    # 4. Announcements & Notices query (live SQLite)
    announcement_resp = _get_announcements_response(cleaned_query)
    if announcement_resp:
        return announcement_resp

    # 5. Knowledge Base & FAQs (live SQLite + Vector RAG)
    faq_resp = _get_faq_response(cleaned_query)
    if faq_resp:
        return faq_resp

    # 6. External LLM API (if configured)
    general_resp = _get_general_response(cleaned_query)
    if general_resp:
        return general_resp

    # 7. Live Web Knowledge Search (Wikipedia API for concepts, sciences, tech)
    college_specific_words = [
        'college', 'internship', 'internships',
        'certificate', 'certificates',
        'placement', 'placements',
        'faculty', 'teacher',
        'timetable', 'attendance',
        'exam', 'examination',
        'assignment', 'semester',
        'course', 'department'
    ]

    if not any(word in cleaned_query.lower() for word in college_specific_words):
        web_resp = _get_web_knowledge_response(cleaned_query)
        if web_resp:
            return web_resp

    # 8. Academic Fallback Dictionary
    academic_resp = _get_academic_fallback(cleaned_query)
    if academic_resp:
        return academic_resp

    return GENERAL_FALLBACK