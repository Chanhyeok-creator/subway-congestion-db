from flask import Flask,render_template,request, redirect, url_for
import sqlite3

DB_PATH = "database.db"

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    return render_template("index.html")