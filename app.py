from flask import Flask, render_template_string, request, redirect, session, flash, send_file
import os, json, hashlib
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Detect Render environment
IS_RENDER = 'RENDER' in os.environ or os.environ.get('RENDER_EXTERNAL_URL')

# Permanent storage on Render
PERSIST_DIR = '/var/data' if IS_RENDER else 'data'
UPLOAD_DIR = os.path.join(PERSIST_DIR, 'uploads')
ADMIN_FILE = os.path.join(PERSIST_DIR, 'admin_data.json')

app.config['UPLOAD_FOLDER'] = UPLOAD_DIR
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'zip'}

# ---------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_dirs():
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(PERSIST_DIR, exist_ok=True)

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def load_admin_data():
    if os.path.exists(ADMIN_FILE):
        try:
            with open(ADMIN_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    default = {'username': 'admin', 'password': hash_password('admin123')}
    save_admin_data(default)
    return default

def save_admin_data(data):
    with open(ADMIN_FILE, 'w') as f:
        json.dump(data, f)

# ---------------------------------------------------------------------
# HTML Template (simplified but clean)
# ---------------------------------------------------------------------
TEMPLATE = '''
<!DOCTYPE html>
<html><head>
<title>Secure Upload</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body{background:#0f0f0f;color:#e0e0e0;font-family:sans-serif;margin:0;padding:0}
.container{max-width:800px;margin:auto;padding:20px}
.card{background:#1a1a1a;padding:20px;border-radius:10px;margin-top:20px}
.btn{display:inline-block;padding:10px 20px;border:1px solid #444;border-radius:6px;text-decoration:none;color:#fff;background:#2d2d2d}
.btn-primary{background:#007bff}
.flash{padding:10px;margin:10px 0;border-radius:5px}
.flash.success{background:#133d13;color:#8bc34a}
.flash.error{background:#3d1313;color:#ff6b6b}
</style>
</head>
<body>
<div class="container">
<h2>📁 Secure Upload</h2>

{% with messages = get_flashed_messages(with_categories=true) %}
  {% for cat,msg in messages %}
    <div class="flash {{cat}}">{{msg}}</div>
  {% endfor %}
{% endwith %}

{% if not session.get('admin') and request.path == '/' %}
<div class="card">
<h3>Upload a File or Text</h3>
<form method="POST" action="/upload" enctype="multipart/form-data">
<input type="file" name="file"><br><br>
<textarea name="text_content" rows="4" style="width:100%" placeholder="Enter text..."></textarea><br><br>
<button type="submit" class="btn btn-primary">Upload</button>
</form>
<a href="/admin/login" class="btn" style="margin-top:10px;display:block;text-align:center">Admin Login</a>
</div>

{% elif request.path == '/admin/login' %}
<div class="card">
<h3>Admin Login</h3>
<form method="POST">
<input name="username" placeholder="Username" required><br><br>
<input type="password" name="password" placeholder="Password" required><br><br>
<button type="submit" class="btn btn-primary">Login</button>
</form>
<a href="/" class="btn" style="margin-top:10px;display:block;text-align:center">Back</a>
</div>

{% elif session.get('admin') and request.path == '/admin/dashboard' %}
<div class="card">
<h3>Admin Dashboard</h3>
<a href="/admin/change-password" class="btn">Change Password</a>
<a href="/admin/logout" class="btn">Logout</a>
<hr>
<h4>Uploaded Files:</h4>
{% if files %}
<ul>
{% for f in files %}
<li>{{f.name}} ({{f.size}} bytes)
<a href="/admin/download/{{f.name}}" class="btn">📥</a>
<a href="/admin/delete/{{f.name}}" class="btn">🗑️</a></li>
{% endfor %}
</ul>
{% else %}
<p>No files uploaded</p>
{% endif %}
</div>

{% elif session.get('admin') and request.path == '/admin/change-password' %}
<div class="card">
<h3>Change Password</h3>
<form method="POST">
<input type="password" name="current_password" placeholder="Current" required><br><br>
<input type="password" name="new_password" placeholder="New" required><br><br>
<input type="password" name="confirm_password" placeholder="Confirm" required><br><br>
<button type="submit" class="btn btn-primary">Update</button>
</form>
<a href="/admin/dashboard" class="btn">Back</a>
</div>
{% endif %}
</div>
</body></html>
'''

# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------
@app.route('/')
def index():
    return render_template_string(TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload():
    ensure_dirs()
    f = request.files.get('file')
    txt = request.form.get('text_content', '').strip()

    if f and f.filename and allowed_file(f.filename):
        name = datetime.now().strftime('%Y%m%d_%H%M%S_') + secure_filename(f.filename)
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], name))
        flash('File uploaded successfully!', 'success')
    elif txt:
        name = f"text_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(os.path.join(app.config['UPLOAD_FOLDER'], name), 'w', encoding='utf-8') as out:
            out.write(txt)
        flash('Text saved successfully!', 'success')
    else:
        flash('No file or text provided!', 'error')
    return redirect('/')

@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if session.get('admin'):
        return redirect('/admin/dashboard')
    if request.method == 'POST':
        data = load_admin_data()
        if request.form['username'] == data['username'] and hash_password(request.form['password']) == data['password']:
            session['admin'] = True
            flash('Login successful!', 'success')
            return redirect('/admin/dashboard')
        flash('Invalid credentials!', 'error')
    return render_template_string(TEMPLATE)

@app.route('/admin/dashboard')
def dashboard():
    if not session.get('admin'): return redirect('/admin/login')
    ensure_dirs()
    files = []
    for f in os.listdir(app.config['UPLOAD_FOLDER']):
        path = os.path.join(app.config['UPLOAD_FOLDER'], f)
        if os.path.isfile(path):
            stat = os.stat(path)
            files.append({'name': f, 'size': stat.st_size})
    return render_template_string(TEMPLATE, files=files)

@app.route('/admin/download/<filename>')
def download(filename):
    if not session.get('admin'): return redirect('/admin/login')
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    return send_file(path, as_attachment=True) if os.path.exists(path) else redirect('/admin/dashboard')

@app.route('/admin/delete/<filename>')
def delete(filename):
    if not session.get('admin'): return redirect('/admin/login')
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(path): os.remove(path)
    flash('File deleted!', 'success')
    return redirect('/admin/dashboard')

@app.route('/admin/change-password', methods=['GET','POST'])
def change_pw():
    if not session.get('admin'): return redirect('/admin/login')
    if request.method == 'POST':
        data = load_admin_data()
        cur = request.form['current_password']
        new = request.form['new_password']
        conf = request.form['confirm_password']
        if hash_password(cur) != data['password']:
            flash('Incorrect current password!', 'error')
        elif new != conf:
            flash('Passwords do not match!', 'error')
        else:
            data['password'] = hash_password(new)
            save_admin_data(data)
            flash('Password updated!', 'success')
            return redirect('/admin/dashboard')
    return render_template_string(TEMPLATE)

@app.route('/admin/logout')
def logout():
    session.pop('admin', None)
    flash('Logged out!', 'success')
    return redirect('/')

# ---------------------------------------------------------------------
# Entry Point for Render
# ---------------------------------------------------------------------
if __name__ == '__main__':
    ensure_dirs()
    load_admin_data()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
