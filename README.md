# 🎓 Smart College Assistant – AI-Based Student Helpdesk & Portal

Welcome to the **Smart College Assistant** – an intelligent, feature-rich web platform designed to streamline student support, academics, campus communication, and administrative tasks. 

---

## ✨ Key Features & Modules

### 🤖 AI Helpdesk & Chatbot
- **Smart FAQ Matching:** Powered by TF-IDF vectorization and cosine similarity (`scikit-learn`) to instantly answer student inquiries based on the college knowledge base (`knowledge_base/faq_guide.md`).
- **Optional LLM Integration:** Supports OpenAI-compatible API keys to handle general queries beyond the pre-configured FAQ.

### 📚 Student Portal (`/login`)
- **Interactive Dashboard:** View personal details, semester overview, and quick links.
- **Timetable & Attendance:** Check weekly class schedules and real-time attendance percentage trackers.
- **Assignment Submissions:** Track pending and submitted homework/projects.
- **Complaints & Grievances:** Register campus issues and track their real-time resolution status.
- **Announcements:** Stay updated with official college notices and events.

### 🛡️ Admin Control Panel (`/admin`)
- **System Overview:** Summary statistics of students, complaints, FAQs, and active announcements.
- **User Management:** View registered student directories.
- **Knowledge Base Management:** Add, edit, or delete FAQ entries to instantly update the AI assistant.
- **Complaint Management:** Review student grievances and update resolution statuses.
- **Announcement Broadcasts:** Publish new announcements instantly to all student dashboards.

---

## 🛠️ Tech Stack

- **Backend:** Python, Flask, SQLite (`helpdesk_project/database.py`)
- **AI / NLP:** Scikit-learn (TF-IDF & Cosine Similarity)
- **Frontend:** HTML5, Tailwind CSS, JavaScript, FontAwesome Icons

---

## 🚀 Quick Start Guide & Running the App

### 1. Prerequisites
Ensure you have **Python 3.8+** installed on your system.

### 2. Navigate to the Project Folder
Open your terminal and navigate into `helpdesk_project`:
```bash
cd helpdesk_project
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize & Seed the Database
```bash
python database.py
```

### 5. Run the Flask Server
```bash
python app.py
```

### 6. Open the App in Your Browser
Once the server is running, click or open the link below:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🔑 Demo Login Credentials

| Role | Username | Password | Key Capabilities |
| :--- | :--- | :--- | :--- |
| **Student** | `student` | `student123` | AI Chatbot, Timetable, Attendance, Assignments, Complaints |
| **Admin** | `admin` | `admin123` | Analytics, Knowledge Base Management, Complaint Resolution, Announcements |

---

## 📂 Project File Structure

```text
helpdesk_project/
├── app.py                  # Main Flask application routes & controllers
├── database.py             # SQLite database setup & default data seeding
├── chatbot.py              # Scikit-learn TF-IDF & Cosine Similarity AI NLP engine
├── rag.py                  # RAG retrieval logic & knowledge base interface
├── requirements.txt        # Python dependencies
├── helpdesk.db             # Generated SQLite database
├── knowledge_base/
│   └── faq_guide.md        # FAQ knowledge base
└── templates/
    ├── admin_dashboard.html
    ├── login.html
    ├── register.html
    └── student_dashboard.html
```
└── templates/
    ├── admin_dashboard.html   # Admin control panel (FAQs, Complaints, Announcements)
    ├── login.html             # Sleek login page with quick demo fillers
    ├── register.html          # Student account registration view
    └── student_dashboard.html # Student portal with timetable, attendance, & chatbot widget
```

## 📂 Project Structure

```text
helpdesk_project/
│
├── app.py                  # Main Flask application routes & controllers
├── database.py             # SQLite database setup & default data seeding
├── chatbot.py              # Scikit-learn TF-IDF & Cosine Similarity AI NLP engine
├── requirements.txt        # Python dependencies
├── helpdesk.db             # Generated SQLite database (created on init)
└── templates/
    ├── login.html          # Modern login page with demo credentials card
    ├── student_dashboard.html # Student dashboard, helpdesk tabs & floating AI chat
    └── admin_dashboard.html   # Admin control panel for FAQs, complaints & announcements
```
