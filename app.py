from flask import Flask, render_template, request, redirect, session, flash, send_file, Response
# Importing Mysql Connector
import mysql.connector
# Importing JSON
import json
import csv
from io import StringIO
import datetime
import os
# Imporitng secur_file for safe files
from werkzeug.utils import secure_filename
# importing for mailing
from flask_mail import Mail, Message

# Importing functions from utils to work on resume screening and ranking
from utils.pdf_reader import pdf_reader
from utils.skill_matcher import load_json, match_skills
from utils.resume_parser import parse_resume
from utils.jd_parser import JobDescriptionParser
from utils.ranking_engine import rank_single_candidate
# to use regex
import re

# Flask app initialization
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session management

# Load configuration parameters from config.json
with open('config.json', 'r') as c:
    params = json.load(c)["parameters"]
    
# MySQL connection
conn = mysql.connector.connect(
    host=params["host"],
    user=params["user"],
    password=params["password"],
    database=params["database"]
)
cursor = conn.cursor(dictionary=True)

# Table creation
# Admin Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS admin (
    emp_id VARCHAR(25) NOT NULL,
    name VARCHAR(50) NOT NULL,
    email_id VARCHAR(50) NOT NULL,
    phn_no VARCHAR(10) NOT NULL,
    password VARCHAR(50) NOT NULL,
    last_login DATETIME DEFAULT NULL,
    PRIMARY KEY (emp_id),
    UNIQUE KEY emp_id_UNIQUE (emp_id)
    ); 
""")

# Applicant Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS applicant (
    applicant_id int NOT NULL AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    phn_no VARCHAR(10) NOT NULL,
    email_id VARCHAR(50) NOT NULL,
    password VARCHAR(45) NOT NULL,   
    PRIMARY KEY (applicant_id),
    UNIQUE KEY email_id_UNIQUE (email_id),
    UNIQUE KEY sno_UNIQUE (applicant_id)
);
""")

# Applications Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS applications (
    application_id INT NOT NULL AUTO_INCREMENT,
    applicant_id INT NOT NULL,
    job_id INT NOT NULL,
    application_date DATE NOT NULL,
    match_score DECIMAL(5,2) DEFAULT NULL,
    status VARCHAR(45) DEFAULT NULL,
    resume_uploaded VARCHAR(45) NOT NULL,
    upload_date DATE NOT NULL,
    PRIMARY KEY (application_id),
    UNIQUE KEY application_id_UNIQUE (application_id),
    KEY `appliation to job_idx` (job_id),
    KEY `applicant applications_idx` (applicant_id),
    CONSTRAINT `appliation to job` FOREIGN KEY (job_id) REFERENCES jobs (job_id),
    CONSTRAINT `applicant applications` FOREIGN KEY (applicant_id) REFERENCES applicant (applicant_id)
);
""")

# Job Skills Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS job_skills (
    job_skill_id INT NOT NULL AUTO_INCREMENT,
    job_id INT NOT NULL,
    category_id INT NOT NULL,
    skill_name VARCHAR(45) NOT NULL,
    PRIMARY KEY (job_skill_id),
    UNIQUE KEY job_skill_id_UNIQUE (job_skill_id),
    KEY `job skill_idx` (job_id),
    KEY `job category_idx` (category_id),
    CONSTRAINT `job category` FOREIGN KEY (category_id) REFERENCES skill_category (category_id),
    CONSTRAINT `job skill` FOREIGN KEY (job_id) REFERENCES jobs (job_id)
);
""")

#Jobs Tabele
cursor.execute("""
CREATE TABLE IF NOT EXISTS jobs (
    job_id INT NOT NULL AUTO_INCREMENT,
    emp_id VARCHAR(25) NOT NULL,
    job_title VARCHAR(45) NOT NULL,
    company_name VARCHAR(45) NOT NULL,
    location VARCHAR(45) NOT NULL,
    min_experience INT NOT NULL,
    qualification VARCHAR(45) NOT NULL,
    jd_file_path VARCHAR(45) NOT NULL,
    posted_date DATE NOT NULL,
    status VARCHAR(45) NOT NULL,
    PRIMARY KEY (job_id),
    UNIQUE KEY job_id_UNIQUE (job_id),
    KEY `jobs by admin_idx` (emp_id),
    CONSTRAINT `jobs by admin` FOREIGN KEY (emp_id) REFERENCES admin (emp_id)
);
""")


#Skill Category Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS skill_category (
    category_id INT NOT NULL AUTO_INCREMENT,
    category_name VARCHAR(45) NOT NULL,
    PRIMARY KEY (category_id),
    UNIQUE KEY category_id_UNIQUE (category_id)
);
""")


#Profile Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS profile_applicant (
  applicant_id INT NOT NULL,
  name VARCHAR(45) NOT NULL,
  email VARCHAR(45) NOT NULL,
  phn_no VARCHAR(10) NOT NULL,
  dob DATE DEFAULT NULL,
  gender VARCHAR(45) DEFAULT NULL,
  nationality VARCHAR(45) DEFAULT 'Indian',
  address VARCHAR(100) DEFAULT NULL,
  linkedin VARCHAR(45) DEFAULT NULL,
  github VARCHAR(45) DEFAULT NULL,
  degree VARCHAR(45) DEFAULT NULL,
  branch VARCHAR(45) DEFAULT NULL,
  university VARCHAR(45) DEFAULT NULL,
  g_year YEAR DEFAULT NULL,
  cgpa INT DEFAULT NULL,
  profile_img VARCHAR(45) DEFAULT 'profile_img_default.png',
  PRIMARY KEY (email),
  UNIQUE KEY applicant_id_UNIQUE (applicant_id),
  UNIQUE KEY email_UNIQUE (email),
  CONSTRAINT applicant_to_profile FOREIGN KEY (applicant_id) REFERENCES applicant (applicant_id)
  );
  
""")

# Flask-Mail configuration
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params['mail_username'],
    MAIL_PASSWORD=params['mail_password']
)
mail = Mail(app)

# Mail helper function
def send_selection_mail(candidate_email, candidate_name, job_title):
    subject = "Selection Update - BHEL Recruitment Portal"

    body = f"""
Dear {candidate_name},

Congratulations!

You have been selected for the position of {job_title} through the BHEL Recruitment Portal.

Further communication regarding joining/document verification will be shared with you soon.

Regards,
BHEL Recruitment Team
"""

    msg = Message(
        subject=subject,
        recipients=[candidate_email],
        body=body
    )

    mail.send(msg)

# Configure upload folder for Job Descriptions
app.config['UPLOAD_FOLDER_JD'] = params['upload_location_jd']
# Configure upload folder for Resumes
app.config['UPLOAD_FOLDER_RESUME'] = params['upload_location_resume']
# Configure upload folder for Profile Pictures
app.config['UPLOAD_FOLDER_PROFILE_PICTURE'] = params['upload_location_pf']

def calculate_profile_completion(profile):
    if not profile:
        return 0

    fields = [
        profile.get('name'),
        profile.get('email'),
        profile.get('phn_no'),
        profile.get('dob'),
        profile.get('gender'),
        profile.get('nationality'),
        profile.get('address'),
        profile.get('linkedin'),
        profile.get('github'),
        profile.get('degree'),
        profile.get('branch'),
        profile.get('university'),
        profile.get('g_year'),
        profile.get('cgpa'),
        profile.get('profile_img')
    ]

    filled = sum(1 for field in fields if field not in [None, "", " "])

    return int((filled / len(fields)) * 100)

# create account route
@app.route('/create', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        # Handle account creation logic here
        fullname = request.form['Fullname']
        mobile_number = request.form['mobile_number']
        email = request.form['username']
        password = request.form['password']
        role = request.form['role']
        if role == 'admin':
            try:
                emp_id = request.form['employeeId']
                # Insert the new admin into the database
                cursor.execute("INSERT INTO admin (emp_id, name, email_id, phn_no, password) VALUES (%s, %s, %s, %s, %s)", 
                                (emp_id, fullname, email, mobile_number, password))
                conn.commit()
                flash("Admin account created successfully!", "success")
            except Exception as e:
                conn.rollback()  # Rollback in case of error
                print("Database Error:", e)
                flash("Failed to create admin account.", "danger")
        else:
            try:
                cursor.execute("INSERT INTO applicant (name, phn_no, email_id, password) VALUES (%s, %s, %s, %s)",
                (fullname, mobile_number, email, password))
                applicant_id = cursor.lastrowid
                cursor.execute("INSERT INTO profile_applicant (applicant_id, name, email, phn_no) VALUES (%s, %s, %s, %s)", (applicant_id,fullname, email, mobile_number))
                conn.commit()
                flash("Applicant account created successfully!", "success")
            except Exception as e:
                conn.rollback()  # Rollback in case of error
                print("Database Error:", e)
                flash("Failed to create applicant account.", "danger")
        return redirect('/login')  # Redirect to login page after successful account creation
    return render_template('create_page.html', params=params)


# Login page route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form.get('role')
        if role == 'admin':
            empid = request.form.get('employeeId')
            passa = request.form.get('password')
            cursor.execute("SELECT * FROM admin WHERE emp_id = %s AND password = %s", (empid, passa))
            admin = cursor.fetchone()
            if admin:
                session['user_id'] = admin['emp_id']  # Store admin ID in session
                session['admin_name'] = admin['name']  # Store admin name in session
                session['role'] = 'admin'  # Store admin role in session
                cursor.execute("UPDATE admin SET last_login=%s WHERE emp_id=%s",(datetime.datetime.now(), session['user_id']))
                conn.commit()
                flash("Admin logged in successfully!", "success")
                return redirect(f'/dashboard/{session["role"]}/{session["user_id"]}')  # Redirect to dashboard after successful login
            else:
                flash("Invalid admin credentials.", "danger")

        else:
            email = request.form.get('email')
            passa = request.form.get('password')
            cursor.execute("SELECT * FROM applicant WHERE email_id = %s AND password = %s", (email, passa))
            applicant = cursor.fetchone()
            if applicant:
                session['user_id'] = applicant['applicant_id']  # Store applicant ID in session
                session['applicant_name'] = applicant['name']  # Store applicant name in session
                session['role'] = 'applicant'  # Store applicant role in session
                cursor.execute("UPDATE applicant SET last_login=%s WHERE applicant_id=%s",(datetime.datetime.now(), session['user_id']))
                conn.commit()
                flash("Applicant logged in successfully!", "success")
                return redirect(f'/dashboard/{session["role"]}/{session["user_id"]}')  # Redirect to dashboard after successful login
            else:
                flash("Invalid applicant credentials.", "danger")

    return render_template('login.html', params=params)


# Home page route
@app.route('/')
def home():
    return render_template('home_page.html', params=params)

# Dashboard route for applicant
@app.route('/dashboard/applicant/<string:id>')
def dashboard(id):

    if 'user_id' not in session:
        flash("Please login first.", "danger")
        return redirect('/login')

    if session.get('role') != 'applicant':
        flash("Invalid session.", "danger")
        return redirect('/login')

    applicant_id = session['user_id']

    if str(applicant_id) != str(id):
        flash("Unauthorized access.", "danger")
        return redirect('/login')

    cursor.execute("""
        SELECT *
        FROM applicant
        WHERE applicant_id = %s
    """, (applicant_id,))
    applicant = cursor.fetchone()

    cursor.execute("""
        SELECT *
        FROM profile_applicant
        WHERE applicant_id = %s
    """, (applicant_id,))
    applicant_profile = cursor.fetchone()

    cursor.execute("""
        SELECT
            a.application_id,
            a.application_date,
            a.match_score,
            a.status,
            j.job_title,
            j.company_name,
            j.location
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        WHERE a.applicant_id = %s
        ORDER BY a.application_date DESC
        LIMIT 5
    """, (applicant_id,))
    applications = cursor.fetchall()

    total_applications = len(applications)

    cursor.execute("""
        SELECT
            SUM(CASE WHEN status='Under Review' THEN 1 ELSE 0 END) AS under_review,
            SUM(CASE WHEN status='Shortlisted' THEN 1 ELSE 0 END) AS shortlisted,
            SUM(CASE WHEN status='Rejected' THEN 1 ELSE 0 END) AS rejected,
            SUM(CASE WHEN status='Selected' THEN 1 ELSE 0 END) AS selected
        FROM applications
        WHERE applicant_id=%s
    """, (applicant_id,))
    counts = cursor.fetchone()

    under_review = counts['under_review'] or 0
    shortlisted = counts['shortlisted'] or 0
    rejected = counts['rejected'] or 0
    selected = counts['selected'] or 0

    profile_fields = [
        applicant_profile.get('name') if applicant_profile else None,
        applicant_profile.get('email') if applicant_profile else None,
        applicant_profile.get('phn_no') if applicant_profile else None,
        applicant_profile.get('dob') if applicant_profile else None,
        applicant_profile.get('gender') if applicant_profile else None,
        applicant_profile.get('address') if applicant_profile else None,
        applicant_profile.get('degree') if applicant_profile else None,
        applicant_profile.get('branch') if applicant_profile else None,
        applicant_profile.get('university') if applicant_profile else None,
        applicant_profile.get('cgpa') if applicant_profile else None
    ]

    # filled_fields = sum(1 for field in profile_fields if field)
    profile_completion = calculate_profile_completion(applicant_profile)

    return render_template(
        'dashboard_applicant.html',
        params=params,
        applicant=applicant,
        applicant_profile=applicant_profile,
        applications=applications,
        total_applications=total_applications,
        under_review=under_review,
        shortlisted=shortlisted,
        rejected=rejected,
        selected=selected,
        profile_completion=profile_completion,
        active_page='dashboard'
    )

# Route to handle resume update
@app.route('/applicant/<string:applicant_id>/<string:application_id>/resume/update', methods=['POST'])
def update_resume(applicant_id, application_id):

    if 'user_id' not in session:
        flash("Please login first.", "danger")
        return redirect('/login')

    try:
        if str(session['user_id']) != applicant_id:
            flash("Unauthorized access.", "danger")
            return redirect('/login')
        resume_file = request.files.get('resume_upload')

        if not resume_file or resume_file.filename == '':
            flash("Please select a PDF file.", "danger")
            return redirect(f'/dashboard/applicant/{session["user_id"]}')

        if not resume_file.filename.lower().endswith('.pdf'):
            flash("Only PDF files are allowed.", "danger")
            return redirect(f'/dashboard/applicant/{session["user_id"]}')

        cursor.execute("SELECT * FROM applications WHERE application_id=%s",(application_id,))
        application = cursor.fetchone()
        if not application:
            flash("Application not found.", "danger")
            return redirect(f'/dashboard/applicant/{session["user_id"]}')
        
        #Removing old Resume
        if application.get('resume_uploaded'):
            old_file = os.path.join(
                app.config['UPLOAD_FOLDER_RESUME'],
                application['resume_uploaded'])

            if os.path.exists(old_file):
                os.remove(old_file)
        
        resume_filename = f"{applicant_id}_{application['job_id']}_Resume.pdf"
        resume_file.save(os.path.join(app.config['UPLOAD_FOLDER_RESUME'],resume_filename))
        cursor.execute("UPDATE applications SET resume_uploaded = %s, upload_date = %s WHERE application_id = %s", ( resume_filename, datetime.date.today(), application_id))
        conn.commit()
        flash("Resume updated successfully!", "success")

    except Exception as e:
        conn.rollback()
        print("Resume Update Error:", e)
        flash("Failed to update resume.", "danger")

    return redirect(f'/dashboard/applicant/{session["user_id"]}')

# Route to display applicant's applications
@app.route('/applicant/applications/<string:applicant_id>')
def application(applicant_id):

    if 'user_id' not in session:
        flash("Please login first.", "danger")
        return redirect('/login')

    if str(session['user_id']) != str(applicant_id):
        flash("Unauthorized access.", "danger")
        return redirect('/login')

    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()

    cursor.execute("""
        SELECT *
        FROM applicant
        WHERE applicant_id=%s
    """, (applicant_id,))
    applicant = cursor.fetchone()

    query = """
        SELECT
            a.application_id,
            a.application_date,
            a.match_score,
            a.status,
            a.resume_uploaded,

            j.job_title,
            j.company_name,
            j.location

        FROM applications a
        JOIN jobs j
        ON a.job_id = j.job_id

        WHERE a.applicant_id=%s
    """

    values = [applicant_id]

    if search_query:
        query += " AND j.job_title LIKE %s"
        values.append(f"%{search_query}%")

    if status_filter:
        query += " AND a.status=%s"
        values.append(status_filter)

    query += " ORDER BY a.application_date DESC"

    cursor.execute(query, tuple(values))
    applications = cursor.fetchall()

    total_applied = len(applications)

    shortlisted = sum(
        1 for app in applications
        if app['status'] == 'Shortlisted'
    )

    rejected = sum(
        1 for app in applications
        if app['status'] == 'Rejected'
    )

    selected = sum(
        1 for app in applications
        if app['status'] == 'Selected'
    )

    under_review = sum(
        1 for app in applications
        if app['status'] in ['Applied', 'Under Review']
    )

    return render_template(
        'my_applications.html',
        params=params,
        applicant=applicant,
        applications=applications,

        total_applied=total_applied,
        shortlisted=shortlisted,
        rejected=rejected,
        selected=selected,
        under_review=under_review,

        search_query=search_query,
        status_filter=status_filter,

        active_page='applications'
    )

# Route to display available jobs to the applicant
@app.route('/jobs/<string:applicant_id>')
def find_jobs(applicant_id):

    if 'user_id' not in session:
        flash("Please login first.", "danger")
        return redirect('/login')

    if str(session['user_id']) != str(applicant_id):
        flash("Unauthorized access.", "danger")
        return redirect('/login')

    search_query = request.args.get('q', '').strip()
    location_filter = request.args.get('location', '').strip()
    experience_filter = request.args.get('experience', '').strip()

    cursor.execute("""
        SELECT *
        FROM applicant
        WHERE applicant_id = %s
    """, (applicant_id,))
    applicant = cursor.fetchone()

    query = """
        SELECT
            j.*,
            CASE
                WHEN a.application_id IS NOT NULL THEN 1
                ELSE 0
            END AS already_applied
        FROM jobs j
        LEFT JOIN applications a
            ON j.job_id = a.job_id
            AND a.applicant_id = %s
        WHERE j.status = 'Active'
    """

    values = [applicant_id]

    if search_query:
        query += " AND j.job_title LIKE %s"
        values.append(f"%{search_query}%")

    if location_filter:
        query += " AND j.location LIKE %s"
        values.append(f"%{location_filter}%")

    if experience_filter:
        query += " AND j.min_experience <= %s"
        values.append(experience_filter)

    query += " ORDER BY j.posted_date DESC"

    cursor.execute(query, tuple(values))
    jobs = cursor.fetchall()

    return render_template(
        'find_jobs.html',
        params=params,
        applicant=applicant,
        jobs=jobs,
        search_query=search_query,
        location_filter=location_filter,
        experience_filter=experience_filter,
        active_page='jobs'
    )

# Route to display applicant's resume
@app.route('/applicant/<string:applicant_id>/<string:application_id>/resume')
def view_resume(applicant_id, application_id):

    if 'user_id' not in session:
        flash("Please login first.", "danger")
        return redirect('/login')

    if str(session['user_id']) != str(applicant_id):
        flash("Unauthorized access.", "danger")
        return redirect('/login')

    cursor.execute("""
        SELECT *
        FROM applicant
        WHERE applicant_id=%s
    """, (applicant_id,))
    applicant = cursor.fetchone()

    cursor.execute("""
        SELECT 
            a.*,
            j.job_title,
            j.company_name
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        WHERE a.application_id = %s
        AND a.applicant_id = %s
    """, (application_id, applicant_id))
    application = cursor.fetchone()

    if not application:
        flash("Application not found.", "danger")
        return redirect(f'/applicant/applications/{applicant_id}')

    return render_template(
        'my_resume.html',
        params=params,
        applicant=applicant,
        application=application,
        active_page='resume'
    )

# Route to display applicant's profile
# Route to display applicant's profile
@app.route('/applicant/profile/<string:applicant_id>')
def profile_applicant(applicant_id):

    if 'user_id' not in session:
        flash("Please login first.", "danger")
        return redirect('/login')

    if str(session['user_id']) != str(applicant_id):
        flash("Unauthorized access.", "danger")
        return redirect('/login')

    applicant_id = session['user_id']

    cursor.execute("""
        SELECT *
        FROM profile_applicant
        WHERE applicant_id = %s
    """, (applicant_id,))
    applicant = cursor.fetchone()

    if not applicant:
        flash("Profile not found.", "danger")
        return redirect(f'/dashboard/applicant/{applicant_id}')

    skills = []

    cursor.execute("""
        SELECT resume_uploaded
        FROM applications
        WHERE applicant_id = %s
        AND resume_uploaded IS NOT NULL
        ORDER BY upload_date DESC
        LIMIT 1
    """, (applicant_id,))

    latest_application = cursor.fetchone()

    if latest_application and latest_application['resume_uploaded']:
        resume_path = os.path.join(
            app.config['UPLOAD_FOLDER_RESUME'],
            latest_application['resume_uploaded']
        )

        if os.path.exists(resume_path):
            try:
                resume_data = parse_resume(resume_path)
                skills = resume_data.get("skills", [])
            except Exception as e:
                print("Profile Resume Skill Extraction Error:", e)
                skills = []

    profile_completion = calculate_profile_completion(applicant)

    return render_template(
        'profile.html',
        params=params,
        applicant=applicant,
        skills=skills,
        profile_completion=profile_completion,
        active_page='profile',
        role=session['role'].upper()
    )
    
# Route to edit applicant's profile
@app.route('/profile/<string:applicant_id>/edit', methods=['GET','POST'])
def profile_applicant_edit(applicant_id): 
    if 'user_id' not in session:
        flash("Please login first.", "danger")
        return redirect('/login')
    try:
        applicant_id = session['user_id']
        cursor.execute("SELECT * FROM profile_applicant WHERE applicant_id = %s", (applicant_id,))
        applicant = cursor.fetchone()
        if request.method == 'POST':
            pic_file = applicant['profile_img']
            profile_picture = request.files.get('profile_picture')
            
            # Process image only if user uploaded one
            if profile_picture and profile_picture.filename != '':
                
                if not profile_picture.mimetype.startswith('image/'):
                    flash("Only image files are allowed.", "danger")
                    return redirect(f'/applicant/profile/{session["user_id"]}')

                extension = os.path.splitext(secure_filename(profile_picture.filename))[1].lower()
                pic_file = f"{applicant_id}_profile{extension}"
                profile_picture.save(os.path.join(app.config['UPLOAD_FOLDER_PROFILE_PICTURE'], pic_file))

            name = request.form.get("name")
            dob = request.form.get("dob") or None
            gender = request.form.get("gender")
            nationality = request.form.get("nationality")
            email = request.form.get("email")
            phn_no = request.form.get("phn_no")
            city = request.form.get("city")
            state = request.form.get("state")
            address = request.form.get("address")
            linkedin = request.form.get("linkedin")
            git = request.form.get("git")
            degree = request.form.get("degree")
            branch = request.form.get("branch")
            university = request.form.get("university")
            g_year = request.form.get("g_year") or None
            cgpa = request.form.get("cgpa") or None
            # skill = request.form.get("skill")
            # soft_skill = request.form.get("soft_skill")
            # lang = request.form.get("lang")

            cursor.execute("UPDATE profile_applicant SET name = %s, email = %s, phn_no = %s, dob = %s, gender = %s, nationality = %s, address = %s, linkedin = %s, github = %s, degree = %s, branch = %s, university = %s, g_year = %s, cgpa = %s, profile_img = %s WHERE applicant_id = %s", ( name, email,phn_no, dob, gender, nationality, f"{address}\n{city}\n{state}", linkedin, git, degree, branch, university, g_year, cgpa, pic_file, applicant_id))
            cursor.execute("UPDATE applicant SET name = %s, email_id = %s, phn_no = %s, linkedin_url= %s, github_url = %s WHERE applicant_id = %s", ( name, email, phn_no, linkedin, git, applicant_id))
            conn.commit()
            flash("Profile updated successfully!", "success")
            return redirect(f'/applicant/profile/{session["user_id"]}')

    except Exception as e:
        conn.rollback()
        print("Profile Update Error:", e)
        flash("Failed to update Profile.", "danger")
        return redirect(f'/dashboard/applicant/{session["user_id"]}')
    return render_template('edit_profile.html', params=params, applicant= applicant)

# Route to handle applicant logout
@app.route('/applicant/logout/<string:applicant_id>')
def applicant_logout(applicant_id):
    role = session.get('role').upper()
    cursor.execute("SELECT * FROM applicant WHERE applicant_id = %s", (applicant_id,))
    applicant = cursor.fetchone()
    cursor.execute("SELECT * FROM profile_applicant WHERE applicant_id = %s", (applicant_id,))
    applicant_profile = cursor.fetchone()
    return render_template('logout.html', params=params, applicant = applicant, applicant_profile = applicant_profile, role=role)

# Route to handle admin logout
@app.route('/admin/logout/<string:admin_id>')
def admin_logout(admin_id):
    if 'user_id' not in session:
        flash("Please login first.", "danger")
        return redirect('/login')
    admin_id = session['user_id']
    role = session.get('role').upper()
    cursor.execute("SELECT * FROM admin WHERE emp_id = %s", (admin_id,))
    admin = cursor.fetchone()
    return render_template('admin_logout.html', params=params, admin = admin, role=role)

# Route to handle logout for both admin and applicant
@app.route('/logout')
def logout():  
    session.clear()
    return redirect('/')

# Route to preview applicant's resume
@app.route('/preview_resume/<int:application_id>')
def preview_resume(application_id):

    if 'user_id' not in session:
        flash("Please login first.", "danger")
        return redirect('/login')

    cursor.execute("""
        SELECT resume_uploaded
        FROM applications
        WHERE application_id=%s
    """, (application_id,))

    application = cursor.fetchone()

    if not application or not application['resume_uploaded']:
        flash("Resume not found.", "danger")
        return redirect(request.referrer or '/')

    resume_path = os.path.join(
        app.config['UPLOAD_FOLDER_RESUME'],
        application['resume_uploaded']
    )

    if not os.path.exists(resume_path):
        flash("Resume file does not exist.", "danger")
        return redirect(request.referrer or '/')

    return send_file(resume_path)

# Route to download applicant's resume
@app.route('/download_resume/<int:application_id>')
def download_resume(application_id):

    cursor.execute("""
        SELECT resume_uploaded
        FROM applications
        WHERE application_id=%s
    """, (application_id,))

    application = cursor.fetchone()

    if not application or not application['resume_uploaded']:
        flash("Resume not found.", "danger")
        return redirect(request.referrer or '/')

    resume_path = os.path.join(
        app.config['UPLOAD_FOLDER_RESUME'],
        application['resume_uploaded']
    )

    return send_file(resume_path, as_attachment=True)


@app.route('/<string:applicant_id>/apply/<string:job_id>', methods=['POST'])
def apply_job(applicant_id, job_id):

    if 'user_id' not in session:
        flash("Please login first.", "danger")
        return redirect('/login')

    if str(session['user_id']) != str(applicant_id):
        flash("Unauthorized access.", "danger")
        return redirect('/login')

    try:
        cursor.execute("""
            SELECT *
            FROM applications
            WHERE applicant_id = %s AND job_id = %s
        """, (applicant_id, job_id))

        existing_application = cursor.fetchone()

        if existing_application:
            flash("You have already applied for this job.", "warning")
            return redirect(f'/jobs/{applicant_id}')

        resume_file = request.files.get('resume')

        if not resume_file or resume_file.filename == '':
            flash("Please upload your resume PDF.", "danger")
            return redirect(f'/jobs/{applicant_id}')

        if not resume_file.filename.lower().endswith('.pdf'):
            flash("Only PDF resumes are allowed.", "danger")
            return redirect(f'/jobs/{applicant_id}')

        resume_filename = f"{applicant_id}_{job_id}_Resume.pdf"
        resume_path = os.path.join(app.config['UPLOAD_FOLDER_RESUME'], resume_filename)
        resume_file.save(resume_path)

        cursor.execute("""
            INSERT INTO applications
            (applicant_id, job_id, application_date, match_score,
             status, resume_uploaded, upload_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            applicant_id,
            job_id,
            datetime.date.today(),
            0,
            'Applied',
            resume_filename,
            datetime.date.today()
        ))

        conn.commit()

        flash("Application submitted successfully.", "success")
        return redirect(f'/applicant/applications/{applicant_id}')

    except Exception as e:
        conn.rollback()
        print("Apply Job Error:", e)
        flash("Failed to apply for job.", "danger")
        return redirect(f'/jobs/{applicant_id}')

# ---------------- ADMIN HELPER ----------------

def get_logged_admin():
    if 'user_id' not in session or session.get('role') != 'admin':
        return None

    cursor.execute("SELECT * FROM admin WHERE emp_id = %s", (session['user_id'],))
    return cursor.fetchone()


# ---------------- ADMIN DASHBOARD ----------------

@app.route('/dashboard/admin/<string:admin_id>')
def admin_dashboard(admin_id):
    admin = get_logged_admin()
    if not admin:
        flash("Please login first.", "danger")
        return redirect('/login')

    cursor.execute("SELECT COUNT(*) AS total_jobs FROM jobs WHERE emp_id=%s", (admin['emp_id'],))
    total_jobs = cursor.fetchone()['total_jobs']

    cursor.execute("SELECT COUNT(*) AS active_jobs FROM jobs WHERE emp_id=%s AND status='Active'", (admin['emp_id'],))
    active_jobs = cursor.fetchone()['active_jobs']

    cursor.execute("""
        SELECT COUNT(*) AS total_applications
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        WHERE j.emp_id = %s
    """, (admin['emp_id'],))
    total_applications = cursor.fetchone()['total_applications']

    cursor.execute("""
        SELECT COUNT(*) AS shortlisted
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        WHERE j.emp_id=%s AND a.status='Shortlisted'
    """, (admin['emp_id'],))
    shortlisted = cursor.fetchone()['shortlisted']

    cursor.execute("""
        SELECT a.*, ap.name, j.job_title
        FROM applications a
        JOIN applicant ap ON a.applicant_id = ap.applicant_id
        JOIN jobs j ON a.job_id = j.job_id
        WHERE j.emp_id=%s
        ORDER BY a.application_date DESC
        LIMIT 5
    """, (admin['emp_id'],))
    recent_applications = cursor.fetchall()

    return render_template(
        'admin_dashboard.html',
        params=params,
        admin=admin,
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        total_applications=total_applications,
        shortlisted=shortlisted,
        recent_applications=recent_applications,
        active_page='dashboard'
    )


# ---------------- MANAGE JOBS ----------------

@app.route('/manage_jobs')
def manage_jobs():
    admin = get_logged_admin()

    if not admin:
        flash("Please login first.", "danger")
        return redirect('/login')

    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()

    query = """
        SELECT *
        FROM jobs
        WHERE emp_id=%s
    """

    values = [admin['emp_id']]

    if search_query:
        query += " AND job_title LIKE %s"
        values.append(f"%{search_query}%")

    if status_filter:
        query += " AND status=%s"
        values.append(status_filter)

    query += " ORDER BY posted_date DESC"

    cursor.execute(query, tuple(values))
    jobs = cursor.fetchall()

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM jobs
        WHERE emp_id=%s
    """, (admin['emp_id'],))
    total_jobs = cursor.fetchone()['total']

    cursor.execute("""
        SELECT COUNT(*) AS active
        FROM jobs
        WHERE emp_id=%s AND status='Active'
    """, (admin['emp_id'],))
    active_jobs = cursor.fetchone()['active']

    cursor.execute("""
        SELECT COUNT(*) AS closed
        FROM jobs
        WHERE emp_id=%s AND status='Closed'
    """, (admin['emp_id'],))
    closed_jobs = cursor.fetchone()['closed']

    return render_template(
        'manage_jobs.html',
        params=params,
        admin=admin,
        jobs=jobs,
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        closed_jobs=closed_jobs,
        active_page='manage_jobs',
        search_query=search_query,
        status_filter=status_filter
    )
# ---------------- APPLICANTS ----------------

@app.route('/applicants')
def applicants():
    admin = get_logged_admin()
    if not admin:
        flash("Please login first.", "danger")
        return redirect('/login')

    cursor.execute("""
        SELECT 
            a.application_id,
            a.applicant_id,
            a.application_date,
            a.match_score,
            a.status,
            a.resume_uploaded,
            ap.name,
            ap.email_id,
            ap.phn_no,
            j.job_title,
            j.qualification
        FROM applications a
        JOIN applicant ap ON a.applicant_id = ap.applicant_id
        JOIN jobs j ON a.job_id = j.job_id
        WHERE j.emp_id = %s
        ORDER BY a.application_date DESC
    """, (admin['emp_id'],))
    applicants_data = cursor.fetchall()

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        WHERE j.emp_id=%s
    """, (admin['emp_id'],))
    total_applicants = cursor.fetchone()['total']

    return render_template(
        'applicants.html',
        params=params,
        admin=admin,
        applicants=applicants_data,
        total_applicants=total_applicants,
        active_page='applicants'
    )


# ---------------- AI SCREENING ----------------

@app.route('/ai_screen')
def ai_screen():

    admin = get_logged_admin()

    if not admin:
        flash("Please login first.", "danger")
        return redirect('/login')

    job_id = request.args.get('job_id', '').strip()
    score_filter = request.args.get('score', '').strip()

    cursor.execute("""
        SELECT job_id, job_title
        FROM jobs
        WHERE emp_id=%s
        ORDER BY posted_date DESC
    """, (admin['emp_id'],))
    jobs = cursor.fetchall()

    query = """
        SELECT 
            a.application_id,
            a.applicant_id,
            a.application_date,
            a.match_score,
            a.status,
            a.resume_uploaded,

            ap.name,
            ap.email_id,
            ap.phn_no,

            j.job_id,
            j.job_title,
            j.company_name,
            j.location,
            j.qualification

        FROM applications a
        JOIN applicant ap ON a.applicant_id = ap.applicant_id
        JOIN jobs j ON a.job_id = j.job_id

        WHERE j.emp_id=%s
    """

    values = [admin['emp_id']]

    if job_id:
        query += " AND j.job_id=%s"
        values.append(job_id)

    if score_filter:
        query += " AND a.match_score >= %s"
        values.append(score_filter)

    query += """
        ORDER BY 
            a.match_score DESC,
            a.application_date ASC
    """

    cursor.execute(query, tuple(values))
    rankings = cursor.fetchall()

    total_screened = len(rankings)

    qualified = sum(
        1 for candidate in rankings
        if candidate['match_score'] and candidate['match_score'] >= 70
    )

    rejected = sum(
        1 for candidate in rankings
        if candidate['status'] == 'Rejected'
    )

    pending = sum(
        1 for candidate in rankings
        if candidate['status'] in ['Applied', 'Under Review', None]
    )

    if rankings:
        scores = [
            float(candidate['match_score'] or 0)
            for candidate in rankings
        ]

        avg_score = round(sum(scores) / len(scores), 2)
        top_score = max(scores)
    else:
        avg_score = 0
        top_score = 0

    return render_template(
        'ai_screening.html',
        params=params,
        admin=admin,
        jobs=jobs,
        rankings=rankings,

        total_screened=total_screened,
        qualified=qualified,
        rejected=rejected,
        pending=pending,
        avg_score=avg_score,
        top_score=top_score,

        selected_job_id=job_id,
        selected_score=score_filter,

        active_page='ai_screen'
    )


# ---------------- SHORTLISTED ----------------

@app.route('/shortlist')
def shortlist():
    admin = get_logged_admin()
    if not admin:
        flash("Please login first.", "danger")
        return redirect('/login')

    cursor.execute("""
        SELECT 
            a.application_id,
            a.match_score,
            a.status,
            ap.name,
            ap.email_id,
            ap.phn_no,
            j.job_title
        FROM applications a
        JOIN applicant ap ON a.applicant_id = ap.applicant_id
        JOIN jobs j ON a.job_id = j.job_id
        WHERE j.emp_id=%s AND a.status='Shortlisted'
        ORDER BY a.match_score DESC
    """, (admin['emp_id'],))
    shortlisted = cursor.fetchall()

    return render_template(
        'shortlisted.html',
        params=params,
        admin=admin,
        shortlisted=shortlisted,
        active_page='shortlist'
    )


# ---------------- UPDATE APPLICATION STATUS ----------------

@app.route('/application/<int:application_id>/status/<string:new_status>')
def update_application_status(application_id, new_status):

    admin = get_logged_admin()

    if not admin:
        flash("Please login first.", "danger")
        return redirect('/login')

    allowed_status = [
        'Applied',
        'Under Review',
        'Shortlisted',
        'Rejected',
        'Selected'
    ]

    if new_status not in allowed_status:
        flash("Invalid application status.", "danger")
        return redirect(request.referrer or '/applicants')

    cursor.execute("""
        SELECT
            a.application_id,
            a.status,
            ap.name,
            ap.email_id,
            j.job_title
        FROM applications a
        JOIN applicant ap ON a.applicant_id = ap.applicant_id
        JOIN jobs j ON a.job_id = j.job_id
        WHERE a.application_id=%s
        AND j.emp_id=%s
    """, (application_id, admin['emp_id']))

    application = cursor.fetchone()

    if not application:
        flash("Application not found.", "danger")
        return redirect(request.referrer or '/applicants')

    cursor.execute("""
        UPDATE applications
        SET status=%s
        WHERE application_id=%s
    """, (new_status, application_id))

    conn.commit()

    if new_status == "Selected":
        try:
            send_selection_mail(
                application['email_id'],
                application['name'],
                application['job_title']
            )
            flash("Candidate selected and email sent successfully.", "success")

        except Exception as e:
            print("Mail Error:", e)
            flash("Candidate selected, but email could not be sent.", "warning")
    else:
        flash(f"Application status updated to {new_status}.", "success")

    return redirect(request.referrer or '/applicants')


# ---------------- REPORTS ----------------

@app.route('/report')
def report():

    admin = get_logged_admin()

    if not admin:
        flash("Please login first.", "danger")
        return redirect('/login')

    # ---------------- TOTAL JOBS ----------------

    cursor.execute("""
        SELECT COUNT(*) AS total_jobs
        FROM jobs
        WHERE emp_id=%s
    """, (admin['emp_id'],))

    total_jobs = cursor.fetchone()['total_jobs']

    # ---------------- TOTAL APPLICATIONS ----------------

    cursor.execute("""
        SELECT COUNT(*) AS total_applications
        FROM applications a
        JOIN jobs j
        ON a.job_id = j.job_id
        WHERE j.emp_id=%s
    """, (admin['emp_id'],))

    total_applications = cursor.fetchone()['total_applications']

    # ---------------- STATUS COUNTS ----------------

    cursor.execute("""
        SELECT
            SUM(CASE WHEN a.status='Under Review' THEN 1 ELSE 0 END) AS under_review,
            SUM(CASE WHEN a.status='Shortlisted' THEN 1 ELSE 0 END) AS shortlisted_count,
            SUM(CASE WHEN a.status='Selected' THEN 1 ELSE 0 END) AS selected_count,
            SUM(CASE WHEN a.status='Rejected' THEN 1 ELSE 0 END) AS rejected_count
        FROM applications a
        JOIN jobs j
        ON a.job_id=j.job_id
        WHERE j.emp_id=%s
    """, (admin['emp_id'],))

    counts = cursor.fetchone()

    under_review = counts['under_review'] or 0
    shortlisted_count = counts['shortlisted_count'] or 0
    selected_count = counts['selected_count'] or 0
    rejected_count = counts['rejected_count'] or 0

    # ---------------- STATUS REPORT ----------------

    cursor.execute("""
        SELECT
            a.status,
            COUNT(*) AS count
        FROM applications a
        JOIN jobs j
        ON a.job_id=j.job_id
        WHERE j.emp_id=%s
        GROUP BY a.status
    """, (admin['emp_id'],))

    status_report = cursor.fetchall()

    # ---------------- JOB REPORT ----------------

    cursor.execute("""
        SELECT
            j.job_title,
            COUNT(a.application_id) AS applications
        FROM jobs j
        LEFT JOIN applications a
        ON j.job_id=a.job_id
        WHERE j.emp_id=%s
        GROUP BY j.job_id
        ORDER BY applications DESC
    """, (admin['emp_id'],))

    job_report = cursor.fetchall()

    # ---------------- AI ANALYTICS ----------------

    cursor.execute("""
        SELECT
            AVG(match_score) AS avg_score,
            MAX(match_score) AS top_score,
            MIN(match_score) AS low_score
        FROM applications a
        JOIN jobs j
        ON a.job_id=j.job_id
        WHERE j.emp_id=%s
    """, (admin['emp_id'],))

    analytics = cursor.fetchone()

    avg_score = round(analytics['avg_score'] or 0, 2)
    top_score = analytics['top_score'] or 0
    low_score = analytics['low_score'] or 0

    # ---------------- RATES ----------------

    selection_rate = 0
    rejection_rate = 0
    shortlist_rate = 0

    if total_applications > 0:

        selection_rate = round(
            (selected_count / total_applications) * 100,
            2
        )

        rejection_rate = round(
            (rejected_count / total_applications) * 100,
            2
        )

        shortlist_rate = round(
            (shortlisted_count / total_applications) * 100,
            2
        )

    return render_template(
        'reports.html',
        params=params,
        admin=admin,
        active_page='report',

        total_jobs=total_jobs,
        total_applications=total_applications,

        under_review=under_review,
        shortlisted_count=shortlisted_count,
        selected_count=selected_count,
        rejected_count=rejected_count,

        status_report=status_report,
        job_report=job_report,

        avg_score=avg_score,
        top_score=top_score,
        low_score=low_score,

        selection_rate=selection_rate,
        rejection_rate=rejection_rate,
        shortlist_rate=shortlist_rate
    )


# ---------------- SETTINGS ----------------

@app.route('/setting')
def setting():
    admin = get_logged_admin()
    if not admin:
        flash("Please login first.", "danger")
        return redirect('/login')

    return render_template(
        'settings.html',
        params=params,
        admin=admin,
        active_page='setting'
    )

# Update admin profile Route
@app.route('/admin/profile/update', methods=['POST'])
def update_admin_profile():
    admin = get_logged_admin()
    if not admin:
        flash("Please login first.", "danger")
        return redirect('/login')

    name = request.form.get('name')
    email = request.form.get('email')
    phn_no = request.form.get('phn_no')

    cursor.execute("""
        UPDATE admin
        SET name=%s, email_id=%s, phn_no=%s
        WHERE emp_id=%s
    """, (name, email, phn_no, admin['emp_id']))

    conn.commit()
    flash("Admin profile updated successfully.", "success")
    return redirect('/setting')

# update admin password route
@app.route('/admin/password/update', methods=['POST'])
def update_admin_password():
    admin = get_logged_admin()
    if not admin:
        flash("Please login first.", "danger")
        return redirect('/login')

    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if current_password != admin['password']:
        flash("Current password is incorrect.", "danger")
        return redirect('/setting')

    if new_password != confirm_password:
        flash("New password and confirm password do not match.", "danger")
        return redirect('/setting')

    cursor.execute("""
        UPDATE admin
        SET password=%s
        WHERE emp_id=%s
    """, (new_password, admin['emp_id']))

    conn.commit()
    flash("Password updated successfully.", "success")
    return redirect('/setting')


# Job Post Route
@app.route('/post_job', methods=['GET', 'POST'])
def post_job():

    admin = get_logged_admin()

    if not admin:
        flash("Please login first.", "danger")
        return redirect('/login')

    if request.method == 'POST':

        try:
            jd_file = request.files.get('jd_file')

            if not jd_file or jd_file.filename == '':
                flash("Please upload a JD PDF file.", "danger")
                return redirect('/post_job')

            if not jd_file.filename.lower().endswith('.pdf'):
                flash("Only PDF files are allowed.", "danger")
                return redirect('/post_job')

            original_filename = secure_filename(jd_file.filename)

            jd_filename = (
                f"{admin['emp_id']}_"
                f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_"
                f"{original_filename}"
            )

            jd_path = os.path.join(app.config['UPLOAD_FOLDER_JD'], jd_filename)
            jd_file.save(jd_path)

            parser = JobDescriptionParser(jd_path)
            jd_data = parser.parse()

            basic_info = jd_data.get("basic_info", {})
            common_eligibility = jd_data.get("common_eligibility", {})
            positions = jd_data.get("positions", [])

            company_name = (
                request.form.get("company_name")
                or basic_info.get("organization")
                or "BHEL"
            )

            location = request.form.get("location") or "Not Specified"
            status = request.form.get("status") or "Active"

            if not positions:
                job_title = request.form.get("job_title") or "Not Specified"
                qualification = (
                    common_eligibility.get("qualification_rule")
                    or "Not Specified"
                )

                cursor.execute("""
                    INSERT INTO jobs
                    (emp_id, job_title, company_name, location,
                     min_experience, qualification, jd_file_path,
                     posted_date, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    admin['emp_id'],
                    job_title,
                    company_name,
                    location,
                    1,
                    qualification[:45],
                    jd_filename,
                    datetime.date.today(),
                    status
                ))

                conn.commit()
                flash("Job posted successfully, but no FTA positions found.", "warning")
                return redirect('/manage_jobs')

            cursor.execute("""
                SELECT category_id
                FROM skill_category
                WHERE category_name=%s
            """, ("Technical Skills",))

            category = cursor.fetchone()

            if category:
                category_id = category["category_id"]
            else:
                cursor.execute("""
                    INSERT INTO skill_category (category_name)
                    VALUES (%s)
                """, ("Technical Skills",))
                category_id = cursor.lastrowid

            for position in positions:

                position_code = position.get("position_code", "")
                position_title = position.get("position_title") or "Not Specified"

                job_title = f"{position_title} ({position_code})"

                education = position.get("education", {})
                qualification = education.get("qualification_level") or "Not Specified"

                experience_required = position.get("experience_required", {})
                min_experience = experience_required.get("minimum_years") or 1

                cursor.execute("""
                    INSERT INTO jobs
                    (emp_id, job_title, company_name, location,
                     min_experience, qualification, jd_file_path,
                     posted_date, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    admin['emp_id'],
                    job_title[:45],
                    company_name[:45],
                    location[:45],
                    min_experience,
                    qualification[:45],
                    jd_filename,
                    datetime.date.today(),
                    status
                ))

                job_id = cursor.lastrowid

                required_skills = position.get("required_skills", [])

                for skill_item in required_skills:
                    skill_name = skill_item.get("skill", "")
                    skill_category = skill_item.get("skill_category", "Technical Skills")

                    if not skill_name:
                        continue

                    cursor.execute("""
                        SELECT category_id
                        FROM skill_category
                        WHERE category_name=%s
                    """, (skill_category,))

                    category_row = cursor.fetchone()

                    if category_row:
                        skill_category_id = category_row["category_id"]
                    else:
                        cursor.execute("""
                            INSERT INTO skill_category (category_name)
                            VALUES (%s)
                        """, (skill_category,))
                        skill_category_id = cursor.lastrowid

                    cursor.execute("""
                        INSERT INTO job_skills
                        (job_id, category_id, skill_name)
                        VALUES (%s, %s, %s)
                    """, (
                        job_id,
                        skill_category_id,
                        skill_name[:45]
                    ))

            conn.commit()
            flash("JD parsed and jobs posted successfully.", "success")
            return redirect('/manage_jobs')

        except Exception as e:
            conn.rollback()
            print("Post Job Error:", e)
            flash("Failed to post job.", "danger")
            return redirect('/post_job')

    return render_template(
        'post_job.html',
        params=params,
        admin=admin,
        active_page='manage_jobs'
    )
    
    
# update job Status Route
@app.route('/job/<int:job_id>/status/<string:new_status>')
def update_job_status(job_id, new_status):

    admin = get_logged_admin()

    if not admin:
        flash("Please login first.", "danger")
        return redirect('/login')

    if new_status not in ['Active', 'Closed']:
        flash("Invalid status.", "danger")
        return redirect('/manage_jobs')

    cursor.execute("""
        UPDATE jobs
        SET status=%s
        WHERE job_id=%s
        AND emp_id=%s
    """, (
        new_status,
        job_id,
        admin['emp_id']
    ))

    conn.commit()

    flash(f"Job marked as {new_status}.", "success")

    return redirect('/manage_jobs')

# Delte Job route
@app.route('/job/<int:job_id>/delete')
def delete_job(job_id):

    admin = get_logged_admin()

    if not admin:
        flash("Please login first.", "danger")
        return redirect('/login')

    try:
        cursor.execute("""
            SELECT COUNT(*) AS total_applications
            FROM applications
            WHERE job_id=%s
        """, (job_id,))

        total_applications = cursor.fetchone()['total_applications']

        if total_applications > 0:
            flash("This job has applications. Close it instead of deleting.", "warning")
            return redirect('/manage_jobs')

        cursor.execute("""
            DELETE FROM job_skills
            WHERE job_id=%s
        """, (job_id,))

        cursor.execute("""
            DELETE FROM jobs
            WHERE job_id=%s
            AND emp_id=%s
        """, (job_id, admin['emp_id']))

        conn.commit()

        flash("Job deleted successfully.", "success")

    except Exception as e:
        conn.rollback()
        print("Delete Job Error:", e)
        flash("Unable to delete job.", "danger")

    return redirect('/manage_jobs')

# Job Edit route
@app.route('/job/<int:job_id>/edit', methods=['GET', 'POST'])
def edit_job(job_id):

    admin = get_logged_admin()

    if not admin:
        flash("Please login first.", "danger")
        return redirect('/login')

    cursor.execute("""
        SELECT *
        FROM jobs
        WHERE job_id=%s
        AND emp_id=%s
    """, (
        job_id,
        admin['emp_id']
    ))

    job = cursor.fetchone()

    if not job:
        flash("Job not found.", "danger")
        return redirect('/manage_jobs')

    if request.method == 'POST':

        job_title = request.form.get('job_title')
        location = request.form.get('location')
        qualification = request.form.get('qualification')
        min_experience = request.form.get('min_experience')
        status = request.form.get('status')

        cursor.execute("""
            UPDATE jobs
            SET
                job_title=%s,
                location=%s,
                qualification=%s,
                min_experience=%s,
                status=%s
            WHERE job_id=%s
        """, (
            job_title,
            location,
            qualification,
            min_experience,
            status,
            job_id
        ))

        conn.commit()

        flash("Job updated successfully.", "success")

        return redirect('/manage_jobs')

    return render_template(
        'edit_job.html',
        params=params,
        admin=admin,
        job=job,
        active_page='manage_jobs'
    )

# Export route
@app.route('/report/export/csv')
def export_report_csv():

    admin = get_logged_admin()

    if not admin:
        flash("Please login first.", "danger")
        return redirect('/login')

    cursor.execute("""
        SELECT
            a.application_id,
            ap.name AS candidate_name,
            ap.email_id,
            ap.phn_no,
            j.job_title,
            a.application_date,
            a.match_score,
            a.status
        FROM applications a
        JOIN applicant ap
        ON a.applicant_id = ap.applicant_id
        JOIN jobs j
        ON a.job_id = j.job_id
        WHERE j.emp_id=%s
        ORDER BY a.application_date DESC
    """, (admin['emp_id'],))

    rows = cursor.fetchall()

    output = StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "Application ID",
        "Candidate Name",
        "Email",
        "Phone",
        "Job Title",
        "Application Date",
        "Match Score",
        "Status"
    ])

    for row in rows:
        writer.writerow([
            row["application_id"],
            row["candidate_name"],
            row["email_id"],
            row["phn_no"],
            row["job_title"],
            row["application_date"],
            row["match_score"],
            row["status"]
        ])

    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=recruitment_report.csv"
        }
    )
    
# applicant profile
@app.route('/admin/applicant/<int:application_id>')
def admin_applicant_detail(application_id):

    admin = get_logged_admin()

    if not admin:
        flash("Please login first.", "danger")
        return redirect('/login')

    cursor.execute("""
        SELECT
            a.application_id,
            a.application_date,
            a.match_score,
            a.status,
            a.resume_uploaded,

            ap.applicant_id,
            ap.name,
            ap.email_id,
            ap.phn_no,
            ap.linkedin_url,
            ap.github_url,
            ap.total_experience,

            p.dob,
            p.gender,
            p.nationality,
            p.address,
            p.degree,
            p.branch,
            p.university,
            p.g_year,
            p.cgpa,
            p.profile_img,

            j.job_id,
            j.job_title,
            j.company_name,
            j.location,
            j.qualification,
            j.min_experience

        FROM applications a
        JOIN applicant ap ON a.applicant_id = ap.applicant_id
        JOIN jobs j ON a.job_id = j.job_id
        LEFT JOIN profile_applicant p ON ap.applicant_id = p.applicant_id
        WHERE a.application_id=%s
        AND j.emp_id=%s
    """, (application_id, admin['emp_id']))

    applicant = cursor.fetchone()

    if not applicant:
        flash("Applicant not found.", "danger")
        return redirect('/applicants')

    return render_template(
        'admin_applicant_detail.html',
        params=params,
        admin=admin,
        applicant=applicant,
        active_page='applicants'
    )
    
@app.route('/job/<int:job_id>/details/<string:applicant_id>')
def job_details(job_id, applicant_id):

    if 'user_id' not in session:
        flash("Please login first.", "danger")
        return redirect('/login')

    if str(session['user_id']) != str(applicant_id):
        flash("Unauthorized access.", "danger")
        return redirect('/login')

    cursor.execute("""
        SELECT *
        FROM applicant
        WHERE applicant_id=%s
    """, (applicant_id,))
    applicant = cursor.fetchone()

    cursor.execute("""
        SELECT *
        FROM jobs
        WHERE job_id=%s
        AND status='Active'
    """, (job_id,))
    job = cursor.fetchone()

    if not job:
        flash("Job not found or closed.", "danger")
        return redirect(f'/jobs/{applicant_id}')

    cursor.execute("""
        SELECT skill_name
        FROM job_skills
        WHERE job_id=%s
    """, (job_id,))
    skills = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM applications
        WHERE applicant_id=%s
        AND job_id=%s
    """, (applicant_id, job_id))
    application = cursor.fetchone()

    already_applied = True if application else False

    return render_template(
        'job_details.html',
        params=params,
        applicant=applicant,
        job=job,
        skills=skills,
        already_applied=already_applied,
        active_page='jobs'
    )
    
# Applicant application details
@app.route('/applicant/application/<int:application_id>')
def applicant_application_detail(application_id):

    if 'user_id' not in session:
        flash("Please login first.", "danger")
        return redirect('/login')

    applicant_id = session['user_id']

    cursor.execute("""
        SELECT *
        FROM applicant
        WHERE applicant_id=%s
    """, (applicant_id,))
    applicant = cursor.fetchone()

    cursor.execute("""
        SELECT
            a.application_id,
            a.application_date,
            a.match_score,
            a.status,
            a.resume_uploaded,
            a.upload_date,

            j.job_id,
            j.job_title,
            j.company_name,
            j.location,
            j.min_experience,
            j.qualification,
            j.posted_date

        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        WHERE a.application_id=%s
        AND a.applicant_id=%s
    """, (application_id, applicant_id))

    application = cursor.fetchone()

    if not application:
        flash("Application not found.", "danger")
        return redirect(f'/applicant/applications/{applicant_id}')

    return render_template(
        'application_detail.html',
        params=params,
        applicant=applicant,
        application=application,
        active_page='applications'
    )
    
    
# AI engine integration

# Helper
def extract_position_code_from_job_title(job_title):
    match = re.search(r"FTA-\d+", job_title, re.I)
    return match.group(0).upper() if match else ""

# Run ai screening
@app.route('/run_ai_screening/<int:job_id>')
def run_ai_screening(job_id):

    admin = get_logged_admin()

    if not admin:
        flash("Please login first.", "danger")
        return redirect('/login')

    try:
        cursor.execute("""
            SELECT *
            FROM jobs
            WHERE job_id=%s AND emp_id=%s
        """, (job_id, admin['emp_id']))

        job = cursor.fetchone()

        if not job:
            flash("Job not found.", "danger")
            return redirect('/ai_screen')

        position_code = extract_position_code_from_job_title(job['job_title'])

        if not position_code:
            flash("FTA position code not found in job title.", "danger")
            return redirect('/ai_screen')

        jd_path = os.path.join(
            app.config['UPLOAD_FOLDER_JD'],
            job['jd_file_path']
        )

        if not os.path.exists(jd_path):
            flash("JD file not found.", "danger")
            return redirect('/ai_screen')

        jd_parser = JobDescriptionParser(jd_path)
        jd_data = jd_parser.parse()

        cursor.execute("""
            SELECT
                a.application_id,
                a.resume_uploaded,
                ap.name
            FROM applications a
            JOIN applicant ap ON a.applicant_id = ap.applicant_id
            WHERE a.job_id=%s
        """, (job_id,))

        applications = cursor.fetchall()

        if not applications:
            flash("No applications found for this job.", "warning")
            return redirect('/ai_screen')

        screened_count = 0

        for application in applications:

            if not application['resume_uploaded']:
                continue

            resume_path = os.path.join(
                app.config['UPLOAD_FOLDER_RESUME'],
                application['resume_uploaded']
            )

            if not os.path.exists(resume_path):
                continue

            resume_data = parse_resume(resume_path)

            result = rank_single_candidate(
                resume_data,
                jd_data,
                position_code
            )

            final_score = result.get("final_score", 0)

            if final_score >= 80:
                status = "Shortlisted"
            elif final_score >= 60:
                status = "Under Review"
            else:
                status = "Rejected"

            cursor.execute("""
                UPDATE applications
                SET match_score=%s,
                    status=%s
                WHERE application_id=%s
            """, (
                final_score,
                status,
                application['application_id']
            ))

            conn.commit()
            screened_count += 1

        flash(f"AI screening completed for {screened_count} candidates.", "success")
        return redirect('/ai_screen')

    except Exception as e:
        conn.rollback()
        print("AI Screening Error:", e)
        flash("AI screening failed.", "danger")
        return redirect('/ai_screen')

# candidate data visible route
@app.route('/candidate_ai_analysis/<int:application_id>')
def candidate_ai_analysis(application_id):

    admin = get_logged_admin()

    if not admin:
        flash("Please login first.", "danger")
        return redirect('/login')

    cursor.execute("""
        SELECT
            a.*,
            ap.name,
            ap.email_id,
            ap.phn_no,
            j.job_title,
            j.jd_file_path

        FROM applications a
        JOIN applicant ap
            ON a.applicant_id = ap.applicant_id
        JOIN jobs j
            ON a.job_id = j.job_id

        WHERE a.application_id=%s
    """, (application_id,))

    application = cursor.fetchone()

    if not application:
        flash("Application not found.", "danger")
        return redirect('/ai_screen')

    resume_path = os.path.join(
        app.config['UPLOAD_FOLDER_RESUME'],
        application['resume_uploaded']
    )

    jd_path = os.path.join(
        app.config['UPLOAD_FOLDER_JD'],
        application['jd_file_path']
    )

    resume_data = parse_resume(resume_path)

    jd_data = JobDescriptionParser(jd_path).parse()

    position_code = extract_position_code_from_job_title(
        application['job_title']
    )

    result = rank_single_candidate(
        resume_data,
        jd_data,
        position_code
    )
    skill_details = result.get("skill_details", {})

    matched_skills = (
        skill_details.get("matched_skills", [])
        + skill_details.get("core_matched_skills", [])
        + skill_details.get("bonus_matched_skills", [])
        + skill_details.get("common_matched_skills", [])
        + skill_details.get("best_group_matched_skills", [])
    )

    missing_skills = (
        skill_details.get("missing_skills", [])
        + skill_details.get("core_missing_skills", [])
        + skill_details.get("bonus_missing_skills", [])
        + skill_details.get("common_missing_skills", [])
        + skill_details.get("best_group_missing_skills", [])
    )

    resume_skills = skill_details.get("resume_skills", [])
    return render_template(
    'candidate_ai_analysis.html',
    params=params,
    admin=admin,
    application=application,
    result=result,
    matched_skills=matched_skills,
    missing_skills=missing_skills,
    resume_skills=resume_skills,
    active_page='ai_screen'
)


# Support Page
@app.route('/support/<string:applicant_id>', methods=['GET', 'POST'])
def support(applicant_id):

    if 'user_id' not in session:
        flash("Please login first.", "danger")
        return redirect('/login')

    if str(session['user_id']) != str(applicant_id):
        flash("Unauthorized access.", "danger")
        return redirect('/login')

    cursor.execute("""
        SELECT *
        FROM applicant
        WHERE applicant_id=%s
    """, (applicant_id,))
    applicant = cursor.fetchone()

    if request.method == 'POST':
        subject = request.form.get('subject')
        message = request.form.get('message')

        try:
            msg = Message(
                subject=f"Support Request: {subject}",
                recipients=[app.config['MAIL_USERNAME']],
                body=f"""
New support request received.

Applicant Name: {applicant['name']}
Applicant ID: {applicant['applicant_id']}
Email: {applicant['email_id']}
Phone: {applicant['phn_no']}

Subject:
{subject}

Message:
{message}
"""
            )

            mail.send(msg)

            flash("Your message has been sent to support team.", "success")
            return redirect(f'/support/{applicant_id}')

        except Exception as e:
            print("Support Mail Error:", e)
            flash("Message could not be sent. Please try again.", "danger")

    return render_template(
        'support.html',
        params=params,
        applicant=applicant,
        active_page='support'
    )
    

app.run(debug=True)