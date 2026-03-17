from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os, cloudinary, cloudinary.uploader
from functools import wraps

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
            sid TEXT UNIQUE NOT NULL, contact TEXT NOT NULL,
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
    ''')
    conn.commit()
    conn.close()

init_db()

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
            flash('Please log in.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if 'user_id' not in session:
        return None
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    return user

DEPARTMENTS = ['CSE','ECE','EE','ME','CE','AE','IT','MCA','MBA','PHY','CHEM','MATH']
CATEGORIES = ['Electronics','Keys','Wallet/Purse','ID Card','Books/Notes','Clothing','Accessories','Bag/Backpack','Sports Equipment','Other']
LOCATIONS = ['CC Block','OAT','Library','Sidhartha Hall','Canteen','Sports Complex','Main Gate','Hostel Area','Labs','Classroom','Parking','Other']

@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'user_id' in session else url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        sid = request.form.get('sid','').strip()
        password = request.form.get('password','').strip()
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE sid = ?', (sid,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['full_name']
            flash(f'Welcome back, {user["full_name"].split()[0]}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid Student ID or password.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        full_name = request.form.get('full_name','').strip()
        department = request.form.get('department','').strip()
        sid = request.form.get('sid','').strip()
        contact = request.form.get('contact','').strip()
        hosteler_status = request.form.get('hosteler_status','Day Scholar')
        hostel_name = request.form.get('hostel_name','').strip() if hosteler_status == 'Hosteler' else None
        password = request.form.get('password','')
        confirm_password = request.form.get('confirm_password','')
        if not all([full_name, department, sid, contact, password]):
            flash('All fields are required.', 'error')
            return render_template('register.html', departments=DEPARTMENTS)
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html', departments=DEPARTMENTS)
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('register.html', departments=DEPARTMENTS)
        conn = get_db()
        if conn.execute('SELECT id FROM users WHERE sid = ?', (sid,)).fetchone():
            conn.close()
            flash('Student ID already registered.', 'error')
            return render_template('register.html', departments=DEPARTMENTS)
        conn.execute('INSERT INTO users (full_name,department,sid,contact,hosteler_status,hostel_name,password_hash) VALUES (?,?,?,?,?,?,?)',
            (full_name, department, sid, contact, hosteler_status, hostel_name, generate_password_hash(password)))
        conn.commit()
        conn.close()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', departments=DEPARTMENTS)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

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

@app.route('/browse')
@login_required
def browse():
    conn = get_db()
    category = request.args.get('category','')
    search = request.args.get('search','')
    lq = 'SELECT l.*, u.full_name, u.department FROM lost_items l JOIN users u ON l.user_id = u.id WHERE l.status = "open"'
    fq = 'SELECT f.*, u.full_name, u.department FROM found_items f JOIN users u ON f.user_id = u.id WHERE f.status = "open"'
    params = []
    if category:
        lq += ' AND l.category = ?'; fq += ' AND f.category = ?'; params.append(category)
    if search:
        lq += ' AND (l.item_name LIKE ? OR l.location LIKE ?)'; fq += ' AND (f.brief_description LIKE ? OR f.location LIKE ?)'; params.extend([f'%{search}%', f'%{search}%'])
    lost_items = conn.execute(lq + ' ORDER BY l.created_at DESC', params).fetchall()
    found_items = conn.execute(fq + ' ORDER BY f.created_at DESC', params).fetchall()
    conn.close()
    return render_template('browse.html', lost_items=lost_items, found_items=found_items,
                           categories=CATEGORIES, selected_category=category, search=search)

@app.route('/post-lost', methods=['GET','POST'])
@login_required
def post_lost():
    if request.method == 'POST':
        image_url = None
        if 'image' in request.files:
            f = request.files['image']
            if f and f.filename and allowed_file(f.filename):
                image_url = upload_image(f)
        conn = get_db()
        conn.execute('INSERT INTO lost_items (user_id,item_name,category,color,location,image_path,date_lost,description) VALUES (?,?,?,?,?,?,?,?)',
            (session['user_id'], request.form.get('item_name','').strip(), request.form.get('category','').strip(),
             request.form.get('color','').strip(), request.form.get('location','').strip(),
             image_url, request.form.get('date_lost','').strip(), request.form.get('description','').strip()))
        conn.commit(); conn.close()
        flash('Lost item posted successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('post_lost.html', categories=CATEGORIES, locations=LOCATIONS)

@app.route('/post-found', methods=['GET','POST'])
@login_required
def post_found():
    if request.method == 'POST':
        conn = get_db()
        conn.execute('INSERT INTO found_items (user_id,brief_description,category,location,date_found) VALUES (?,?,?,?,?)',
            (session['user_id'], request.form.get('brief_description','').strip(),
             request.form.get('category','').strip(), request.form.get('location','').strip(),
             request.form.get('date_found','').strip()))
        conn.commit(); conn.close()
        flash('Found item posted!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('post_found.html', categories=CATEGORIES, locations=LOCATIONS)

@app.route('/claim/<int:found_item_id>', methods=['GET','POST'])
@login_required
def claim_item(found_item_id):
    conn = get_db()
    found_item = conn.execute('SELECT f.*, u.full_name FROM found_items f JOIN users u ON f.user_id = u.id WHERE f.id = ?', (found_item_id,)).fetchone()
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
        conn.commit(); conn.close()
        flash('Claim submitted! The finder will review your description.', 'success')
        return redirect(url_for('browse'))
    conn.close()
    return render_template('claim.html', found_item=found_item, existing_claim=existing_claim)

@app.route('/resolve-claim/<int:claim_id>/<action>')
@login_required
def resolve_claim(claim_id, action):
    conn = get_db()
    claim = conn.execute('SELECT c.*, f.user_id as finder_id FROM claims c JOIN found_items f ON c.found_item_id = f.id WHERE c.id = ?', (claim_id,)).fetchone()
    if not claim or claim['finder_id'] != session['user_id']:
        conn.close(); flash('Unauthorized.', 'error'); return redirect(url_for('dashboard'))
    if action == 'approve':
        conn.execute('UPDATE claims SET status = "approved" WHERE id = ?', (claim_id,))
        conn.execute('UPDATE found_items SET status = "resolved" WHERE id = ?', (claim['found_item_id'],))
        conn.execute('UPDATE claims SET status = "rejected" WHERE found_item_id = ? AND id != ?', (claim['found_item_id'], claim_id))
        flash('Claim approved! Item marked as returned.', 'success')
    else:
        conn.execute('UPDATE claims SET status = "rejected" WHERE id = ?', (claim_id,))
        flash('Claim rejected.', 'info')
    conn.commit(); conn.close()
    return redirect(url_for('dashboard'))

@app.route('/delete-lost/<int:item_id>')
@login_required
def delete_lost(item_id):
    conn = get_db()
    if conn.execute('SELECT id FROM lost_items WHERE id = ? AND user_id = ?', (item_id, session['user_id'])).fetchone():
        conn.execute('DELETE FROM lost_items WHERE id = ?', (item_id,))
        conn.commit(); flash('Post deleted.', 'info')
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/delete-found/<int:item_id>')
@login_required
def delete_found(item_id):
    conn = get_db()
    if conn.execute('SELECT id FROM found_items WHERE id = ? AND user_id = ?', (item_id, session['user_id'])).fetchone():
        conn.execute('DELETE FROM claims WHERE found_item_id = ?', (item_id,))
        conn.execute('DELETE FROM found_items WHERE id = ?', (item_id,))
        conn.commit(); flash('Post deleted.', 'info')
    conn.close()
    return redirect(url_for('dashboard'))

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
