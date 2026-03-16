from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
import re

app = Flask(__name__)
app.secret_key = "samudrakata_super_secret_2026"

# koneksi ke database
db = pymysql.connect(
    host="localhost",
    user="root",
    password="",
    database="samudrakata"
)

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

    cursor = db.cursor()

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

    return render_template("index.html", stories=stories)

# bagian stories (isinya kumpulan cerita yang udah dibuat sama para pengguna webnya)
@app.route("/stories")
def stories():

    cursor = db.cursor()

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

    return render_template("stories.html", stories=stories)


# bagian story detail (jika cerita di klik, bakal masuk ke dalam storynya supaya bisa baca lebih lanjut)
@app.route("/story/<slug>")
def story_detail(slug):

    cursor = db.cursor()

    sql = """
    SELECT stories.title, stories.notes, stories.content,
    users.username, stories.created_at, stories.status
    FROM stories
    JOIN users ON stories.author_id = users.id
    WHERE stories.slug = %s
    """

    cursor.execute(sql,(slug,))
    story = cursor.fetchone()

    if story:
        return render_template("story.html", story=story)
    else:
        return "Cerita tidak tersedia"

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

        if action == "publish":
            status = "published"
        else:
            status = "draft"

        cursor = db.cursor()

        sql = """
        INSERT INTO stories (title, notes, content, slug, author_id, status)
        VALUES (%s,%s,%s,%s,%s,%s)
        """

        cursor.execute(sql, (title, notes, content, slug, author_id, status))
        db.commit()

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

    cursor = db.cursor()

    sql = """
    SELECT id, title, notes, content, created_at, slug, status
    FROM stories
    WHERE author_id=%s
    ORDER BY created_at DESC
    """

    cursor.execute(sql,(session["user_id"],))
    stories = cursor.fetchall()

    return render_template("dashboard.html", stories=stories)


# bagian username, jadi pas diklik usernamenya bisa liat karya-karya hasil dari user tersebut
@app.route("/user/<username>")
def user_profile(username):

    cursor = db.cursor()

    sql = """
    SELECT stories.id, stories.title, stories.notes, stories.content,
    stories.created_at, stories.slug
    FROM stories
    JOIN users ON stories.author_id = users.id
    WHERE users.username = %s
    ORDER BY stories.created_at DESC
    """

    cursor.execute(sql,(username,))
    stories = cursor.fetchall()

    return render_template("profile.html", username=username, stories=stories)


# bagian delete, jadi user bisa delete karya-karya yang udah dibuat
@app.route("/delete/<int:id>")
def delete_story(id):

    if "user_id" not in session:
        return redirect("/login")

    cursor = db.cursor()

    sql = "DELETE FROM stories WHERE id=%s AND author_id=%s"
    cursor.execute(sql,(id, session["user_id"]))

    db.commit()

    return redirect("/dashboard")


# bagian edit story, jadi user bisa edit narasi yg udah dia buat
@app.route("/edit/<int:id>", methods=["GET","POST"])
def edit_story(id):

    if "user_id" not in session:
        return redirect("/login")

    cursor = db.cursor()

    if request.method == "POST":

        title = request.form["title"]
        notes = request.form["notes"]
        content = request.form["content"]

        slug = make_slug(title)

        sql = """
        UPDATE stories
        SET title=%s, notes=%s, content=%s, slug=%s
        WHERE id=%s AND author_id=%s
        """

        cursor.execute(sql,(title,notes,content,slug,id,session["user_id"]))
        db.commit()

        return redirect(f"/story/{slug}")

    sql = "SELECT title, notes, content FROM stories WHERE id=%s AND author_id=%s"
    cursor.execute(sql,(id,session["user_id"]))

    story = cursor.fetchone()

    return render_template("edit.html", story=story, id=id)

@app.route("/publish/<int:id>")
def publish_story(id):

    if "user_id" not in session:
        return redirect("/login")

    cursor = db.cursor()

    sql = """
    UPDATE stories
    SET status='published'
    WHERE id=%s AND author_id=%s
    """

    cursor.execute(sql,(id,session["user_id"]))
    db.commit()

    return redirect("/dashboard")

# bagian login, user yang udah logout bisa login lagi
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        cursor = db.cursor()

        sql = "SELECT * FROM users WHERE username=%s"
        cursor.execute(sql,(username,))
        user = cursor.fetchone()

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

        cursor = db.cursor()

        sql = "SELECT * FROM users WHERE username=%s"
        cursor.execute(sql,(username,))
        user = cursor.fetchone()

        if user:
            return "Username sudah dipakai"

        hashed_password = generate_password_hash(password)

        sql = "INSERT INTO users (username, password) VALUES (%s,%s)"
        cursor.execute(sql,(username,hashed_password))

        db.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


# yang punya akun bisa logout, nanti bisa login lagi
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)