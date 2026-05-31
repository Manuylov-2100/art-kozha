# -*- coding: utf-8 -*-

import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for, session,
                   flash, g, abort)
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = "art-kozha-secret-key-change-in-production"

# База данных
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# Авторизация и роли
def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return get_db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()


@app.context_processor
def inject_globals():
    db = get_db()
    return dict(
        user=current_user(),
        now=datetime.now(),
        menu=[
            ("index", "Главная"),
            ("about", "О производстве"),
            ("catalog", "Каталог"),
            ("services", "Услуги"),
            ("news", "Новости"),
            ("blog", "Статьи"),
            ("contacts", "Контакты"),
        ],
    )


def login_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        if not current_user():
            flash("Войдите в систему, чтобы продолжить.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*a, **kw)
    return wrapped


def staff_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        u = current_user()
        if not u or u["role"] != "admin":
            abort(403)
        return view(*a, **kw)
    return wrapped


# Публичные страницы
@app.route("/")
def index():
    db = get_db()
    banners = db.execute("SELECT * FROM banners ORDER BY id").fetchall()
    news = db.execute("SELECT * FROM news ORDER BY date DESC LIMIT 3").fetchall()
    products = db.execute("SELECT * FROM products ORDER BY id LIMIT 4").fetchall()
    return render_template("index.html", banners=banners, news=news, products=products)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/catalog")
def catalog():
    db = get_db()
    category = request.args.get("category", "")
    if category:
        items = db.execute("SELECT * FROM products WHERE category = ? ORDER BY id",
                           (category,)).fetchall()
    else:
        items = db.execute("SELECT * FROM products ORDER BY id").fetchall()
    cats = db.execute("SELECT DISTINCT category FROM products ORDER BY category").fetchall()
    return render_template("catalog.html", items=items, cats=cats, active=category)


@app.route("/catalog/<int:pid>")
def product(pid):
    item = get_db().execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    if not item:
        abort(404)
    return render_template("product.html", item=item)


@app.route("/services")
def services():
    items = get_db().execute("SELECT * FROM services ORDER BY id").fetchall()
    return render_template("services.html", items=items)


@app.route("/news")
def news():
    items = get_db().execute("SELECT * FROM news ORDER BY date DESC").fetchall()
    return render_template("news.html", items=items)


@app.route("/news/<int:nid>")
def news_item(nid):
    item = get_db().execute("SELECT * FROM news WHERE id = ?", (nid,)).fetchone()
    if not item:
        abort(404)
    return render_template("news_item.html", item=item)


@app.route("/blog")
def blog():
    items = get_db().execute("SELECT * FROM articles ORDER BY date DESC").fetchall()
    return render_template("blog.html", items=items)


@app.route("/blog/<int:aid>")
def article(aid):
    item = get_db().execute("SELECT * FROM articles WHERE id = ?", (aid,)).fetchone()
    if not item:
        abort(404)
    return render_template("article.html", item=item)


@app.route("/contacts", methods=["GET", "POST"])
def contacts():
    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO feedback (name, email, phone, message, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (request.form.get("name", "").strip(),
             request.form.get("email", "").strip(),
             request.form.get("phone", "").strip(),
             request.form.get("message", "").strip(),
             datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
        db.commit()
        flash("Сообщение отправлено. Менеджер свяжется с вами.", "success")
        return redirect(url_for("contacts"))
    return render_template("contacts.html")


# Поиск по сайту
@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    results = []
    if q:
        like = f"%{q}%"
        db = get_db()
        for row in db.execute(
            "SELECT title, description AS text, 'catalog' AS kind, id FROM products "
            "WHERE title LIKE ? OR description LIKE ?", (like, like)):
            results.append(dict(row))
        for row in db.execute(
            "SELECT title, summary AS text, 'news' AS kind, id FROM news "
            "WHERE title LIKE ? OR body LIKE ?", (like, like)):
            results.append(dict(row))
        for row in db.execute(
            "SELECT title, summary AS text, 'blog' AS kind, id FROM articles "
            "WHERE title LIKE ? OR body LIKE ?", (like, like)):
            results.append(dict(row))
        for row in db.execute(
            "SELECT title, description AS text, 'services' AS kind, id FROM services "
            "WHERE title LIKE ? OR description LIKE ?", (like, like)):
            results.append(dict(row))
    return render_template("search.html", q=q, results=results)


# Карта сайта
@app.route("/sitemap")
def sitemap():
    db = get_db()
    return render_template(
        "sitemap.html",
        products=db.execute("SELECT id, title FROM products ORDER BY id").fetchall(),
        news=db.execute("SELECT id, title FROM news ORDER BY date DESC").fetchall(),
        articles=db.execute("SELECT id, title FROM articles ORDER BY date DESC").fetchall(),
    )


# Учётные записи: регистрация, вход, выход, личный кабинет
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        db = get_db()
        if not username or not password:
            flash("Логин и пароль обязательны.", "danger")
        elif db.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
            flash("Пользователь с таким логином уже существует.", "danger")
        else:
            db.execute(
                "INSERT INTO users (username, password_hash, role, full_name, email, created_at) "
                "VALUES (?, ?, 'client', ?, ?, ?)",
                (username, generate_password_hash(password), full_name, email,
                 datetime.now().strftime("%Y-%m-%d %H:%M")),
            )
            db.commit()
            flash("Учётная запись создана. Теперь войдите.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        u = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if u and check_password_hash(u["password_hash"], password):
            session["user_id"] = u["id"]
            flash(f"Добро пожаловать, {u['full_name'] or u['username']}!", "success")
            nxt = request.args.get("next") or url_for("account")
            return redirect(nxt)
        flash("Неверный логин или пароль.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Вы вышли из системы.", "info")
    return redirect(url_for("index"))


@app.route("/account")
@login_required
def account():
    u = current_user()
    msgs = get_db().execute(
        "SELECT * FROM messages WHERE user_id = ? ORDER BY created_at DESC", (u["id"],)
    ).fetchall()
    return render_template("account.html", msgs=msgs)


# Система обмена сообщениями
@app.route("/messages", methods=["GET", "POST"])
@login_required
def messages():
    db = get_db()
    u = current_user()
    if request.method == "POST":
        db.execute(
            "INSERT INTO messages (user_id, subject, body, is_from_staff, created_at) "
            "VALUES (?, ?, ?, 0, ?)",
            (u["id"], request.form.get("subject", "").strip(),
             request.form.get("body", "").strip(),
             datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
        db.commit()
        flash("Сообщение отправлено менеджеру.", "success")
        return redirect(url_for("messages"))
    thread = db.execute(
        "SELECT * FROM messages WHERE user_id = ? ORDER BY created_at", (u["id"],)
    ).fetchall()
    return render_template("messages.html", thread=thread)


# Панель сотрудника (роль admin): создание пользователей, обращения
@app.route("/admin", methods=["GET", "POST"])
@staff_required
def admin():
    db = get_db()
    if request.method == "POST" and request.form.get("action") == "create_user":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "client")
        if username and password and not db.execute(
                "SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
            db.execute(
                "INSERT INTO users (username, password_hash, role, full_name, email, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (username, generate_password_hash(password), role,
                 request.form.get("full_name", "").strip(),
                 request.form.get("email", "").strip(),
                 datetime.now().strftime("%Y-%m-%d %H:%M")),
            )
            db.commit()
            flash(f"Пользователь «{username}» создан сотрудником.", "success")
        else:
            flash("Не удалось создать пользователя (проверьте данные/логин).", "danger")
        return redirect(url_for("admin"))

    users = db.execute("SELECT * FROM users ORDER BY id").fetchall()
    feedback = db.execute("SELECT * FROM feedback ORDER BY created_at DESC").fetchall()
    msgs = db.execute(
        "SELECT m.*, u.username FROM messages m JOIN users u ON u.id = m.user_id "
        "ORDER BY m.created_at DESC").fetchall()
    return render_template("admin.html", users=users, feedback=feedback, msgs=msgs)


# Страница 404 и перенаправление на неё
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        import init_db
        init_db.seed()
    app.run(debug=True, port=5000)
