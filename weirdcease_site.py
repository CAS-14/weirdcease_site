from flask import request, redirect, url_for, send_file, g, flash, session
from werkzeug.security import check_password_hash
import json
from datetime import datetime
import re
import random

import tools

CENSORS = {}
with open(tools.util("censors.json"), "r") as f:
    CENSORS = json.load(f)

DB_ROUTES = [
    "main.blog",
    "main.blogpost",
    "main.create_comment",
    "main.create_post",
    "main.gallery",
    "main.gallery_image"
]

bp = tools.MyBlueprint("main", "weirdcease_site", host="indev.act25.com", db="main", db_routes=DB_ROUTES)

# these dont hide anything important right now so even though i accidentally made them public it doesn't really matter
ADMIN_USER = "cas"
ADMIN_HASH = "pbkdf2:sha256:260000$Je4bs5nrC66GvmoX$fbb5ddea1d6e336c6f4dcb2e68acab19fe4564175df63a18710d77e359f1789a"

@bp.route("/")
@bp.route("/home")
def home():
    mobile = False
    
    agent = request.headers.get('User-Agent')
    for a in ["iphone", "android", "blackberry", "mobile"]:
        if a in agent.lower():
            mobile = True

    return bp.render("wchome.html", mobile=mobile)

@bp.route("/about")
def about():
    return bp.render("about.html")

@bp.route("/blog")
def blog():
    posts = g.cur.execute(
        "SELECT id, title, time, comments FROM blogposts ORDER BY id DESC;"
    ).fetchall()

    return bp.render("blog.html", posts=posts)

@bp.route("/blog/post/<post_id>")
def blogpost(post_id):
    post = g.cur.execute(
        "SELECT title, time, body, comments, id FROM blogposts WHERE id = ?;", 
        (post_id,)
    ).fetchone()
    
    if post:
        comments = g.cur.execute(
            "SELECT time, author, body FROM comments WHERE parent = ? ORDER BY id DESC;", 
            (post_id,)
        ).fetchall()

        return bp.render("blogpost.html", post=post, comments=comments)

    else:
        return bp.render("blognf.html", post_id=post_id)

@bp.route("/blog/post/<parent_post>/create_comment", methods=["POST"])
def create_comment(parent_post):
    author = request.form.get("author")
    if not author: author = "anonymous"
    body = request.form.get("body")
    
    if body:
        for word in CENSORS:
            body = re.sub(word, "*" * len(word), body, flags=re.IGNORECASE)

        time = int(datetime.timestamp(datetime.now()))

        try:
            g.cur.execute(
                "INSERT INTO comments (parent, author, body, time) VALUES (?, ?, ?, ?);",
                (parent_post, author, body, time)
            )

        except:
            pass

        else:
            g.cur.execute(
                "UPDATE blogposts SET comments = comments + 1 WHERE id = ?;",
                (parent_post,)
            )

    return redirect(url_for("main.blogpost", post_id=parent_post))

@bp.route("/blog/create_post", methods=["POST"])
def create_post():
    token = request.headers.get("token")

    ADMIN_TOKEN = tools.SECRETS["blog_post_token"]

    if token == ADMIN_TOKEN:
        title = request.headers.get("title")
        body = request.headers.get("body")
        
        time = int(datetime.timestamp(datetime.now()))

        g.cur.execute(
            "INSERT INTO blogposts (title, body, time, comments) VALUES (?, ?, ?, ?);",
            (title, body, time, 0)
        )
    
        return "Post created!"

    else:
        return "Authentication failed!"

@bp.route("/projects")
def projects():
    return bp.render("projects.html")

@bp.route("/projects/gallery")
def gallery():
    images = g.cur.execute(
        "SELECT id, title, filename FROM artwork;"
    ).fetchall()
    random.shuffle(images)

    return bp.render("gallery.html", images=images)

@bp.route("/projects/gallery/<image_id>")
def gallery_image(image_id):
    image = g.cur.execute(
        "SELECT title, filename, description FROM artwork WHERE id = ?;",
        (image_id,)
    ).fetchone()
    
    if not image:
        return bp.render("wcerror.html", code="404")

    return bp.render("galleryimg.html", image=image)

@bp.route("/projects/webhook")
def webhook_sender():
    return bp.render("webhook_sender.html")

@bp.route("/force404")
def force404():
    return bp.render("wcerror.html", code="404", message="Balls")

@bp.route("/keybase.txt")
def keybase():
    return send_file("static/keybase.txt")

@bp.route("/shhh")
@bp.route("/login")
def login():
    return bp.render("secretlogin.html")

@bp.route("/login_handler", methods=["POST"])
def login_handler():
    username = request.form.get("username")
    password = request.form.get("password")

    if username == ADMIN_USER and password and check_password_hash(ADMIN_HASH, password):
        session.clear()
        session["user_id"] = "cas"

        return redirect(url_for("main.secret"))
    
    flash("Incorrect credentials.")
    return redirect(url_for("main.login"))

@bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("main.login"))

@bp.route("/secret")
def secret():
    if "user_id" in session and session["user_id"] == "cas":
        return bp.render("secret.html")
    
    flash("You must login to view that page.")
    return redirect(url_for("main.login"))
