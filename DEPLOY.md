# Deployment Guide

This project is planned to be deployed with:
- Render for the Flask backend API
- Vercel for the frontend UI

This guide covers the steps to prepare the project, push it to Git, and deploy both parts.

---

## 1. Make sure you are in the project root

From your workspace root:

```bash
cd c:\Users\Akshaya\college
```

---

## 2. Create the Git ignore file

A `.gitignore` file is already created in the project root to avoid pushing:
- virtual environments
- Python cache files
- local databases
- uploaded files
- Chroma database files
- environment variables
- frontend build output

If you want to check it:

```bash
type .gitignore
```

---

## 3. Initialize Git

If this repo is not already initialized:

```bash
git init
git branch -M main
```

If you already have a repo, skip this step.

---

## 4. Add and commit your files

```bash
git add .
git commit -m "Initial project setup"
```

If Git asks for your identity:

```bash
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

---

## 5. Connect to GitHub

Create a GitHub repository first, then run:

```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

If you already connected a remote, use:

```bash
git remote -v
```

and then:

```bash
git push -u origin main
```

---

## 6. Deploy the backend on Render

### 6.1 Prepare the backend project

Open the backend folder:

```bash
cd helpdesk_project
```

Create a virtual environment:

```bash
python -m venv venv
venv\Scripts\activate
```

Install required packages:

```bash
pip install -r requirements.txt
pip install gunicorn
```

Test the app locally:

```bash
python app.py
```

The app should run on:

```text
http://127.0.0.1:5000
```

### 6.2 Important Render settings

For Render, use the start command:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

This assumes:
- the file is named `app.py`
- the Flask app object is named `app`

If your file or variable name is different, adjust the command accordingly.

### 6.3 Deploy on Render

1. Open Render
2. Click New > Web Service
3. Connect your GitHub repo
4. Choose the backend project directory or repo
5. Set the build command:

```bash
pip install -r requirements.txt
```

6. Set the start command:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

7. Click Create Web Service

After deployment, Render will give you a URL like:

```text
https://your-backend-name.onrender.com
```

---

## 7. Deploy the frontend on Vercel

### Option A: Use a separate frontend repo

This is the recommended structure.

Create a new frontend project using:
- React
- Vite
- Next.js
- or plain HTML/JavaScript

### Option B: Use the same repo with a frontend folder

If you want to keep one repo, create a frontend folder such as:

```text
frontend/
```

Then push both backend and frontend to the same GitHub repo.

### 7.1 Connect to Vercel

1. Go to Vercel
2. Click New Project
3. Import your frontend repo
4. Keep the default project settings
5. Click Deploy

Your frontend URL will look like:

```text
https://your-project-name.vercel.app
```

---

## 8. Connect frontend to backend

In the frontend app, set the backend URL as an environment variable.

Example in Vercel:

```bash
VITE_API_URL=https://your-backend-name.onrender.com
```

Then call it in the frontend like:

```javascript
const API_URL = import.meta.env.VITE_API_URL;

fetch(`${API_URL}/api/chat`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ message: "hello" })
})
```

---

## 9. CORS fix for the backend

If the frontend cannot reach the backend, enable CORS in Flask.

Install:

```bash
pip install flask-cors
```

Then in the backend app add:

```python
from flask_cors import CORS

CORS(app, resources={r"/api/*": {"origins": "*"}})
```

This allows Vercel frontend requests to the Render backend.

---

## 10. Important production notes for this project

This project uses:
- Flask
- SQLite
- ChromaDB
- local uploaded files

For deployment, watch out for:

### Database
- SQLite is fine for small projects, but keep backups
- avoid losing the database after each redeploy

### Uploaded files
- do not forget to persist the upload folder
- upload folder should exist on production server

### Chroma database
- keep it in a persistent folder
- do not reset it on every deployment

### Secret keys
Use environment variables for:
- `SECRET_KEY`
- database config
- external APIs

Example:

```bash
export SECRET_KEY=your-secret-key
```

---

## 11. Git workflow summary

Use this every time you update code:

```bash
git add .
git commit -m "Update project"
git push origin main
```

Then the Render and Vercel services can redeploy automatically if connected to GitHub.

---

## 12. Recommended structure

The cleanest deployment structure is:

```text
project-root/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── templates/
│   └── static/
├── frontend/
│   ├── src/
│   ├── package.json
│   └── .env
├── .gitignore
├── README.md
└── DEPLOY.md
```

If you are not splitting the app yet, you can still deploy the Flask app to Render as a single service.

---

## 13. Quick start checklist

Before pushing to Git and deploying:

- [ ] `.gitignore` is created
- [ ] all virtual environments are excluded
- [ ] no local DB files are committed
- [ ] no `.env` file is pushed
- [ ] backend dependencies are in `requirements.txt`
- [ ] backend uses `gunicorn`
- [ ] frontend is ready for Vercel
- [ ] backend URL is configured in the frontend

---

## 14. Final note

For your current app, the easiest real-world setup is:
- Render for the Flask backend
- Vercel for the frontend UI
- cross-origin API requests between them

If you want, I can also create the exact backend and frontend deployment files for your project next.
