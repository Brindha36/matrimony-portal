import os
import io
import csv
import hashlib
from typing import List, Optional
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, Response
)
from werkzeug.utils import secure_filename
import mysql.connector
from PIL import Image
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

app = Flask(__name__)
app.secret_key = "matrimony_enterprise_portal_secret_key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.environ["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", 4000)),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "test"),
    "charset": "utf8mb4",
    "use_unicode": True,
    "ssl_disabled": False,
    "ssl_verify_cert": False
}

def get_db_connection():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SET NAMES utf8mb4;")
    cursor.execute("SET CHARACTER SET utf8mb4;")
    cursor.execute("SET character_set_connection=utf8mb4;")
    cursor.close()
    return conn

def generate_next_batch_id(cursor) -> str:
    cursor.execute("SELECT COUNT(*) AS total FROM uploads_log")
    next_num = cursor.fetchone()["total"] + 1
    return f"SMMOC{next_num:02d}"

class MatrimonyProfile(BaseModel):
    profile_id: str = Field(description="Profile ID, e.g., 'B-6429', 'G-6435'")
    name: str = Field(description="Full name in English or Tamil")
    dob: Optional[str] = Field(None, description="Date of birth")
    star_rasi: Optional[str] = Field(None, description="Star, Rasi, Gothram in English or Tamil")
    height_complexion: Optional[str] = Field(None, description="Height and skin tone")
    education: Optional[str] = Field(None, description="Educational qualifications")
    job_and_company: Optional[str] = Field(None, description="Occupation and workplace")
    salary: Optional[str] = Field(None, description="Salary or income details")
    native_place: Optional[str] = Field(None, description="Native place or living town")
    father_details: Optional[str] = Field(None, description="Father's job or pension")
    property_details: Optional[str] = Field(None, description="Owned house, flat details")
    expectation: Optional[str] = Field(None, description="Partner expectation")
    contact_person: Optional[str] = Field(None, description="Contact person and address")
    phone_numbers: Optional[str] = Field(None, description="Phone numbers")
    email: Optional[str] = Field(None, description="Email ID")

class ProfilesContainer(BaseModel):
    profiles: List[MatrimonyProfile]

def extract_profiles_from_image(image_path: str) -> List[dict]:
    client = genai.Client()
    img = Image.open(image_path)
    
    prompt = (
        "Extract every distinct matrimony profile card visible on this page. "
        "Extract Tamil and English text exactly as printed without transliterating."
    )
    
    # Updated to gemini-3.8-flash
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[img, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ProfilesContainer,
        ),
    )
    parsed = ProfilesContainer.model_validate_json(response.text)
    return [p.model_dump() for p in parsed.profiles]

@app.route("/", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, hashed_pw))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user:
                session["user"] = user["username"]
                return redirect(url_for("dashboard"))
            else:
                flash("Invalid Username or Password!", "danger")
        except Exception as e:
            flash(f"Database error: {str(e)}", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/dashboard", methods=["GET"])
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    edu_filter = request.args.get("edu_filter", "").strip()
    search = request.args.get("search", "").strip()

    cursor.execute("SELECT COUNT(*) AS total FROM profiles")
    total_profiles = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS today_count FROM profiles WHERE DATE(created_at) = CURDATE()")
    today_count = cursor.fetchone()["today_count"]

    cursor.execute("SELECT COUNT(*) AS month_count FROM profiles WHERE MONTH(created_at) = MONTH(CURDATE()) AND YEAR(created_at) = YEAR(CURDATE())")
    month_count = cursor.fetchone()["month_count"]

    cursor.execute("SELECT COUNT(*) AS verified_phones FROM profiles WHERE phone_numbers IS NOT NULL AND TRIM(phone_numbers) != ''")
    verified_phones = cursor.fetchone()["verified_phones"]

    cursor.execute("""
        SELECT COUNT(*) AS salaried_count FROM profiles 
        WHERE salary IS NOT NULL AND (
            LOWER(salary) LIKE '%lpa%' OR 
            LOWER(salary) LIKE '%lakh%' OR 
            LOWER(salary) LIKE '%pm%' OR 
            salary REGEXP '[0-9]{5,}'
        )
    """)
    salaried_count = cursor.fetchone()["salaried_count"]

    cursor.execute("SELECT COUNT(*) AS total_batches, COALESCE(SUM(profiles_extracted), 0) AS total_ai_scanned FROM uploads_log")
    batch_stats = cursor.fetchone()

    cursor.execute("""
        SELECT 
            CASE 
                WHEN LOWER(education) LIKE '%b.e%' OR LOWER(education) LIKE '%b.tech%' OR LOWER(education) LIKE '%m.e%' THEN 'Engineering'
                WHEN LOWER(education) LIKE '%mba%' OR LOWER(education) LIKE '%m.com%' OR LOWER(education) LIKE '%b.com%' THEN 'Commerce / Mgmt'
                WHEN LOWER(education) LIKE '%mbbs%' OR LOWER(education) LIKE '%bds%' OR LOWER(education) LIKE '%md%' THEN 'Medical'
                WHEN LOWER(education) LIKE '%m.sc%' OR LOWER(education) LIKE '%b.sc%' OR LOWER(education) LIKE '%mca%' THEN 'Science & IT'
                WHEN LOWER(education) LIKE '%arts%' OR LOWER(education) LIKE '%b.a%' OR LOWER(education) LIKE '%m.a%' THEN 'Arts & Humanities'
                ELSE 'Other Degrees'
            END AS degree_category,
            COUNT(*) AS count
        FROM profiles
        WHERE education IS NOT NULL AND education != ''
        GROUP BY degree_category
        ORDER BY count DESC
    """)
    edu_data = cursor.fetchall()

    cursor.execute("""
        SELECT COALESCE(NULLIF(TRIM(native_place), ''), 'Not Specified') AS region, COUNT(*) AS count
        FROM profiles
        GROUP BY region
        ORDER BY count DESC
        LIMIT 6
    """)
    native_data = cursor.fetchall()

    query = "SELECT * FROM profiles WHERE 1=1"
    params = []

    if date_from:
        query += " AND DATE(created_at) >= %s"
        params.append(date_from)
    if date_to:
        query += " AND DATE(created_at) <= %s"
        params.append(date_to)
    if edu_filter:
        query += " AND LOWER(education) LIKE %s"
        params.append(f"%{edu_filter.lower()}%")
    if search:
        query += " AND (LOWER(name) LIKE %s OR LOWER(profile_id) LIKE %s OR phone_numbers LIKE %s OR LOWER(batch_id) LIKE %s)"
        params.extend([f"%{search.lower()}%", f"%{search.lower()}%", f"%{search.lower()}%", f"%{search.lower()}%"])

    query += " ORDER BY id DESC"
    cursor.execute(query, tuple(params))
    recent_profiles = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "dashboard.html",
        username=session["user"],
        total_profiles=total_profiles,
        today_count=today_count,
        month_count=month_count,
        verified_phones=verified_phones,
        salaried_count=salaried_count,
        total_batches=batch_stats["total_batches"],
        total_ai_scanned=batch_stats["total_ai_scanned"],
        pie_labels=[row["degree_category"] for row in edu_data],
        pie_counts=[row["count"] for row in edu_data],
        bar_labels=[row["region"] for row in native_data],
        bar_counts=[row["count"] for row in native_data],
        recent_profiles=recent_profiles,
        date_from=date_from,
        date_to=date_to,
        edu_filter=edu_filter,
        search=search
    )

@app.route("/upload", methods=["GET"])
def upload_page():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    current_batch_id = generate_next_batch_id(cursor)

    cursor.execute("SELECT * FROM profiles ORDER BY id DESC")
    db_profiles = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template(
        "upload.html",
        username=session["user"],
        db_profiles=db_profiles,
        current_batch_id=current_batch_id
    )

@app.route("/extract_profiles_ajax", methods=["POST"])
def extract_profiles_ajax():
    if "user" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    file = request.files.get("photo")
    if not file or file.filename == "":
        return jsonify({"success": False, "error": "No file uploaded"}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(file_path)

    try:
        extracted = extract_profiles_from_image(file_path)
        return jsonify({
            "success": True, 
            "profiles": extracted,
            "filename": filename,
            "count": len(extracted)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@app.route("/save_profiles", methods=["POST"])
def save_profiles():
    if "user" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    data = request.get_json()
    profiles_to_save = data.get("profiles", [])
    batch_id = data.get("batch_id")

    if not profiles_to_save:
        return jsonify({"success": False, "error": "No profiles provided"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if not batch_id:
        batch_id = generate_next_batch_id(cursor)

    insert_query = """
        INSERT INTO profiles (
            batch_id, profile_id, name, dob, star_rasi, height_complexion,
            education, job_and_company, salary, native_place,
            father_details, property_details, expectation,
            contact_person, phone_numbers, email
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    for p in profiles_to_save:
        cursor.execute(insert_query, (
            batch_id,
            p.get("profile_id"),
            p.get("name"),
            p.get("dob"),
            p.get("star_rasi"),
            p.get("height_complexion"),
            p.get("education"),
            p.get("job_and_company"),
            p.get("salary"),
            p.get("native_place"),
            p.get("father_details"),
            p.get("property_details"),
            p.get("expectation"),
            p.get("contact_person"),
            p.get("phone_numbers"),
            p.get("email")
        ))

    cursor.execute(
        "INSERT INTO uploads_log (batch_id, filename, profiles_extracted) VALUES (%s, %s, %s)",
        (batch_id, "OCR Scan Batch", len(profiles_to_save))
    )

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"success": True, "batch_id": batch_id, "count": len(profiles_to_save)})

@app.route("/export", methods=["GET"])
def export_page():
    if "user" not in session:
        return redirect(url_for("login"))

    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    education = request.args.get("education", "").strip()
    native_place = request.args.get("native_place", "").strip()
    batch_filter = request.args.get("batch_filter", "").strip()
    search = request.args.get("search", "").strip()
    action = request.args.get("action", "preview")

    query = "SELECT * FROM profiles WHERE 1=1"
    params = []

    if date_from:
        query += " AND DATE(created_at) >= %s"
        params.append(date_from)
    if date_to:
        query += " AND DATE(created_at) <= %s"
        params.append(date_to)
    if education:
        query += " AND LOWER(education) LIKE %s"
        params.append(f"%{education.lower()}%")
    if native_place:
        query += " AND LOWER(native_place) LIKE %s"
        params.append(f"%{native_place.lower()}%")
    if batch_filter:
        query += " AND LOWER(batch_id) LIKE %s"
        params.append(f"%{batch_filter.lower()}%")
    if search:
        query += " AND (LOWER(name) LIKE %s OR LOWER(profile_id) LIKE %s OR phone_numbers LIKE %s)"
        params.extend([f"%{search.lower()}%", f"%{search.lower()}%", f"%{search.lower()}%"])

    query += " ORDER BY id DESC"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, tuple(params))
    filtered_profiles = cursor.fetchall()
    cursor.close()
    conn.close()

    if action == "export_csv":
        output = io.StringIO()
        output.write('\ufeff')
        
        writer = csv.writer(output)

        headers = [
            "Batch ID",
            "Profile ID",
            "Name",
            "Mobile No",
            "Email",
            "Education",
            "Job & Company",
            "Salary",
            "Date of Birth",
            "Native / Living Place",
            "Star / Rasi",
            "Height & Complexion",
            "Father Details",
            "Property Details",
            "Expectation",
            "Address / Contact Person",
            "Database ID",
            "Registered Date"
        ]
        writer.writerow(headers)

        for row in filtered_profiles:
            writer.writerow([
                row.get("batch_id") or "-",
                row.get("profile_id") or "-",
                row.get("name") or "-",
                row.get("phone_numbers") or "-",
                row.get("email") or "-",
                row.get("education") or "-",
                row.get("job_and_company") or "-",
                row.get("salary") or "-",
                row.get("dob") or "-",
                row.get("native_place") or "-",
                row.get("star_rasi") or "-",
                row.get("height_complexion") or "-",
                row.get("father_details") or "-",
                row.get("property_details") or "-",
                row.get("expectation") or "-",
                row.get("contact_person") or "-",
                row.get("id"),
                row.get("created_at")
            ])

        output.seek(0)
        filename = f"Matrimony_Profiles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            output.getvalue().encode('utf-8'),
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    return render_template(
        "export.html",
        username=session["user"],
        profiles=filtered_profiles,
        date_from=date_from,
        date_to=date_to,
        education=education,
        native_place=native_place,
        batch_filter=batch_filter,
        search=search
    )

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
