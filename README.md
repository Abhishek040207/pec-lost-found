# PEC Lost & Found

🔗 **Live site:** [https://pec-lost-found.onrender.com](https://pec-lost-found.onrender.com)

A full-stack web app for Punjab Engineering College students to report, browse, and reclaim lost & found items on campus. Only `@pec.edu.in` Google accounts can sign in.

---

## Features

- **Google OAuth Login** — sign in with your PEC email only (`@pec.edu.in`)
- **Post Lost Items** — with image upload (Cloudinary), color, category, location, date
- **Post Found Items** — limited details posted intentionally (no color/marks) to protect ownership
- **Claim System** — claimants describe hidden details only they'd know; finder approves or rejects
- **Mark Lost Item as Returned** — close your own lost post once you've got it back
- **Smart Email Notifications** — get emailed when a found item matches your lost category
- **In-App Notification Bell** — real-time notification drawer, polls every 30 seconds
- **Dashboard** — manage all your posts, review incoming claims, see stats
- **Browse & Filter** — search by keyword, filter by category, paginated results
- **Feedback System** — star ratings + comments sent to the admin email
- **Fully Responsive** — works on mobile and desktop
- **SEO Ready** — meta tags, Open Graph, sitemap.xml, robots.txt

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python / Flask |
| Database | PostgreSQL (via psycopg2) |
| Auth | Google OAuth 2.0 (Authlib) |
| Image Storage | Cloudinary |
| Email | Google Apps Script HTTPS relay (see `docs/mail_relay.gs`) |
| Hosting | Render |
| Frontend | Jinja2 templates, Vanilla CSS, Vanilla JS |

---

## Local Setup

### Prerequisites
- Python 3.8+
- A PostgreSQL database (local or cloud)
- A Google Cloud OAuth 2.0 client (for login)

### 1. Clone & navigate
```bash
git clone https://github.com/your-username/pec-lost-found.git
cd pec-lost-found
```

### 2. Create a virtual environment
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

### 4. Set environment variables

Create a `.env` file in the project root:

```env
# Required
SECRET_KEY=any_random_secret_string
DATABASE_URL=postgresql://user:password@localhost:5432/pec_lost_found
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret

# Image uploads (optional locally, required on Render)
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Email — for local dev use Gmail SMTP App Password
MAIL_USERNAME=peclostandfound@gmail.com
MAIL_PASSWORD=your_gmail_app_password

# Email — for Render use the HTTPS relay (see docs/mail_relay.gs)
# MAIL_RELAY_URL=https://script.google.com/macros/s/.../exec
# MAIL_RELAY_SECRET=your_relay_secret
```

### 5. Run the app
```bash
python app.py
```

### 6. Open in browser
```
http://localhost:5000
```

> **Note:** Google OAuth requires the redirect URI `http://localhost:5000/auth/google/callback` to be added in your Google Cloud Console under Authorised redirect URIs.

---

## Email Setup (Production — Render)

Render's free tier **blocks all outbound SMTP ports**. Emails are sent via a Google Apps Script relay instead.

1. Open `docs/mail_relay.gs` and paste the script into a new [Google Apps Script](https://script.google.com) project (logged in as `peclostandfound@gmail.com`)
2. Set `var SECRET` to a strong random string
3. Deploy as a **Web App** → Execute as: Me → Who has access: Anyone
4. Copy the `/exec` URL
5. Set these two env vars on Render:
   - `MAIL_RELAY_URL` → the `/exec` URL
   - `MAIL_RELAY_SECRET` → the same secret string

---

## Project Structure

```
pec-lost-found/
├── app.py                     ← Flask backend — all routes, DB logic, email
├── mailer.py                  ← Email module (HTTPS relay or Gmail SMTP)
├── test_email.py              ← Standalone email delivery test script
├── requirements.txt
├── Procfile                   ← Render: gunicorn app:app
├── docs/
│   └── mail_relay.gs          ← Google Apps Script email relay
├── static/
│   ├── css/main.css           ← All styles (dark glassmorphism theme)
│   ├── js/main.js             ← Frontend interactivity
│   ├── img/pec-logo.png
│   └── noise.png              ← Grain texture overlay
└── templates/
    ├── base.html              ← Sidebar shell, notifications, toasts
    ├── login.html             ← Google OAuth login page
    ├── dashboard.html         ← User dashboard
    ├── browse.html            ← Public item browser
    ├── post_lost.html         ← Post a lost item
    ├── post_found.html        ← Post a found item
    ├── claim.html             ← Submit a claim
    ├── complete_profile.html  ← First-time profile completion
    ├── profile.html           ← Profile view & edit
    └── feedback.html          ← Star rating feedback
```

---

## Deployment (Render)

1. Push this repo to GitHub
2. Create a new **Web Service** on [Render](https://render.com) connected to the repo
3. Set **Build Command:** `pip install -r requirements.txt`
4. Set **Start Command:** `gunicorn app:app`
5. Add all environment variables from the `.env` section above under **Environment**
6. Create a **PostgreSQL** database on Render and copy its `DATABASE_URL` into env vars

Render auto-deploys on every push to `main`.
