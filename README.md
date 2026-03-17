# PEC Lost & Found — Setup Guide

## Prerequisites
- Python 3.8+ (comes with SQLite built-in)
- pip

## Setup (Linux & Windows)

### 1. Navigate to the project folder
```bash
cd pec_lost_found
```

### 2. (Recommended) Create a virtual environment
```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the app
```bash
python app.py
```

### 5. Open in browser
```
http://localhost:5000
```

---

## Project Structure
```
pec_lost_found/
├── app.py                  ← Flask backend (all routes + DB logic)
├── requirements.txt
├── pec_lostfound.db        ← SQLite DB (auto-created on first run)
├── static/
│   ├── css/
│   │   └── main.css        ← All styles
│   ├── js/
│   │   └── main.js         ← Frontend interactivity
│   └── uploads/            ← Uploaded images stored here
└── templates/
    ├── base.html           ← Sidebar + shell layout
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── browse.html
    ├── post_lost.html
    ├── post_found.html
    ├── claim.html
    └── profile.html
```

## Features
- **Register/Login** with Student ID, Department, Hostel status
- **Post Lost Items** with image upload, color, location, date
- **Post Found Items** with limited details (no color/marks) to protect ownership
- **Claim System** — claimants describe hidden details, finder approves/rejects
- **Dashboard** to manage your posts and review incoming claims
- **Browse + Filter** by category and search
- **Fully responsive** — works on mobile and desktop
- **SQLite database** — single portable file, no server required
