import os
import re
import uuid

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

from werkzeug.utils import secure_filename

from database import get_db_connection
from config import Config


# =========================================
# 1. FLASK APP CONFIGURATION
# =========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(
        BASE_DIR, "modales", "templates"
    ),
    static_folder=os.path.join(
        BASE_DIR, "modales", "static"
    )
)

app.secret_key = Config.SECRET_KEY

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    getattr(Config, "UPLOAD_FOLDER", "uploads")
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {"pdf", "docx"}


# =========================================
# 2. DATABASE CONNECTION
# =========================================

def execute_query(query, values=None, fetch=False):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(query, values or ())

        if fetch:
            return cursor.fetchall()

        connection.commit()

        return cursor.lastrowid

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


# =========================================
# 3. DATABASE INITIALIZATION
# =========================================

def init_db():

    connection = get_db_connection()
    cursor = connection.cursor()

    try:

        # JOBS TABLE

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(250) NOT NULL,
                job_title VARCHAR(250),
                description TEXT,
                required_skills TEXT,
                department VARCHAR(150),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # RESUMES TABLE

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resumes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                candidate_name VARCHAR(255),
                email VARCHAR(255),
                phone VARCHAR(50),
                resume_file VARCHAR(255),
                extracted_text LONGTEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # SCREENING RESULTS TABLE

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS screening_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                resume_id INT,
                job_id INT,
                match_score FLOAT DEFAULT 0,
                matched_skills TEXT,
                missing_skills TEXT,
                status VARCHAR(50) DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # CHECK JOB COLUMNS

        cursor.execute("SHOW COLUMNS FROM jobs")

        job_columns = [
            row[0] for row in cursor.fetchall()
        ]

        job_fields = {
            "title": "VARCHAR(250) NULL",
            "job_title": "VARCHAR(250) NULL",
            "description": "TEXT",
            "required_skills": "TEXT",
            "department": "VARCHAR(150)"
        }

        for column, datatype in job_fields.items():

            if column not in job_columns:

                cursor.execute(
                    f"ALTER TABLE jobs ADD COLUMN {column} {datatype}"
                )

        # SYNC OLD JOB TITLES

        cursor.execute("""
            UPDATE jobs
            SET title = COALESCE(
                NULLIF(title, ''),
                NULLIF(job_title, ''),
                'Untitled Job'
            ),
            job_title = COALESCE(
                NULLIF(job_title, ''),
                NULLIF(title, ''),
                'Untitled Job'
            )
        """)

        # CHECK RESUME COLUMNS

        cursor.execute("SHOW COLUMNS FROM resumes")

        resume_columns = [
            row[0] for row in cursor.fetchall()
        ]

        resume_fields = {
            "candidate_name": "VARCHAR(255)",
            "email": "VARCHAR(255)",
            "phone": "VARCHAR(50)",
            "resume_file": "VARCHAR(255)",
            "extracted_text": "LONGTEXT"
        }

        for column, datatype in resume_fields.items():

            if column not in resume_columns:

                cursor.execute(
                    f"ALTER TABLE resumes ADD COLUMN {column} {datatype}"
                )

        # CHECK SCREENING COLUMNS

        cursor.execute("SHOW COLUMNS FROM screening_results")

        result_columns = [
            row[0] for row in cursor.fetchall()
        ]

        result_fields = {
            "resume_id": "INT NULL",
            "job_id": "INT NULL",
            "match_score": "FLOAT DEFAULT 0",
            "matched_skills": "TEXT",
            "missing_skills": "TEXT",
            "status": "VARCHAR(50) DEFAULT 'Pending'"
        }

        for column, datatype in result_fields.items():

            if column not in result_columns:

                cursor.execute(
                    f"ALTER TABLE screening_results "
                    f"ADD COLUMN {column} {datatype}"
                )

        connection.commit()

        print("Database initialized successfully!")

    except Exception as e:

        connection.rollback()

        print("DATABASE ERROR:", str(e))

        raise

    finally:

        cursor.close()
        connection.close()


# =========================================
# 4. HELPER FUNCTIONS
# =========================================

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def extract_resume_text(filepath):

    extension = filepath.rsplit(".", 1)[1].lower()

    if extension == "pdf":

        from pypdf import PdfReader

        reader = PdfReader(filepath)

        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    elif extension == "docx":

        from docx import Document

        document = Document(filepath)

        return "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
        )

    return ""


def extract_candidate_details(text):

    email_match = re.search(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text
    )

    phone_match = re.search(
        r"(?:\+91[\s-]?)?[6-9]\d{9}",
        text
    )

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    name = lines[0][:255] if lines else "Unknown Candidate"

    email = email_match.group(0) if email_match else ""

    phone = phone_match.group(0) if phone_match else ""

    return name, email, phone


def calculate_match(resume_text, required_skills):

    resume_text = (resume_text or "").lower()

    skills = [
        skill.strip().lower()
        for skill in (required_skills or "").split(",")
        if skill.strip()
    ]

    matched = [
        skill for skill in skills
        if skill in resume_text
    ]

    missing = [
        skill for skill in skills
        if skill not in matched
    ]

    score = (
        round(len(matched) / len(skills) * 100, 2)
        if skills else 0
    )

    return score, matched, missing


# =========================================
# 5. HOME PAGE
# =========================================

@app.route("/")
def home():

    return redirect(url_for("dashboard"))


# =========================================
# 6. DASHBOARD
# =========================================

@app.route("/dashboard")
def dashboard():

    try:

        jobs = execute_query(
            "SELECT COUNT(*) AS total FROM jobs",
            fetch=True
        )

        resumes = execute_query(
            "SELECT COUNT(*) AS total FROM resumes",
            fetch=True
        )

        results = execute_query(
            "SELECT COUNT(*) AS total FROM screening_results",
            fetch=True
        )

        candidates = execute_query("""
            SELECT
                r.id,
                r.candidate_name,
                r.email,
                s.match_score,
                s.status
            FROM resumes r
            LEFT JOIN screening_results s
            ON r.id = s.resume_id
            ORDER BY r.id DESC
            LIMIT 5
        """, fetch=True)

        return render_template(
            "dashboard.html",
            total_jobs=jobs[0]["total"],
            total_resumes=resumes[0]["total"],
            total_results=results[0]["total"],
            candidates=candidates
        )

    except Exception as e:

        print("DASHBOARD ERROR:", repr(e))

        return f"Dashboard Error: {e}", 500


# =========================================
# 7. JOBS PAGE
# =========================================

@app.route("/jobs")
def jobs():

    try:

        job_list = execute_query("""
            SELECT
                id,
                COALESCE(
                    NULLIF(job_title, ''),
                    NULLIF(title, ''),
                    'Untitled Job'
                ) AS title,
                required_skills,
                description,
                department,
                created_at
            FROM jobs
            ORDER BY id DESC
        """, fetch=True)

        return render_template(
            "jobs.html",
            jobs=job_list
        )

    except Exception as e:

        print("JOBS ERROR:", repr(e))

        return f"Jobs Error: {e}", 500


# =========================================
# 8. ADD JOB
# =========================================

@app.route("/add_job", methods=["GET", "POST"])
def add_job():

    if request.method == "POST":

        title = request.form.get("title", "").strip()

        description = request.form.get(
            "description", ""
        ).strip()

        skills = request.form.get(
            "required_skills", ""
        ).strip()

        department = request.form.get(
            "department", ""
        ).strip()

        if not title:

            flash("Please enter job title!")

            return redirect(url_for("add_job"))

        try:

            execute_query("""
                INSERT INTO jobs
                (
                    title,
                    job_title,
                    description,
                    required_skills,
                    department
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                title,
                title,
                description,
                skills,
                department
            ))

            flash("Job added successfully!")

            return redirect(url_for("jobs"))

        except Exception as e:

            print("ADD JOB ERROR:", repr(e))

            return f"Add Job Error: {e}", 500

    return render_template("add_job.html")


# =========================================
# 9. UPLOAD RESUME
# =========================================

@app.route("/upload", methods=["GET", "POST"])
def upload():

    if request.method == "POST":

        file = request.files.get("resume")

        job_id = request.form.get("job_id")

        if not file or not file.filename:

            flash("Please select a resume!")

            return redirect(url_for("upload"))

        if not allowed_file(file.filename):

            flash("Only PDF and DOCX files allowed!")

            return redirect(url_for("upload"))

        if not job_id or not job_id.isdigit():

            flash("Please select a valid job!")

            return redirect(url_for("upload"))

        filepath = None

        try:

            selected_jobs = execute_query("""
                SELECT
                    id,
                    COALESCE(
                        NULLIF(job_title, ''),
                        NULLIF(title, '')
                    ) AS title,
                    required_skills
                FROM jobs
                WHERE id = %s
            """, (int(job_id),), fetch=True)

            if not selected_jobs:

                flash("Selected job does not exist!")

                return redirect(url_for("upload"))

            filename = (
                str(uuid.uuid4()) + "_"
                + secure_filename(file.filename)
            )

            filepath = os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )

            file.save(filepath)

            text = extract_resume_text(filepath)

            if not text.strip():

                os.remove(filepath)

                flash("Resume text could not be extracted!")

                return redirect(url_for("upload"))

            name, email, phone = extract_candidate_details(text)

            resume_id = execute_query("""
                INSERT INTO resumes
                (
                    candidate_name,
                    email,
                    phone,
                    resume_file,
                    extracted_text
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                name,
                email,
                phone,
                filename,
                text
            ))

            score, matched, missing = calculate_match(
                text,
                selected_jobs[0]["required_skills"]
            )

            execute_query("""
                INSERT INTO screening_results
                (
                    resume_id,
                    job_id,
                    match_score,
                    matched_skills,
                    missing_skills,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                resume_id,
                int(job_id),
                score,
                ", ".join(matched),
                ", ".join(missing),
                "Pending"
            ))

            return render_template(
                "RESULT.HTML",
                candidate_name=name,
                email=email,
                phone=phone,
                score=score,
                matched_skills=matched,
                missing_skills=missing
            )

        except Exception as e:

            print("UPLOAD ERROR:", repr(e))

            if filepath and os.path.exists(filepath):
                os.remove(filepath)

            return f"Resume Upload Error: {e}", 500

    try:

        job_list = execute_query("""
            SELECT
                id,
                COALESCE(
                    NULLIF(job_title, ''),
                    NULLIF(title, ''),
                    'Untitled Job'
                ) AS title,
                required_skills
            FROM jobs
            ORDER BY id DESC
        """, fetch=True)

        return render_template(
            "upload.html",
            jobs=job_list
        )

    except Exception as e:

        print("UPLOAD PAGE ERROR:", repr(e))

        return f"Upload Page Error: {e}", 500


# =========================================
# 10. CANDIDATES
# =========================================

@app.route("/candidates")
def candidates():

    try:

        candidate_list = execute_query("""
            SELECT
                r.id,
                r.candidate_name,
                r.email,
                r.phone,
                r.resume_file,
                COALESCE(s.match_score, 0) AS match_score,
                s.matched_skills,
                s.missing_skills,
                COALESCE(s.status, 'Pending') AS status,
                COALESCE(
                    NULLIF(j.job_title, ''),
                    NULLIF(j.title, ''),
                    'N/A'
                ) AS job_title
            FROM resumes r
            LEFT JOIN screening_results s
            ON r.id = s.resume_id
            LEFT JOIN jobs j
            ON s.job_id = j.id
            ORDER BY r.id DESC
        """, fetch=True)

        return render_template(
            "candidate.html",
            candidates=candidate_list
        )

    except Exception as e:

        print("CANDIDATES ERROR:", repr(e))

        return f"Candidates Error: {e}", 500


# =========================================
# 11. UPDATE CANDIDATE STATUS
# =========================================

@app.route(
    "/update_status/<int:candidate_id>",
    methods=["POST"]
)
def update_status(candidate_id):

    status = request.form.get("status", "").strip()

    if status not in ["Pending", "Selected", "Rejected"]:

        flash("Invalid status!")

        return redirect(url_for("candidates"))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            UPDATE screening_results
            SET status = %s
            WHERE resume_id = %s
        """, (status, candidate_id))

        if cursor.rowcount == 0:

            cursor.execute("""
                SELECT id
                FROM resumes
                WHERE id = %s
            """, (candidate_id,))

            resume = cursor.fetchone()

            if not resume:

                flash("Candidate not found!")

            else:

                cursor.execute("""
                    SELECT id
                    FROM jobs
                    ORDER BY id DESC
                    LIMIT 1
                """)

                job = cursor.fetchone()

                if job:

                    cursor.execute("""
                        INSERT INTO screening_results
                        (resume_id, job_id, status)
                        VALUES (%s, %s, %s)
                    """, (
                        candidate_id,
                        job[0],
                        status
                    ))

                    flash("Candidate status updated!")

                else:

                    flash("Please add a job first!")

        else:

            flash("Candidate status updated!")

        connection.commit()

    except Exception as e:

        connection.rollback()

        print("STATUS ERROR:", repr(e))

        flash("Status update failed!")

    finally:

        cursor.close()
        connection.close()

    return redirect(url_for("candidates"))


# =========================================
# 12. DELETE CANDIDATE
# =========================================

@app.route(
    "/delete_candidate/<int:candidate_id>",
    methods=["POST"]
)
def delete_candidate(candidate_id):

    try:

        resumes = execute_query("""
            SELECT resume_file
            FROM resumes
            WHERE id = %s
        """, (candidate_id,), fetch=True)

        execute_query("""
            DELETE FROM screening_results
            WHERE resume_id = %s
        """, (candidate_id,))

        execute_query("""
            DELETE FROM resumes
            WHERE id = %s
        """, (candidate_id,))

        if resumes and resumes[0]["resume_file"]:

            filepath = os.path.join(
                app.config["UPLOAD_FOLDER"],
                resumes[0]["resume_file"]
            )

            if os.path.exists(filepath):
                os.remove(filepath)

        flash("Candidate deleted successfully!")

    except Exception as e:

        print("DELETE ERROR:", repr(e))

        flash("Candidate delete failed!")

    return redirect(url_for("candidates"))


# =========================================
# LOGOUT ROUTE
# =========================================

@app.route("/logout", methods=["GET", "POST"])
def logout():
    from flask import session

    session.clear()

    flash("Logged out successfully!")

    return redirect(url_for("home"))


# =========================================
# START FLASK APPLICATION
# =========================================

if __name__ == "__main__":

    print("=================================")
    print(" RESUME SCREENING SYSTEM STARTING")
    print("=================================")

    try:
        init_db()
        print("Database initialized successfully!")

    except Exception as e:
        print("DATABASE ERROR:", repr(e))
        raise

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        use_reloader=False
    )


# =========================================
# 14. ERROR HANDLERS
# =========================================

@app.errorhandler(404)
def page_not_found(error):

    return "404 - Page Not Found", 404


@app.errorhandler(413)
def file_too_large(error):

    return "File size must be less than 10 MB.", 413


# =========================================
# 15. START APPLICATION
# =========================================

if __name__ == "__main__":

    print("\n================================")
    print(" RESUME SCREENING SYSTEM")
    print("================================\n")

    try:

        init_db()

        print("Database connected successfully!")

        print("Starting Flask server...")

        app.run(
            host="127.0.0.1",
            port=5000,
            debug=True,
            use_reloader=False
        )

    except Exception as e:

        print("APPLICATION START ERROR:", repr(e))