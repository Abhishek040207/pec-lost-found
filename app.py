from flask import Flask, render_template, request, redirect, url_for, session, flash, Response, jsonify
import sqlite3, os, cloudinary, cloudinary.uploader, smtplib, threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
from authlib.integrations.flask_client import OAuth

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'pec_lost_found_secret_2024')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'pec_lostfound.db')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png','jpg','jpeg','gif','webp'}

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

oauth = OAuth(app)
oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL, department TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL, contact TEXT NOT NULL,
            hosteler_status TEXT NOT NULL DEFAULT 'Day Scholar',
            hostel_name TEXT, password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS lost_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, item_name TEXT NOT NULL,
            category TEXT NOT NULL, color TEXT NOT NULL,
            location TEXT NOT NULL, image_path TEXT,
            date_lost DATE NOT NULL, description TEXT,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS found_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, brief_description TEXT NOT NULL,
            category TEXT NOT NULL, location TEXT NOT NULL,
            date_found DATE NOT NULL, status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            found_item_id INTEGER NOT NULL, claimant_user_id INTEGER NOT NULL,
            hidden_details TEXT NOT NULL, status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(found_item_id) REFERENCES found_items(id),
            FOREIGN KEY(claimant_user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS custom_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT UNIQUE NOT NULL,
            added_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            message TEXT NOT NULL,
            link TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    ''')
    # Migration: add email column for existing databases that predate this field
    try:
        conn.execute('ALTER TABLE users ADD COLUMN email TEXT')
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
    # Migration: drop the old sid column now that login/registration no longer use it
    try:
        conn.execute('ALTER TABLE users DROP COLUMN sid')
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already removed, or SQLite version doesn't support DROP COLUMN
    # Migration: add exact_location column to lost_items
    try:
        conn.execute('ALTER TABLE lost_items ADD COLUMN exact_location TEXT')
        conn.commit()
    except sqlite3.OperationalError:
        pass
    # Migration: add exact_location column to found_items
    try:
        conn.execute('ALTER TABLE found_items ADD COLUMN exact_location TEXT')
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

init_db()

PEC_EMAIL_DOMAIN = '@pec.edu.in'
MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')

# ─── Notification Helpers ─────────────────────────────────────────────────────

def create_notification(user_id, notif_type, message, link=None):
    """Store an in-app notification for a user."""
    try:
        conn = get_db()
        conn.execute(
            'INSERT INTO notifications (user_id, type, message, link) VALUES (?,?,?,?)',
            (user_id, notif_type, message, link)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Notification DB error: {e}")

def send_email(to_email, subject, body):
    """Send an email asynchronously via Gmail SMTP."""
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        return
    def _send():
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f'PEC Lost & Found <{MAIL_USERNAME}>'
            msg['To'] = to_email
            msg.attach(MIMEText(body, 'html'))
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(MAIL_USERNAME, MAIL_PASSWORD)
                smtp.sendmail(MAIL_USERNAME, to_email, msg.as_string())
            print(f"Email sent to {to_email}")
        except Exception as e:
            print(f"Email error: {e}")
    threading.Thread(target=_send, daemon=True).start()

def email_body(heading, lines, action_url=None, action_label=None):
    """Build a clean HTML email body."""
    btn = ''
    if action_url and action_label:
        btn = f'<p style="margin-top:20px;"><a href="{action_url}" style="background:#3b82f6;color:white;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:600;">{action_label}</a></p>'
    rows = ''.join(f'<p style="color:#d1d5db;margin:6px 0;">{l}</p>' for l in lines)
    return f"""
    <div style="background:#111111;font-family:sans-serif;padding:32px;">
      <div style="max-width:520px;margin:auto;background:#1c1c1c;border:1px solid #2e2e2e;border-radius:12px;padding:28px;">
        <h2 style="color:#f0f0f0;font-size:1.2rem;margin-bottom:16px;">🔔 {heading}</h2>
        {rows}
        {btn}
        <p style="color:#666;font-size:.75rem;margin-top:24px;">PEC Lost &amp; Found · Punjab Engineering College</p>
      </div>
    </div>"""

def is_valid_pec_email(email):
    email = email.strip().lower()
    return email.endswith(PEC_EMAIL_DOMAIN) and len(email) > len(PEC_EMAIL_DOMAIN)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_image(file):
    try:
        result = cloudinary.uploader.upload(file, folder='pec_lost_found')
        return result['secure_url']
    except Exception as e:
        print(f"Cloudinary error: {e}")
        return None

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if 'user_id' not in session:
        return None
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    return user

def get_all_locations():
    base = [
        'Library', 'NAB Classes', 'PEC Market', 'ED Halls',
        'Civil Department', 'ECE Department',
        'Cricket Ground', 'Basketball Court', 'Tennis Court', 'GYM',
        'Athletic Ground', 'Football Ground',
        'Shivalik Hostel', 'Aravali Hostel', 'Himalaya Hostel',
        'Kurukshetra Hostel', 'Kalpana Chawla Hostel', 'Vindhya Hostel'
    ]
    conn = get_db()
    custom = [r['location'] for r in conn.execute('SELECT location FROM custom_locations ORDER BY location').fetchall()]
    conn.close()
    combined = base + [l for l in custom if l not in base]
    return sorted(combined)

CATEGORIES = ['Electronics','Keys','Wallet/Purse','ID Card','Books/Notes','Clothing','Accessories','Bag/Backpack','Sports Equipment','Other']
PAGE_SIZE = 20

# ─── Auth ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login')
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    next_url = request.args.get('next') or url_for('dashboard')
    return render_template('login.html', next_url=next_url)

@app.route('/auth/google/login')
def google_login():
    next_url = request.args.get('next') or url_for('dashboard')
    session['post_login_redirect'] = next_url
    redirect_uri = url_for('google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def google_callback():
    try:
        token = oauth.google.authorize_access_token()
    except Exception as e:
        print(f"Google OAuth error: {e}")
        flash('Google sign-in failed. Please try again.', 'error')
        return redirect(url_for('login'))
    userinfo = token.get('userinfo') or {}
    email = (userinfo.get('email') or '').strip().lower()
    name = (userinfo.get('name') or '').strip() or (email.split('@')[0] if email else 'PEC User')
    if not userinfo.get('email_verified', True):
        flash('Your Google email is not verified.', 'error')
        return redirect(url_for('login'))
    if not is_valid_pec_email(email):
        flash('Please sign in with your PEC email ID (must end in @pec.edu.in).', 'error')
        return redirect(url_for('login'))
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE LOWER(email) = ?', (email,)).fetchone()
    is_new = False
    if not user:
        conn.execute('INSERT INTO users (full_name,department,email,contact,hosteler_status,hostel_name,password_hash) VALUES (?,?,?,?,?,?,?)',
            (name, '', email, '', 'Day Scholar', None, ''))
        conn.commit()
        user = conn.execute('SELECT * FROM users WHERE LOWER(email) = ?', (email,)).fetchone()
        is_new = True
    conn.close()
    session['user_id'] = user['id']
    session['user_name'] = user['full_name']
    next_url = session.pop('post_login_redirect', None) or url_for('dashboard')
    if is_new or not user['contact']:
        session['profile_next'] = next_url
        return redirect(url_for('complete_profile'))
    flash(f'Welcome, {user["full_name"].split()[0]}!', 'success')
    return redirect(next_url)

@app.route('/complete-profile', methods=['GET','POST'])
@login_required
def complete_profile():
    user = get_current_user()
    if request.method == 'POST':
        full_name = request.form.get('full_name','').strip()
        contact = request.form.get('contact','').strip()
        if not full_name or not contact:
            flash('Please fill in your name and contact number.', 'error')
            return render_template('complete_profile.html', user=user)
        conn = get_db()
        conn.execute('UPDATE users SET full_name=?, contact=? WHERE id=?',
            (full_name, contact, session['user_id']))
        conn.commit(); conn.close()
        session['user_name'] = full_name
        flash('Profile completed!', 'success')
        next_url = session.pop('profile_next', None) or url_for('dashboard')
        return redirect(next_url)
    return render_template('complete_profile.html', user=user)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ─── Delete Account ───────────────────────────────────────────────────────────

@app.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    uid = session['user_id']
    conn = get_db()
    conn.execute('DELETE FROM claims WHERE claimant_user_id = ?', (uid,))
    conn.execute('DELETE FROM lost_items WHERE user_id = ?', (uid,))
    founds = conn.execute('SELECT id FROM found_items WHERE user_id = ?', (uid,)).fetchall()
    for f in founds:
        conn.execute('DELETE FROM claims WHERE found_item_id = ?', (f['id'],))
    conn.execute('DELETE FROM found_items WHERE user_id = ?', (uid,))
    conn.execute('DELETE FROM users WHERE id = ?', (uid,))
    conn.commit(); conn.close()
    session.clear()
    flash('Your account has been deleted.', 'info')
    return redirect(url_for('login'))

# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    uid = session['user_id']
    my_lost = conn.execute('SELECT * FROM lost_items WHERE user_id = ? ORDER BY created_at DESC', (uid,)).fetchall()
    my_found = conn.execute('SELECT * FROM found_items WHERE user_id = ? ORDER BY created_at DESC', (uid,)).fetchall()
    my_claims = conn.execute('''
        SELECT c.*, u.full_name, u.department, u.contact, f.brief_description
        FROM claims c JOIN users u ON c.claimant_user_id = u.id
        JOIN found_items f ON c.found_item_id = f.id
        WHERE f.user_id = ? AND c.status = 'pending' ORDER BY c.created_at DESC
    ''', (uid,)).fetchall()
    conn.close()
    return render_template('dashboard.html', user=get_current_user(), my_lost=my_lost, my_found=my_found, my_claims=my_claims)

# ─── Browse ───────────────────────────────────────────────────────────────────

@app.route('/browse')
def browse():
    conn = get_db()
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    page = max(1, int(request.args.get('page', 1)))
    offset = (page - 1) * PAGE_SIZE

    lq_base = 'SELECT l.*, u.full_name, u.contact FROM lost_items l JOIN users u ON l.user_id = u.id WHERE l.status = "open"'
    fq_base = 'SELECT f.*, u.full_name, u.contact FROM found_items f JOIN users u ON f.user_id = u.id WHERE f.status = "open"'
    count_lq = 'SELECT COUNT(*) FROM lost_items l JOIN users u ON l.user_id = u.id WHERE l.status = "open"'
    count_fq = 'SELECT COUNT(*) FROM found_items f JOIN users u ON f.user_id = u.id WHERE f.status = "open"'

    params = []
    if category:
        lq_base += ' AND l.category = ?'
        fq_base += ' AND f.category = ?'
        count_lq += ' AND l.category = ?'
        count_fq += ' AND f.category = ?'
        params.append(category)
    if search:
        lq_base += ' AND (l.item_name LIKE ? OR l.location LIKE ?)'
        fq_base += ' AND (f.brief_description LIKE ? OR f.location LIKE ?)'
        count_lq += ' AND (l.item_name LIKE ? OR l.location LIKE ?)'
        count_fq += ' AND (f.brief_description LIKE ? OR f.location LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])

    total_lost = conn.execute(count_lq, params).fetchone()[0]
    total_found = conn.execute(count_fq, params).fetchone()[0]
    lost_items = conn.execute(lq_base + ' ORDER BY l.created_at DESC LIMIT ? OFFSET ?', params + [PAGE_SIZE, offset]).fetchall()
    found_items = conn.execute(fq_base + ' ORDER BY f.created_at DESC LIMIT ? OFFSET ?', params + [PAGE_SIZE, offset]).fetchall()
    conn.close()

    import math
    total_lost_pages = max(1, math.ceil(total_lost / PAGE_SIZE))
    total_found_pages = max(1, math.ceil(total_found / PAGE_SIZE))

    return render_template('browse.html',
        lost_items=lost_items, found_items=found_items,
        categories=CATEGORIES, selected_category=category, search=search,
        page=page, total_lost=total_lost, total_found=total_found,
        total_lost_pages=total_lost_pages, total_found_pages=total_found_pages)

# ─── Post Lost ────────────────────────────────────────────────────────────────

@app.route('/post-lost', methods=['GET','POST'])
@login_required
def post_lost():
    locations = get_all_locations()
    if request.method == 'POST':
        location = request.form.get('location','').strip()
        custom_loc = request.form.get('custom_location','').strip()
        if location == '__custom__' and custom_loc:
            location = custom_loc
            conn = get_db()
            try:
                conn.execute('INSERT OR IGNORE INTO custom_locations (location, added_by) VALUES (?,?)', (location, session['user_id']))
                conn.commit()
            except: pass
            conn.close()
        image_url = None
        if 'image' in request.files:
            f = request.files['image']
            if f and f.filename and allowed_file(f.filename):
                image_url = upload_image(f)
        conn = get_db()
        conn.execute('INSERT INTO lost_items (user_id,item_name,category,color,location,exact_location,image_path,date_lost,description) VALUES (?,?,?,?,?,?,?,?,?)',
            (session['user_id'], request.form.get('item_name','').strip(), request.form.get('category','').strip(),
             request.form.get('color','').strip(), location,
             request.form.get('exact_location','').strip() or None,
             image_url,
             request.form.get('date_lost','').strip(), request.form.get('description','').strip()))
        conn.commit(); conn.close()
        flash('Lost item posted successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('post_lost.html', categories=CATEGORIES, locations=locations)

# ─── Post Found ───────────────────────────────────────────────────────────────

@app.route('/post-found', methods=['GET','POST'])
@login_required
def post_found():
    locations = get_all_locations()
    if request.method == 'POST':
        location = request.form.get('location','').strip()
        custom_loc = request.form.get('custom_location','').strip()
        if location == '__custom__' and custom_loc:
            location = custom_loc
            conn = get_db()
            try:
                conn.execute('INSERT OR IGNORE INTO custom_locations (location, added_by) VALUES (?,?)', (location, session['user_id']))
                conn.commit()
            except Exception as e:
                print(f"DB error saving custom location: {e}")
            conn.close()
        conn = get_db()
        category = request.form.get('category','').strip()
        brief_desc = request.form.get('brief_description','').strip()
        date_found = request.form.get('date_found','').strip()
        conn.execute('INSERT INTO found_items (user_id,brief_description,category,location,exact_location,date_found) VALUES (?,?,?,?,?,?)',
            (session['user_id'], brief_desc, category, location,
             request.form.get('exact_location','').strip() or None,
             date_found))
        conn.commit()
        # Notify users who have open lost items in the same category
        matched = conn.execute(
            'SELECT l.user_id, u.email, u.full_name FROM lost_items l JOIN users u ON l.user_id=u.id WHERE l.category=? AND l.status="open" AND l.user_id!=?',
            (category, session['user_id'])
        ).fetchall()
        conn.close()
        for m in matched:
            msg = f'A found item in category <strong>{category}</strong> was just posted — it might be yours!'
            link = url_for('browse', category=category, _external=True)
            create_notification(m['user_id'], 'found_match', f'A found {category} item was posted — could be yours!', url_for('browse', category=category))
            send_email(m['email'], f'[PEC Lost & Found] A found {category} item was posted',
                email_body('Possible Match Found!', [
                    f'Hi {m["full_name"].split()[0]},',
                    f'Someone just posted a found item in the <strong style="color:#3b82f6">{category}</strong> category.',
                    'It might be your lost item. Click below to browse and claim it.'
                ], link, 'View Found Items'))
        flash('Found item posted!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('post_found.html', categories=CATEGORIES, locations=locations)

# ─── Claim ────────────────────────────────────────────────────────────────────

@app.route('/claim/<int:found_item_id>', methods=['GET','POST'])
@login_required
def claim_item(found_item_id):
    conn = get_db()
    found_item = conn.execute(
        'SELECT f.*, u.full_name, u.department, u.contact, u.hostel_name, u.hosteler_status FROM found_items f JOIN users u ON f.user_id = u.id WHERE f.id = ?',
        (found_item_id,)).fetchone()
    if not found_item:
        conn.close(); flash('Item not found.', 'error'); return redirect(url_for('browse'))
    if found_item['user_id'] == session['user_id']:
        conn.close(); flash('You cannot claim your own post.', 'error'); return redirect(url_for('browse'))
    existing_claim = conn.execute('SELECT id FROM claims WHERE found_item_id = ? AND claimant_user_id = ?', (found_item_id, session['user_id'])).fetchone()
    if request.method == 'POST':
        if existing_claim:
            flash('Already submitted a claim.', 'error'); conn.close(); return redirect(url_for('browse'))
        hidden_details = request.form.get('hidden_details','').strip()
        if len(hidden_details) < 20:
            flash('Please provide more detail (min 20 chars).', 'error'); conn.close()
            return render_template('claim.html', found_item=found_item, existing_claim=None)
        conn.execute('INSERT INTO claims (found_item_id,claimant_user_id,hidden_details) VALUES (?,?,?)', (found_item_id, session['user_id'], hidden_details))
        conn.commit()
        # Notify the finder
        finder = conn.execute('SELECT u.email, u.full_name FROM users u WHERE u.id=?', (found_item['user_id'],)).fetchone()
        claimant = conn.execute('SELECT full_name FROM users WHERE id=?', (session['user_id'],)).fetchone()
        conn.close()
        notif_msg = f'{claimant["full_name"]} submitted a claim on your found item: "{found_item["brief_description"]}"'
        create_notification(found_item['user_id'], 'claim_received', notif_msg, url_for('dashboard'))
        send_email(finder['email'], '[PEC Lost & Found] Someone claimed your found item',
            email_body('New Claim Received!', [
                f'Hi {finder["full_name"].split()[0]},',
                f'<strong>{claimant["full_name"]}</strong> has submitted a claim on your found item:',
                f'<em style="color:#a0a0a0">"{found_item["brief_description"]}"</em>',
                'Log in to your dashboard to review their hidden details and approve or reject the claim.'
            ], url_for('dashboard', _external=True), 'Review Claim'))
        flash('Claim submitted! The finder will review your description.', 'success')
        return redirect(url_for('browse'))
    conn.close()
    return render_template('claim.html', found_item=found_item, existing_claim=existing_claim)

# ─── Resolve Claim ────────────────────────────────────────────────────────────

@app.route('/resolve-claim/<int:claim_id>/<action>', methods=['POST'])
@login_required
def resolve_claim(claim_id, action):
    if action not in ('approve', 'reject'):
        flash('Invalid action.', 'error')
        return redirect(url_for('dashboard'))
    conn = get_db()
    claim = conn.execute('SELECT c.*, f.user_id as finder_id FROM claims c JOIN found_items f ON c.found_item_id = f.id WHERE c.id = ?', (claim_id,)).fetchone()
    if not claim or claim['finder_id'] != session['user_id']:
        conn.close(); flash('Unauthorized.', 'error'); return redirect(url_for('dashboard'))
    claimant = conn.execute('SELECT u.email, u.full_name FROM users u WHERE u.id=?', (claim['claimant_user_id'],)).fetchone()
    found_item_row = conn.execute('SELECT brief_description FROM found_items WHERE id=?', (claim['found_item_id'],)).fetchone()
    item_desc = found_item_row['brief_description'] if found_item_row else 'your item'
    if action == 'approve':
        conn.execute('UPDATE claims SET status = "approved" WHERE id = ?', (claim_id,))
        conn.execute('UPDATE found_items SET status = "resolved" WHERE id = ?', (claim['found_item_id'],))
        conn.execute('UPDATE claims SET status = "rejected" WHERE found_item_id = ? AND id != ?', (claim['found_item_id'], claim_id))
        conn.commit(); conn.close()
        create_notification(claim['claimant_user_id'], 'claim_approved',
            f'Your claim on "{item_desc}" was approved! Contact the finder to collect your item.', url_for('dashboard'))
        send_email(claimant['email'], '[PEC Lost & Found] Your claim was approved! 🎉',
            email_body('Claim Approved!', [
                f'Hi {claimant["full_name"].split()[0]},',
                f'Great news! Your claim on <em style="color:#a0a0a0">"{item_desc}"</em> has been <strong style="color:#22c55e">approved</strong>.',
                'The finder has confirmed you are the owner. Please contact them to collect your item.'
            ], url_for('dashboard', _external=True), 'Go to Dashboard'))
        flash('Claim approved! Item marked as returned.', 'success')
    else:
        conn.execute('UPDATE claims SET status = "rejected" WHERE id = ?', (claim_id,))
        conn.commit(); conn.close()
        create_notification(claim['claimant_user_id'], 'claim_rejected',
            f'Your claim on "{item_desc}" was rejected. You can still browse other found items.', url_for('browse'))
        send_email(claimant['email'], '[PEC Lost & Found] Your claim was not approved',
            email_body('Claim Rejected', [
                f'Hi {claimant["full_name"].split()[0]},',
                f'Unfortunately your claim on <em style="color:#a0a0a0">"{item_desc}"</em> was <strong style="color:#ef4444">rejected</strong> by the finder.',
                'This may mean the item belongs to someone else. You can continue browsing found items.'
            ], url_for('browse', _external=True), 'Browse Found Items'))
        flash('Claim rejected.', 'info')
    return redirect(url_for('dashboard'))

# ─── Delete ───────────────────────────────────────────────────────────────────

@app.route('/delete-lost/<int:item_id>', methods=['POST'])
@login_required
def delete_lost(item_id):
    conn = get_db()
    if conn.execute('SELECT id FROM lost_items WHERE id = ? AND user_id = ?', (item_id, session['user_id'])).fetchone():
        conn.execute('DELETE FROM lost_items WHERE id = ?', (item_id,))
        conn.commit(); flash('Post deleted.', 'info')
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/delete-found/<int:item_id>', methods=['POST'])
@login_required
def delete_found(item_id):
    conn = get_db()
    if conn.execute('SELECT id FROM found_items WHERE id = ? AND user_id = ?', (item_id, session['user_id'])).fetchone():
        conn.execute('DELETE FROM claims WHERE found_item_id = ?', (item_id,))
        conn.execute('DELETE FROM found_items WHERE id = ?', (item_id,))
        conn.commit(); flash('Post deleted.', 'info')
    conn.close()
    return redirect(url_for('dashboard'))

# ─── Profile ──────────────────────────────────────────────────────────────────

@app.route('/profile')
@login_required
def profile():
    user = get_current_user()
    conn = get_db()
    uid = session['user_id']
    stats = {
        'lost_posted': conn.execute('SELECT COUNT(*) FROM lost_items WHERE user_id = ?', (uid,)).fetchone()[0],
        'found_posted': conn.execute('SELECT COUNT(*) FROM found_items WHERE user_id = ?', (uid,)).fetchone()[0],
        'resolved': conn.execute('SELECT COUNT(*) FROM found_items WHERE user_id = ? AND status = "resolved"', (uid,)).fetchone()[0],
    }
    conn.close()
    return render_template('profile.html', user=user, stats=stats)

# ─── Notifications API ───────────────────────────────────────────────────────

@app.route('/notifications')
@login_required
def get_notifications():
    conn = get_db()
    notifs = conn.execute(
        'SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 20',
        (session['user_id'],)
    ).fetchall()
    unread = conn.execute(
        'SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0',
        (session['user_id'],)
    ).fetchone()[0]
    conn.close()
    return jsonify({
        'unread': unread,
        'notifications': [{
            'id': n['id'], 'type': n['type'], 'message': n['message'],
            'link': n['link'], 'is_read': n['is_read'],
            'created_at': n['created_at']
        } for n in notifs]
    })

@app.route('/notifications/mark-read', methods=['POST'])
@login_required
def mark_all_read():
    conn = get_db()
    conn.execute('UPDATE notifications SET is_read=1 WHERE user_id=?', (session['user_id'],))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

@app.route('/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_one_read(notif_id):
    conn = get_db()
    conn.execute('UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?', (notif_id, session['user_id']))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

@app.route('/google895b8fa8bed373f0.html')
def google_verify():
    return 'google-site-verification: google895b8fa8bed373f0.html'

@app.route('/robots.txt')
def robots_txt():
    content = """User-agent: *
Allow: /

Sitemap: https://pec-lost-found.onrender.com/sitemap.xml
"""
    return Response(content, mimetype='text/plain')

@app.route('/sitemap.xml')
def sitemap_xml():
    pages = ['/', '/login', '/browse']
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for page in pages:
        xml.append(f'  <url><loc>https://pec-lost-found.onrender.com{page}</loc></url>')
    xml.append('</urlset>')
    return Response('\n'.join(xml), mimetype='application/xml')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
