# Smart College Assistant Knowledge Guide

## About the Student Portal
The Smart College Assistant is a Flask-based student helpdesk portal. Students can sign in to view their dashboard, ask the AI assistant questions, view the timetable, check attendance, read assignments and announcements, submit complaints, send queries, and browse FAQs. The portal is available locally at `http://127.0.0.1:5000` when the Flask server is running.

## Student Login and Registration
Students can sign in with their username and password. New students can register with their name, username, password, department, and semester. The demo student account is username `student` with password `student123`. The demo administrator account is username `admin` with password `admin123`. These demo credentials should be changed in a real deployment.

## Chatbot Questions
Students can ask about assignments, due dates, timetable, classes, faculty, rooms, attendance, exams, announcements, complaints, queries, placements, internships, resumes, certificates, facilities, and general academic topics. Questions should include specific keywords such as the assignment title, subject, day, internship, placement, resume, or certificate for more precise answers.

## Timetable and Classes
The Timetable tab shows scheduled classes with the day, time slot, subject, faculty, room, and semester. Students can ask for today's classes, tomorrow's classes, a class on a particular day, a subject's faculty, the class room, upcoming classes, or free periods. If a timetable entry is not available, the student should contact the administrator.

## Attendance
The Attendance tab shows attendance by subject, attended classes, total classes, percentage, and the number of classes needed to reach the target. The portal uses a default target attendance of 75 percent. Students should verify official attendance rules with their department because medical permissions and shortage rules may vary.

## Assignments and Homework
The Assignments tab lists the assignment subject, title, description, and due date. To submit work, open Assignments, choose a file, and the file is submitted automatically after selection. A student can replace an earlier submission by choosing another file. Supported file types are PDF, DOC, DOCX, TXT, PY, ZIP, JPG, JPEG, and PNG. The maximum upload size is 16 MB. Students can download their submitted file and view its status, grade, and feedback after an administrator reviews it.

## Complaints and Grievances
Students can submit a complaint from the Complaints tab by selecting a category and entering a description. A new complaint starts with Pending status. Administrators can mark it In Progress or Resolved and add an administrative response. Students can view their complaint history and replies from the dashboard.

## Student Queries
Students can send an academic or administrative question from the Queries tab with a subject and detailed question. A new query starts with Pending status. Administrators can add a response and update its status. Students should include relevant dates, department, semester, and supporting context when asking for help.

## Announcements and Notices
The dashboard displays college announcements with a title, message, date, and category. Students can ask the chatbot for the latest announcements or search for a notice by its topic. Official announcements should be treated as the current source for deadlines and events.

## Frequently Asked Questions Management
Administrators can add or delete FAQ entries from the admin dashboard. FAQ answers are stored in the SQLite database and added to the retrieval index so new college-specific information can be available to the chatbot. Administrators should keep answers concise, accurate, and specific to the institution.

## Placements and Internships
The Training and Placement Cell is located in the Administrative Block, 2nd Floor. Students in Sem 5 and Sem 7 can register for campus interviews through the student portal. Mandatory summer internship certificates should be submitted to the departmental coordinator. Students should ask the placement cell for current company lists, eligibility criteria, application deadlines, interview schedules, and offer-letter procedures because these change by recruitment drive.

## Resume and CV Documents
For a resume or CV, students should keep their latest academic marksheets, degree or provisional certificate details, internship and project information, workshop and training certificates, technical skills, contact details, LinkedIn or portfolio link, achievements, and relevant experience letters ready. Entrance scorecards, category certificates, and a recent photograph may be requested for particular applications. Students should use accurate information and save the final resume as a PDF before submitting it.

## Engineering Admission Documents
Common engineering admission documents include the 10th certificate and marksheet, 12th or intermediate certificate and marksheet, transfer certificate, migration certificate when applicable, entrance examination rank card or scorecard, domicile or residence certificate, caste or category certificate when applicable, income or EWS certificate when applicable, identity proof, passport photographs, medical fitness certificate, and study or conduct certificate. Requirements vary by university and admission route, so students must confirm the final checklist with the institution.

## Library Timings
The central college library is open Monday through Saturday from 8:00 AM to 8:00 PM. On Sundays, it is open from 10:00 AM to 4:00 PM. Students must carry their digital student ID card to enter.

## Exam Fees and Deadlines
Regular semester examination fees must be paid through the student portal before the 25th of every month. Late payments incur a fine of $50 per week for up to two weeks, after which permission from the Dean of Academic Affairs is required.

## Hostel and Accommodation
Hostel room maintenance requests can be raised through the Complaints section. Wardens inspect rooms every Tuesday and Thursday between 4:00 PM and 6:00 PM.

## Wi-Fi and Network Connectivity
To connect to the campus Wi-Fi network `CampusSecure`, use the student portal username and Wi-Fi password. For connection issues, contact the IT Helpdesk at room 302 or email `it-support@college.edu`.

## Sports Complex and Gym
The indoor sports complex and gym are open daily from 6:00 AM to 9:00 AM and from 4:00 PM to 8:00 PM. Registration is free for enrolled students.

## When Information Is Missing
The chatbot should not invent college-specific deadlines, fees, eligibility rules, company names, or contact details. If the answer is not in the knowledge guide, live portal data, or administrator FAQs, students should submit a query under the Queries tab or ask an administrator to add an FAQ.
