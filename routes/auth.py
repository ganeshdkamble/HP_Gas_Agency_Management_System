from flask import Blueprint, render_template, request, redirect, session
from db import get_connection

auth = Blueprint("auth", __name__)


@auth.route("/")
def login():
    return render_template("login.html")


@auth.route("/login", methods=["POST"])
def check_login():

    username = request.form["username"]
    password = request.form["password"]

    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM admin WHERE username=%s AND password=%s"
    cursor.execute(query, (username, password))

    admin = cursor.fetchone()

    if admin:
        session["admin"] = username
        return redirect("/dashboard")

    return "Invalid Username or Password"