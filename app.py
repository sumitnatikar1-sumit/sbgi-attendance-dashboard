from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import date, timedelta

app = Flask(__name__)

DEPARTMENTS = [
    "Civil Engineering", "Computer Engineering", "Electrical Engineering",
    "Electronics & Telecommunication", "Mechanical Engineering",
    "Computer Science & Engineering (AIML)", "Electronics & Computer Science",
    "General Science"
]


def get_dashboard_data(selected_department=""):
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    if selected_department:
        cursor.execute("SELECT * FROM attendance WHERE department = ? ORDER BY id DESC", (selected_department,))
    else:
        cursor.execute("SELECT * FROM attendance ORDER BY id DESC")
    records = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM attendance")
    total_count = cursor.fetchone()[0]

    today = date.today()
    cursor.execute("SELECT COUNT(*) FROM attendance WHERE date = ?", (today.isoformat(),))
    today_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT name) FROM attendance")
    unique_students = cursor.fetchone()[0]

    cursor.execute("SELECT department, COUNT(*) FROM attendance GROUP BY department")
    dept_data = cursor.fetchall()
    dept_labels = [row[0] for row in dept_data if row[0]]
    dept_counts = [row[1] for row in dept_data if row[0]]

    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    days_elapsed_week = (today - week_start).days + 1
    days_elapsed_month = (today - month_start).days + 1

    cursor.execute("SELECT DISTINCT name FROM attendance")
    students = [row[0] for row in cursor.fetchall()]

    attendance_pct = []
    for student in students:
        cursor.execute("SELECT COUNT(DISTINCT date) FROM attendance WHERE name = ? AND date >= ?", (student, week_start.isoformat()))
        week_days = cursor.fetchone()[0]
        week_pct = round((week_days / days_elapsed_week) * 100) if days_elapsed_week else 0

        cursor.execute("SELECT COUNT(DISTINCT date) FROM attendance WHERE name = ? AND date >= ?", (student, month_start.isoformat()))
        month_days = cursor.fetchone()[0]
        month_pct = round((month_days / days_elapsed_month) * 100) if days_elapsed_month else 0

        attendance_pct.append({"name": student, "week_pct": week_pct, "month_pct": month_pct})

    conn.close()

    return {
        "records": records, "total_count": total_count, "today_count": today_count,
        "unique_students": unique_students, "dept_labels": dept_labels,
        "dept_counts": dept_counts, "attendance_pct": attendance_pct
    }


@app.route("/")
def dashboard():
    selected_department = request.args.get("department", "")
    data = get_dashboard_data(selected_department)
    return render_template("dashboard.html", departments=DEPARTMENTS, selected_department=selected_department, **data)


@app.route("/api/data")
def api_data():
    selected_department = request.args.get("department", "")
    data = get_dashboard_data(selected_department)
    return jsonify(data)


@app.route("/departments")
def departments_page():
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()
    cursor.execute("SELECT department, COUNT(*), COUNT(DISTINCT name) FROM attendance WHERE department IS NOT NULL GROUP BY department")
    dept_rows = cursor.fetchall()
    conn.close()

    dept_map = {row[0]: {"records": row[1], "students": row[2]} for row in dept_rows}
    dept_list = []
    for d in DEPARTMENTS:
        info = dept_map.get(d, {"records": 0, "students": 0})
        dept_list.append({"name": d, "records": info["records"], "students": info["students"]})

    return render_template("departments.html", dept_list=dept_list)


@app.route("/students")
def students_page():
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, department, section, COUNT(*) as cnt, MAX(date || ' ' || time) as last_seen
        FROM attendance GROUP BY name ORDER BY name
    """)
    students = cursor.fetchall()
    conn.close()
    return render_template("students.html", students=students)


@app.route("/students/<name>")
def student_detail(name):
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attendance WHERE name = ? ORDER BY id DESC", (name,))
    records = cursor.fetchall()
    conn.close()
    return render_template("student_detail.html", name=name, records=records)


@app.route("/leaderboard")
def leaderboard_page():
    data = get_dashboard_data()
    sorted_pct = sorted(data["attendance_pct"], key=lambda x: x["month_pct"], reverse=True)
    return render_template("leaderboard.html", attendance_pct=sorted_pct)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
