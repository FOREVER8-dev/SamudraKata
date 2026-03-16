from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
import pymysql.cursors
import re
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'samudrakata_super_secret_2026')

# Fungsi koneksi database (pake Aiven)
def get_db():
    """Buat koneksi database baru"""
    try:
        connection = pymysql.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'samudrakata'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            ssl={'ca': None, 'cert': None, 'key': None}  # SSL untuk Aiven
        )
        return connection
    except Exception as e:
        print(f"Error koneksi database: {e}")
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
    if not conn:
        return "Error koneksi database", 500
    
    try:
        cursor = conn.cursor()
        sql = """
        SELECT stories.id, stories.title, stories.notes, stories.content,
        users.username, stories.created_at, stories.slug
        FROM stories
        JOIN users ON stories.author_id = users.id
        WHERE stories.status = 'published'
        ORDER BY stories.created_at DESC
        LIMIT 5
        """
        cursor.execute(sql)
        stories = cursor.fetchall()
    except Exception as e:
        return f"Error: {e}", 500
    finally:
        conn.close()
    
    return render_template("index.html", stories=stories)

# bagian stories (isinya kumpulan cerita yang udah dibuat sama para pengguna webnya)
@app.route("/stories")
def stories():
    conn = get_db()
    if not conn:
        return "Error koneksi database", 500
    
    try:
        cursor = conn.cursor()
        sql = """
        SELECT stories.id, stories.title, stories.notes, stories.content,
        users.username, stories.created_at, stories.slug
        FROM stories
        JOIN users ON stories.author_id = users.id
        WHERE stories.status = 'published'
        ORDER BY stories.created_at DESC
        """
        cursor.execute(sql)
        stories = cursor.fetchall()
    except Exception as e:
        return f"Error: {e}", 500
    finally:
        conn.close()
    
    return render_template("stories.html", stories=stories)


# bagian story detail (jika cerita di klik, bakal masuk ke dalam storynya supaya bisa baca lebih lanjut)
@app.route("/story/<slug>")
def story_detail(slug):
    conn = get_db()
    if not conn:
        return "Error koneksi database", 500
    
    try:
        cursor = conn.cursor()
        sql = """
        SELECT stories.title, stories.notes, stories.content,
        users.username, stories.created_at, stories.status
        FROM stories
        JOIN users ON stories.author_id = users.id
        WHERE stories.slug = %s
        """
        cursor.execute(sql, (slug,))
        story = cursor.fetchone()
    except Exception as e:
        return f"Error: {e}", 500
    finally:
        conn.close()
    
    if story:
        return render_template("story.html", story=story)
    else:
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
        
        # cek tombol yang diklik, publish atau draft
        action = request.form.get("action")
        status = "published" if action == "publish" else "draft"
        
        conn = get_db()
        if not conn:
            return "Error koneksi database", 500
        
        try:
            cursor = conn.cursor()
            sql = """
            INSERT INTO stories (title, notes, content, slug, author_id, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (title, notes, content, slug, author_id, status))
            conn.commit()
        except Exception as e:
            conn.rollback()
            return f"Error: {e}", 500
        finally:
            conn.close()
        
        # kalau publish berarti masuk ke halaman stories
        if status == "published":
            return redirect(url_for("stories"))
        # kalau draft berarti masuk ke dashboard
        return redirect(url_for("dashboard"))
    
    return render_template("write.html")

# bagian dashboard (khusus pengguna akun, bisa delete, edit, atau liat status draft/published di laman ini)
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")
    
    conn = get_db()
    if not conn:
        return "Error koneksi database", 500
    
    try:
        cursor = conn.cursor()
        sql = """
        SELECT id, title, notes, content, created_at, slug, status
        FROM stories
        WHERE author_id = %s
        ORDER BY created_at DESC
        """
        cursor.execute(sql, (session["user_id"],))
        stories = cursor.fetchall()
    except Exception as e:
        return f"Error: {e}", 500
    finally:
        conn.close()
    
    return render_template("dashboard.html", stories=stories)


# bagian username, jadi pas diklik usernamenya bisa liat karya-karya hasil dari user tersebut
@app.route("/user/<username>")
def user_profile(username):
    conn = get_db()
    if not conn:
        return "Error koneksi database", 500
    
    try:
        cursor = conn.cursor()
        sql = """
        SELECT stories.id, stories.title, stories.notes, stories.content,
        stories.created_at, stories.slug
        FROM stories
        JOIN users ON stories.author_id = users.id
        WHERE users.username = %s AND stories.status = 'published'
        ORDER BY stories.created_at DESC
        """
        cursor.execute(sql, (username,))
        stories = cursor.fetchall()
    except Exception as e:
        return f"Error: {e}", 500
    finally:
        conn.close()
    
    return render_template("profile.html", username=username, stories=stories)


# bagian delete, jadi user bisa delete karya-karya yang udah dibuat
@app.route("/delete/<int:id>")
def delete_story(id):
    if "user_id" not in session:
        return redirect("/login")
    
    conn = get_db()
    if not conn:
        return "Error koneksi database", 500
    
    try:
        cursor = conn.cursor()
        sql = "DELETE FROM stories WHERE id = %s AND author_id = %s"
        cursor.execute(sql, (id, session["user_id"]))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return f"Error: {e}", 500
    finally:
        conn.close()
    
    return redirect("/dashboard")


# bagian edit story, jadi user bisa edit narasi yg udah dia buat
@app.route("/edit/<int:id>", methods=["GET","POST"])
def edit_story(id):
    if "user_id" not in session:
        return redirect("/login")
    
    conn = get_db()
    if not conn:
        return "Error koneksi database", 500
    
    try:
        if request.method == "POST":
            title = request.form["title"]
            notes = request.form["notes"]
            content = request.form["content"]
            slug = make_slug(title)
            
            cursor = conn.cursor()
            sql = """
            UPDATE stories
            SET title = %s, notes = %s, content = %s, slug = %s
            WHERE id = %s AND author_id = %s
            """
            cursor.execute(sql, (title, notes, content, slug, id, session["user_id"]))
            conn.commit()
            
            return redirect(f"/story/{slug}")
        
        # GET request - tampilkan form edit
        cursor = conn.cursor()
        sql = "SELECT title, notes, content FROM stories WHERE id = %s AND author_id = %s"
        cursor.execute(sql, (id, session["user_id"]))
        story = cursor.fetchone()
        
        if not story:
            return "Story tidak ditemukan", 404
        
    except Exception as e:
        return f"Error: {e}", 500
    finally:
        conn.close()
    
    return render_template("edit.html", story=story, id=id)

@app.route("/publish/<int:id>")
def publish_story(id):
    if "user_id" not in session:
        return redirect("/login")
    
    conn = get_db()
    if not conn:
        return "Error koneksi database", 500
    
    try:
        cursor = conn.cursor()
        sql = """
        UPDATE stories
        SET status = 'published'
        WHERE id = %s AND author_id = %s
        """
        cursor.execute(sql, (id, session["user_id"]))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return f"Error: {e}", 500
    finally:
        conn.close()
    
    return redirect("/dashboard")

# bagian login, user yang udah logout bisa login lagi
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        conn = get_db()
        if not conn:
            return "Error koneksi database", 500
        
        try:
            cursor = conn.cursor()
            sql = "SELECT * FROM users WHERE username = %s"
            cursor.execute(sql, (username,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                return redirect(url_for("home"))
            else:
                return "Username atau password salah", 401
        except Exception as e:
            return f"Error: {e}", 500
        finally:
            conn.close()
    
    return render_template("login.html")


# bagian register, yang belom punya akun bikin akun dulu lewat register
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        conn = get_db()
        if not conn:
            return "Error koneksi database", 500
        
        try:
            cursor = conn.cursor()
            
            # Cek username udah dipake belum
            sql = "SELECT * FROM users WHERE username = %s"
            cursor.execute(sql, (username,))
            user = cursor.fetchone()
            
            if user:
                return "Username sudah dipakai", 400
            
            # Hash password
            hashed_password = generate_password_hash(password)
            
            # Simpan user baru
            sql = "INSERT INTO users (username, password) VALUES (%s, %s)"
            cursor.execute(sql, (username, hashed_password))
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            return f"Error: {e}", 500
        finally:
            conn.close()
        
        return redirect(url_for("login"))
    
    return render_template("register.html")


# yang punya akun bisa logout, nanti bisa login lagi
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# Health check endpoint buat Railway
@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv('PORT', 5000)))
