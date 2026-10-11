import os
from datetime import date

from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db, init_db

init_db()
# =========================
# FLASK APP
# =========================

app = Flask(__name__)

app.secret_key = "CHANGE-THIS-TO-A-LONG-RANDOM-SECRET-KEY"


# =========================
# FLASK LOGIN
# =========================

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "admin_login"


class Admin(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password


@login_manager.user_loader
def load_user(user_id):
    conn = get_db()

    admin = conn.execute(
        "SELECT * FROM admins WHERE id = ?",
        (user_id,)
    ).fetchone()

    conn.close()

    if admin:
        return Admin(
            admin["id"],
            admin["username"],
            admin["password"]
        )

    return None


# =========================
# CREATE DEFAULT ADMIN
# =========================

def create_admin():
    conn = get_db()

    existing_admin = conn.execute(
        "SELECT * FROM admins LIMIT 1"
    ).fetchone()

    if not existing_admin:
        password = generate_password_hash("MOGAdmin2026!")

        conn.execute(
            "INSERT INTO admins (username, password) VALUES (?, ?)",
            ("admin", password)
        )

        conn.commit()

        print("Default admin created.")
        print("Username: admin")
        print("Password: MOGAdmin2026!")

    conn.close()


# =========================
# PUBLIC WEBSITE
# =========================

@app.route("/")
def home():

    conn = get_db()

    gallery = conn.execute(
        "SELECT * FROM gallery ORDER BY id DESC"
    ).fetchall()

    testimonials = conn.execute(
        """
        SELECT * FROM testimonials
        WHERE approved = 1
        ORDER BY created_at DESC
        """
    ).fetchall()

    articles = conn.execute(
        """
        SELECT * FROM articles
        WHERE published = 1
        ORDER BY id DESC
        LIMIT 3
        """
    ).fetchall()

    conn.close()

    return render_template(
        "index.html",
        gallery=gallery,
        testimonials=testimonials,
        articles=articles,
        today=date.today().isoformat()
    )

# =========================
# PUBLIC ARTICLES
# =========================

@app.route("/articles")
def public_articles():

    conn = get_db()

    articles = conn.execute(
        """
        SELECT * FROM articles
        WHERE published = 1
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "articles.html",
        articles=articles
    )
# =========================
# ARTICLE DETAIL
# =========================

@app.route("/articles/<int:article_id>")
def article_detail(article_id):

    conn = get_db()

    article = conn.execute(
        """
        SELECT * FROM articles
        WHERE id = ? AND published = 1
        """,
        (article_id,)
    ).fetchone()

    conn.close()

    if not article:
        return "Article not found", 404

    return render_template(
        "article_detail.html",
        article=article
    )
# =========================
# ADMIN LOGIN
# =========================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()

        admin = conn.execute(
            "SELECT * FROM admins WHERE username = ?",
            (username,)
        ).fetchone()

        conn.close()

        if admin and check_password_hash(
            admin["password"],
            password
        ):

            user = Admin(
                admin["id"],
                admin["username"],
                admin["password"]
            )

            login_user(user)

            return redirect(url_for("admin_dashboard"))

        return "Invalid username or password"

    return render_template("admin_login.html")


# =========================
# ADMIN DASHBOARD
# =========================

@app.route("/admin")
@login_required
def admin_dashboard():
    conn = get_db()

    gallery_count = conn.execute(
        "SELECT COUNT(*) FROM gallery"
    ).fetchone()[0]

    published_count = conn.execute(
        "SELECT COUNT(*) FROM articles WHERE published = 1"
    ).fetchone()[0]

    draft_count = conn.execute(
        "SELECT COUNT(*) FROM articles WHERE published = 0"
    ).fetchone()[0]

    total_articles = conn.execute(
        "SELECT COUNT(*) FROM articles"
    ).fetchone()[0]

    testimonial_count = conn.execute(
        "SELECT COUNT(*) FROM testimonials"
    ).fetchone()[0]

    pending_testimonial_count = conn.execute(
        "SELECT COUNT(*) FROM testimonials WHERE approved = 0"
    ).fetchone()[0]

    approved_testimonial_count = conn.execute(
        "SELECT COUNT(*) FROM testimonials WHERE approved = 1"
    ).fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        gallery_count=gallery_count,
        published_count=published_count,
        draft_count=draft_count,
        total_articles=total_articles,
        testimonial_count=testimonial_count,
        pending_testimonial_count=pending_testimonial_count,
        approved_testimonial_count=approved_testimonial_count
    )

# =========================
# ADMIN GALLERY
# =========================

@app.route("/admin/gallery")
@login_required
def admin_gallery():

    conn = get_db()

    images = conn.execute(
        "SELECT * FROM gallery ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "admin_gallery.html",
        images=images
    )



# =========================
# GALLERY UPLOAD
# =========================
@app.route("/admin/gallery/upload", methods=["GET", "POST"])
@login_required
def admin_gallery_upload():

    if request.method == "POST":

        photo = request.files.get("photo")
        title = request.form.get("title")
        description = request.form.get("description")
        category = request.form.get("category", "Other")

        allowed_categories = [
            "Agbada",
            "Senator Wear",
            "Corporate Wear",
            "Native Wear",
            "Shirts",
            "Other"
        ]

        if category not in allowed_categories:
            category = "Other"

        if photo and photo.filename:

            filename = photo.filename

            upload_path = os.path.join(
                app.static_folder,
                "images",
                filename
            )

            photo.save(upload_path)

            conn = get_db()

            conn.execute(
                """
                INSERT INTO gallery
                (filename, title, description, category)
                VALUES (?, ?, ?, ?)
                """,
                (filename, title, description, category)
            )

            conn.commit()
            conn.close()

            return redirect(url_for("admin_gallery"))

    return render_template("admin_gallery_upload.html")

# =========================
# DELETE GALLERY IMAGE
# =========================

@app.route("/admin/gallery/delete/<int:image_id>", methods=["POST"])
@login_required
def delete_gallery_image(image_id):

    conn = get_db()

    image = conn.execute(
        "SELECT * FROM gallery WHERE id = ?",
        (image_id,)
    ).fetchone()

    if image:

        filename = image["filename"]

        file_path = os.path.join(
            app.static_folder,
            "images",
            filename
        )

        if os.path.exists(file_path):
            os.remove(file_path)

        conn.execute(
            "DELETE FROM gallery WHERE id = ?",
            (image_id,)
        )

        conn.commit()

    conn.close()

    return redirect(url_for("admin_gallery"))

# =========================
# EDIT GALLERY IMAGE DETAILS
# =========================

@app.route("/admin/gallery/edit/<int:image_id>", methods=["GET", "POST"])
@login_required
def edit_gallery_image(image_id):

    allowed_categories = [
        "Agbada",
        "Senator Wear",
        "Corporate Wear",
        "Native Wear",
        "Shirts",
        "Other"
    ]

    conn = get_db()

    image = conn.execute(
        "SELECT * FROM gallery WHERE id = ?",
        (image_id,)
    ).fetchone()

    if not image:
        conn.close()
        return redirect(url_for("admin_gallery"))

    if request.method == "POST":

        title = request.form.get("title")
        description = request.form.get("description")
        category = request.form.get("category", "Other")

        if category not in allowed_categories:
            category = "Other"

        conn.execute(
            """
            UPDATE gallery
            SET title = ?, description = ?, category = ?
            WHERE id = ?
            """,
            (title, description, category, image_id)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("admin_gallery"))

    conn.close()

    return render_template(
        "admin_gallery_edit.html",
        image=image,
        categories=allowed_categories
    )


# =========================
# ADMIN ARTICLES
# =========================

@app.route("/admin/articles")
@login_required
def admin_articles():

    conn = get_db()

    articles = conn.execute(
        "SELECT * FROM articles ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "admin_articles.html",
        articles=articles
    )


# =========================
# CREATE ARTICLE
# =========================

@app.route("/admin/articles/new", methods=["GET", "POST"])
@login_required
def admin_article_new():

    if request.method == "POST":

        title = request.form.get("title")
        content = request.form.get("content")

        published = 1 if request.form.get("published") else 0

        featured_image = request.files.get("featured_image")

        filename = None

        if featured_image and featured_image.filename:

            filename = featured_image.filename

            upload_path = os.path.join(
                app.static_folder,
                "images",
                filename
            )

            featured_image.save(upload_path)

        conn = get_db()

        conn.execute(
            """
            INSERT INTO articles
            (title, content, featured_image, published)
            VALUES (?, ?, ?, ?)
            """,
            (
                title,
                content,
                filename,
                published
            )
        )

        conn.commit()
        conn.close()

        return redirect(url_for("admin_articles"))

    return render_template(
        "admin_article_new.html"
    )

# =========================
# EDIT ARTICLE
# =========================

@app.route("/admin/articles/edit/<int:article_id>", methods=["GET", "POST"])
@login_required
def edit_article(article_id):

    conn = get_db()

    article = conn.execute(
        "SELECT * FROM articles WHERE id = ?",
        (article_id,)
    ).fetchone()

    if not article:
        conn.close()
        return "Article not found", 404

    if request.method == "POST":

        title = request.form.get("title")
        content = request.form.get("content")
        published = 1 if request.form.get("published") else 0

        featured_image = request.files.get("featured_image")
        filename = article["featured_image"]

        if featured_image and featured_image.filename:

            filename = featured_image.filename

            upload_path = os.path.join(
                app.static_folder,
                "images",
                filename
            )

            featured_image.save(upload_path)

        conn.execute(
            """
            UPDATE articles
            SET title = ?,
                content = ?,
                featured_image = ?,
                published = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                title,
                content,
                filename,
                published,
                article_id
            )
        )

        conn.commit()
        conn.close()

        return redirect(url_for("admin_articles"))

    conn.close()

    return render_template(
        "admin_article_edit.html",
        article=article
    )
# =========================
# DELETE ARTICLE
# =========================

@app.route("/admin/articles/delete/<int:article_id>", methods=["POST"])
@login_required
def delete_article(article_id):

    conn = get_db()

    article = conn.execute(
        "SELECT * FROM articles WHERE id = ?",
        (article_id,)
    ).fetchone()

    if article:
        conn.execute(
            "DELETE FROM articles WHERE id = ?",
            (article_id,)
        )

        conn.commit()

    conn.close()

    return redirect(url_for("admin_articles"))
# =========================
# ADMIN LOGOUT
# =========================

@app.route("/admin/logout")
@login_required
def admin_logout():

    logout_user()

    return redirect(url_for("admin_login"))


# =========================
# START APPLICATION
# =========================
def add_existing_gallery_images():

    conn = get_db()

    images = [
        "collection 1.jpg",
        "collection 2.jpg",
        "collection 3.jpg",
        "collection 4.jpg",
        "collection 5.jpg"
    ]

    for filename in images:

        existing = conn.execute(
            "SELECT * FROM gallery WHERE filename = ?",
            (filename,)
        ).fetchone()

        if not existing:

            conn.execute(
                """
                INSERT INTO gallery
                (filename, title, description)
                VALUES (?, ?, ?)
                """,
                (
                    filename,
                    filename.replace(".jpg", "").title(),
                    "MOG Stitches Collection"
                )
            )

    conn.commit()
    conn.close()

@app.route("/leave-review")
def leave_review():
    submitted = request.args.get("submitted") == "1"

    return render_template(
        "leave_review.html",
        submitted=submitted
    )


@app.route("/submit-testimonial", methods=["POST"])
def submit_testimonial():
    client_name = request.form.get("client_name", "").strip()
    review = request.form.get("review", "").strip()

    try:
        rating = int(request.form.get("rating", "5"))
    except ValueError:
        return "Invalid star rating.", 400

    if (
        not client_name
        or not review
        or len(client_name) > 100
        or len(review) > 2000
        or rating not in range(1, 6)
    ):
        return "Please enter valid review details.", 400

    conn = get_db()

    conn.execute(
        """
        INSERT INTO testimonials
        (client_name, review, rating, approved)
        VALUES (?, ?, ?, 0)
        """,
        (client_name, review, rating)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("leave_review", submitted="1"))

@app.route("/admin/testimonials")
@login_required
def admin_testimonials():
    conn = get_db()

    testimonials = conn.execute(
        "SELECT * FROM testimonials ORDER BY created_at DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "admin_testimonials.html",
        testimonials=testimonials
    )

@app.route("/admin/testimonials/approve/<int:testimonial_id>", methods=["POST"])
@login_required
def approve_testimonial(testimonial_id):
    conn = get_db()

    conn.execute(
        "UPDATE testimonials SET approved = 1 WHERE id = ?",
        (testimonial_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_testimonials"))


@app.route("/admin/testimonials/delete/<int:testimonial_id>", methods=["POST"])
@login_required
def delete_testimonial(testimonial_id):
    conn = get_db()

    conn.execute(
        "DELETE FROM testimonials WHERE id = ?",
        (testimonial_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_testimonials"))
@app.route("/admin/change-password", methods=["GET", "POST"])
@login_required
def change_password():

    message = None
    error = None

    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        conn = get_db()

        admin = conn.execute(
            "SELECT * FROM admins WHERE id = ?",
            (current_user.id,)
        ).fetchone()

        if not admin or not check_password_hash(
            admin["password"], current_password
        ):
            error = "Your current password is incorrect."

        elif len(new_password) < 8:
            error = "Your new password must be at least 8 characters."

        elif new_password != confirm_password:
            error = "The new passwords do not match."

        else:
            hashed_password = generate_password_hash(new_password)

            conn.execute(
                "UPDATE admins SET password = ? WHERE id = ?",
                (hashed_password, current_user.id)
            )
            conn.commit()
            message = "Password changed successfully."

        conn.close()

    return render_template(
        "admin_change_password.html",
        message=message,
        error=error
    )

if __name__ == "__main__":
    init_db()
    create_admin()
    add_existing_gallery_images()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )



