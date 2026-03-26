from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
import re
import os

app = Flask(__name__)
app.secret_key = "samudrakata_super_secret_2026"

# Koneksi database (mode cloud sama mode local)
def get_db():
    try:
        # kalau ada DB_HOST berarti otomatis pakai cloud
        if os.getenv('DB_HOST'):
            return pymysql.connect(
                host=os.getenv('DB_HOST'),
                port=int(os.getenv('DB_PORT', 3306)),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                database=os.getenv('DB_NAME'),
                charset='utf8mb4'
            )
        else:
            # fallback ke local
            return pymysql.connect(
                host="localhost",
                user="root",
                password="",
                database="samudrakata",
                charset='utf8mb4'
            )

    except Exception as e:
        print("DB ERROR:", e)
        return None
        
# fungsi slug berdasarkan judul narasi, jadi pas share link urlnya jadi title narasi
def make_slug(title):
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug

# rute tiap aksi yang bisa dilakuin
# bagian home (isinya stories yg udah dipublish, dengan limit 5 sebagai tampilan awal aja)
@app.route("/")
def home():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT stories.id, stories.title, stories.notes, stories.content,
        users.username, stories.created_at, stories.slug
        FROM stories
        JOIN users ON stories.author_id = users.id
        WHERE stories.status = 'published'
        ORDER BY stories.created_at DESC
        LIMIT 5
    """)
    stories = cursor.fetchall()
    conn.close()
    return render_template("index.html", stories=stories)

# bagian stories (isinya kumpulan cerita yang udah dibuat sama para pengguna webnya)
@app.route("/stories")
def stories():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT stories.id, stories.title, stories.notes, stories.content,
        users.username, stories.created_at, stories.slug
        FROM stories
        JOIN users ON stories.author_id = users.id
        WHERE stories.status = 'published'
        ORDER BY stories.created_at DESC
    """)
    stories = cursor.fetchall()
    conn.close()
    return render_template("stories.html", stories=stories)

# bagian story detail (jika cerita di klik, bakal masuk ke dalam storynya supaya bisa baca lebih lanjut)
@app.route("/story/<slug>")
def story_detail(slug):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT stories.title, stories.notes, stories.content,
        users.username, stories.created_at, stories.status
        FROM stories
        JOIN users ON stories.author_id = users.id
        WHERE stories.slug = %s
    """, (slug,))
    story = cursor.fetchone()
    conn.close()
    
    if story:
        return render_template("story.html", story=story)
    return "Cerita tidak tersedia", 404

# bagian nulis narasi (jadi nanti penulis ngetik narasinya lewat laman "write")
@app.route("/write", methods=["GET","POST"])
def write():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        title = request.form.get("title", "")
        notes = request.form.get("notes", "")
        content = request.form.get("content", "")
        slug = make_slug(title)
        author_id = session['user_id']
        
        action = request.form.get("action")
        status = "published" if action == "publish" else "draft"
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO stories (title, notes, content, slug, author_id, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (title, notes, content, slug, author_id, status))
        conn.commit()
        conn.close()
        
        if status == "published":
            return redirect(url_for("stories"))
        return redirect(url_for("dashboard"))
    
    return render_template("write.html")

# bagian dashboard (khusus pengguna akun, bisa delete, edit, atau liat status draft/published di laman ini)
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, notes, content, created_at, slug, status
        FROM stories
        WHERE author_id=%s
        ORDER BY created_at DESC
    """, (session["user_id"],))
    stories = cursor.fetchall()
    conn.close()
    
    return render_template("dashboard.html", stories=stories)

# bagian username, jadi pas diklik usernamenya bisa liat karya-karya hasil dari user tersebut
@app.route("/user/<username>")
def user_profile(username):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT stories.id, stories.title, stories.notes, stories.content,
        stories.created_at, stories.slug
        FROM stories
        JOIN users ON stories.author_id = users.id
        WHERE users.username = %s AND stories.status = 'published'
        ORDER BY stories.created_at DESC
    """, (username,))
    stories = cursor.fetchall()
    conn.close()
    
    return render_template("profile.html", username=username, stories=stories)

# bagian delete, jadi user bisa delete karya-karya yang udah dibuat
@app.route("/delete/<int:id>")
def delete_story(id):
    if "user_id" not in session:
        return redirect("/login")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM stories WHERE id=%s AND author_id=%s", 
                (id, session["user_id"]))
    conn.commit()
    conn.close()
    
    return redirect("/dashboard")

# bagian edit story, jadi user bisa edit narasi yg udah dia buat
@app.route("/edit/<int:id>", methods=["GET","POST"])
def edit_story(id):
    if "user_id" not in session:
        return redirect("/login")
    
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == "POST":
        title = request.form["title"]
        notes = request.form["notes"]
        content = request.form["content"]
        slug = make_slug(title)
        
        cursor.execute("""
            UPDATE stories
            SET title=%s, notes=%s, content=%s, slug=%s
            WHERE id=%s AND author_id=%s
        """, (title, notes, content, slug, id, session["user_id"]))
        conn.commit()
        conn.close()
        
        return redirect(f"/story/{slug}")
    
    cursor.execute("SELECT title, notes, content FROM stories WHERE id=%s AND author_id=%s", 
                (id, session["user_id"]))
    story = cursor.fetchone()
    conn.close()
    
    return render_template("edit.html", story=story, id=id)

# bagian publish narasi berdasarkan id
@app.route("/publish/<int:id>")
def publish_story(id):
    if "user_id" not in session:
        return redirect("/login")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE stories
        SET status='published'
        WHERE id=%s AND author_id=%s
    """, (id, session["user_id"]))
    conn.commit()
    conn.close()
    
    return redirect("/dashboard")

# bagian login, user yang udah logout bisa login lagi
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        conn.close()
        
        # user[0]=id, user[1]=username, user[2]=password (berdasarkan database)
        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for("home"))
        else:
            return "Username atau password salah"
    
    return render_template("login.html")

# bagian register, yang belom punya akun bikin akun dulu lewat register
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        if cursor.fetchone():
            conn.close()
            return "Username sudah dipakai"
        
        hashed_password = generate_password_hash(password)
        cursor.execute("INSERT INTO users (username, password) VALUES (%s,%s)", 
                    (username, hashed_password))
        conn.commit()
        conn.close()
        
        return redirect(url_for("login"))
    
    return render_template("register.html")

# yang punya akun bisa logout, nanti bisa login lagi
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)
