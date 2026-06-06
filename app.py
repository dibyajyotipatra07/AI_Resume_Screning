from flask import Flask, render_template, request, redirect, session, flash, send_file
# Importing Mysql Connector
import mysql.connector
# Importing JSON
import json
import datetime
import os
# Imporitng secur_file for safe files
from werkzeug.utils import secure_filename
# importing for mailing
from flask_mail import Mail

# Importing functions from utils to work on resume screening and ranking
from utils.pdf_reader import pdf_reader
from utils.resume_parser import extract_email, extract_phn, extract_name, extract_git, extract_linkedin

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
    linkedin_url VARCHAR(45) DEFAULT NULL,
    github_url VARCHAR(45) DEFAULT NULL,
    total_experience VARCHAR(45) DEFAULT NULL,
    resume_file_name VARCHAR(60) NOT NULL,
    upload_date DATE NOT NULL,
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
    match_score DECIMAL(5,0) DEFAULT NULL,
    status VARCHAR(45) DEFAULT NULL,
    resume_uploaded VARCHAR(45) NOT NULL,
    PRIMARY KEY (application_id),
    UNIQUE KEY application_id_UNIQUE (application_id),
    KEY `appliation to job_idx` (job_id),
    KEY `applicant applications_idx` (applicant_id),
    CONSTRAINT `appliation to job` FOREIGN KEY (job_id) REFERENCES jobs (job_id),
    CONSTRAINT `applicant applications` FOREIGN KEY (applicant_id) REFERENCES applicant (applicant_id)
);
""")

# Certifications Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS certifications (
    cert_id INT NOT NULL AUTO_INCREMENT,
    applicant_id INT NOT NULL,
    cert_name VARCHAR(45) NOT NULL,
    issuer VARCHAR(45) NOT NULL,
    PRIMARY KEY (cert_id),
    UNIQUE KEY cert_id_UNIQUE (cert_id),
    KEY `certificate earnd_idx` (applicant_id),
    CONSTRAINT `certificate earnd` FOREIGN KEY (applicant_id) REFERENCES applicant (applicant_id)
);
""")

# Education Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS education (
    education_id int NOT NULL AUTO_INCREMENT,
    applicant_id int NOT NULL,
    degree varchar(45) NOT NULL,
    specialization varchar(45) NOT NULL,
    institution varchar(45) NOT NULL,
    end_year year NOT NULL,
    cgpa decimal(4,0) NOT NULL,
    PRIMARY KEY (education_id),
    UNIQUE KEY education_id_UNIQUE (education_id),
    KEY applicant_id_idx (applicant_id),
    CONSTRAINT `education to aplicant` FOREIGN KEY (applicant_id) REFERENCES applicant (applicant_id)
);
""")

# Experience Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS experience (
    exp_id INT NOT NULL AUTO_INCREMENT,
    applicant_id INT NOT NULL,
    company_name VARCHAR(45) NOT NULL,
    designation VARCHAR(45) NOT NULL,
    working_year INT NOT NULL,
    description VARCHAR(45) DEFAULT NULL,
    PRIMARY KEY (exp_id),
    UNIQUE KEY exp_id_UNIQUE (exp_id),
    KEY `experience of applicant_idx` (applicant_id),
    CONSTRAINT `experience of applicant` FOREIGN KEY (applicant_id) REFERENCES applicant (applicant_id)
);
""")

# Internship Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS internship (
    intern_id INT NOT NULL AUTO_INCREMENT,
    applicant_id INT NOT NULL,
    company_name VARCHAR(45) NOT NULL,
    role VARCHAR(45) NOT NULL,
    description VARCHAR(45) DEFAULT NULL,
    PRIMARY KEY (intern_id),
    UNIQUE KEY intern_id_UNIQUE (intern_id),
    KEY `internships done by applicant_idx` (applicant_id),
    CONSTRAINT `internships done by applicant` FOREIGN KEY (applicant_id) REFERENCES applicant (applicant_id)
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

#Projects Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS projects (
    project_id INT NOT NULL AUTO_INCREMENT,
    applicant_id INT NOT NULL,
    project_title VARCHAR(100) NOT NULL,
    description VARCHAR(45) DEFAULT NULL,
    github_link VARCHAR(45) DEFAULT NULL,
    PRIMARY KEY (project_id),
    UNIQUE KEY `project_id_UNIQUE` (project_id),
    KEY `projects done_idx` (applicant_id),
    CONSTRAINT `projects done` FOREIGN KEY (applicant_id) REFERENCES applicant (applicant_id)
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

#Skills Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS skills (
    skill_record_id INT NOT NULL AUTO_INCREMENT,
    applicant_id INT NOT NULL,
    category_id INT NOT NULL,
    skill_name VARCHAR(45) NOT NULL,
    PRIMARY KEY (skill_record_id),
    KEY `skill category_idx` (category_id),
    KEY `applicant skill_idx` (applicant_id),
    CONSTRAINT `applicant skill` FOREIGN KEY (applicant_id) REFERENCES applicant (applicant_id),
    CONSTRAINT `skill category` FOREIGN KEY (category_id) REFERENCES skill_category (category_id)
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

# Configure upload folder for Job Descriptions
app.config['UPLOAD_FOLDER_JD'] = params['upload_location_jd']
# Configure upload folder for Resumes
app.config['UPLOAD_FOLDER_RESUME'] = params['upload_location_resume']
# Configure upload folder for Profile Pictures
app.config['UPLOAD_FOLDER_PROFILE_PICTURE'] = params['upload_location_pf']

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
                resume_file = request.files['resume']
                cursor.execute("INSERT INTO applicant (name, phn_no, email_id, password, resume_file_name, upload_date) VALUES (%s, %s, %s, %s, %s, %s)",
                (fullname, mobile_number, email, password, '', datetime.date.today()))
                applicant_id = cursor.lastrowid
                cursor.execute("INSERT INTO applicant_profile (applicant_id, email, phn_no) VALUES (%s, %s, %s)", (applicant_id, email, mobile_number))
                conn.commit()
                resume_filename = f"{applicant_id}_Resume.pdf"
                resume_file.save(os.path.join(app.config['UPLOAD_FOLDER_RESUME'], resume_filename))
                # update the resume file name in the database
                cursor.execute("UPDATE applicant SET resume_file_name = %s WHERE applicant_id = %s", (resume_filename, applicant_id))
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

# Dashboard route for both admin and applicant
@app.route('/dashboard/<string:role>/<string:applicant_id>')
def dashboard(role, applicant_id):
    if 'user_id' in session:
        if session['role']  == 'admin':
            cursor.execute("SELECT * FROM admin WHERE emp_id = %s", (session['user_id'],))
            admin = cursor.fetchone()
            return render_template('dashboard_admin.html', params=params, admin=admin, active_page='dashboard')
        
        elif session['role'] == 'applicant':
            applicant_id = session['user_id']
            cursor.execute("SELECT * FROM applicant WHERE applicant_id = %s", (applicant_id,))
            applicant = cursor.fetchone()
            cursor.execute("SELECT * FROM profile_applicant WHERE applicant_id = %s", (applicant_id,))
            applicant_profile = cursor.fetchone()
            return render_template('dashboard_applicant.html', params=params, applicant=applicant, applicant_profile = applicant_profile, active_page='dashboard')
    flash("Invalid session", "danger")
    return redirect('/login')

# Route to handle resume update
@app.route('/applicant/<string:applicant_id>/resume/update', methods=['POST'])
def update_resume(applicant_id):

    if 'user_id' not in session:
        flash("Please login first.", "danger")
        return redirect('/login')

    try:
        applicant_id = session['user_id']
        resume_file = request.files.get('resume_upload')

        if not resume_file or resume_file.filename == '':
            flash("Please select a PDF file.", "danger")
            return redirect(f'/dashboard/applicant/{session["user_id"]}')

        if not resume_file.filename.lower().endswith('.pdf'):
            flash("Only PDF files are allowed.", "danger")
            return redirect(f'/dashboard/applicant/{session["user_id"]}')

        resume_filename = f"{applicant_id}_Resume.pdf"

        resume_file.save(os.path.join(app.config['UPLOAD_FOLDER_RESUME'],resume_filename))

        cursor.execute("UPDATE applicant SET resume_file_name = %s, upload_date = %s WHERE applicant_id = %s", ( resume_filename, datetime.date.today(), applicant_id))
        conn.commit()
        flash("Resume updated successfully!", "success")

    except Exception as e:
        conn.rollback()
        print("Error:", e)
        flash("Failed to update resume.", "danger")

    return redirect(f'/dashboard/applicant/{session["user_id"]}')

# Route to display applicant's applications
@app.route('/applicant/applications/<string:applicant_id>')
def application(applicant_id):
    cursor.execute("SELECT * FROM applicant WHERE applicant_id = %s", (applicant_id,))
    applicant = cursor.fetchone()
    return render_template('my_applications.html', params=params, applicant= applicant, active_page='applications')

# Route to display available jobs to the applicant
@app.route('/jobs/<string:applicant_id>')
def find_jobs(applicant_id):
    cursor.execute("SELECT * FROM applicant WHERE applicant_id = %s", (applicant_id,))
    applicant = cursor.fetchone()
    return render_template('find_jobs.html', params=params, applicant= applicant, active_page='jobs')

# Route to display applicant's resume
@app.route('/applicant/resume/<string:applicant_id>')
def view_resume(applicant_id):
    cursor.execute("SELECT * FROM applicant WHERE applicant_id = %s", (applicant_id,))
    applicant = cursor.fetchone()
    return render_template('my_resume.html', params=params, applicant= applicant, active_page='resume')

# Route to display applicant's profile
@app.route('/applicant/profile/<string:applicant_id>')
def profile_applicant(applicant_id):
    if 'user_id' not in session:
        flash("Please login first.", "danger")
        return redirect('/login')
    applicant_id = session['user_id']
    cursor.execute("SELECT * FROM profile_applicant WHERE applicant_id = %s", (applicant_id,))
    applicant = cursor.fetchone()
    return render_template('profile.html', params=params, applicant= applicant, active_page='profile', role=session['role'].upper())

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
        print("Error:", e)
        flash("Failed to update Profile.", "danger")
        return redirect(f'/dashboard/applicant/{session["user_id"]}')
    return render_template('edit_profile.html', params=params, applicant= applicant)

# Route to handle applicant logout
@app.route('/applicant/logout/<string:applicant_id>')
def applicant_logout(applicant_id):
    role = session.get('role').upper()
    cursor.execute("SELECT * FROM applicant WHERE applicant_id = %s", (applicant_id,))
    applicant = cursor.fetchone()
    return render_template('logout.html', params=params, applicant= applicant, role=role)

# Route to handle logout for both admin and applicant
@app.route('/logout')
def logout():  
    session.clear()
    return redirect('/')

# Route to preview applicant's resume
@app.route('/preview_resume/<int:applicant_id>')
def preview_resume(applicant_id):
    cursor.execute("SELECT resume_file_name FROM applicant WHERE applicant_id=%s",(applicant_id,))
    applicant = cursor.fetchone()
    file_path = os.path.join(app.config['UPLOAD_FOLDER_RESUME'],applicant['resume_file_name'])
    return send_file(file_path)

# Route to download applicant's resume
@app.route('/download_resume/<int:applicant_id>')
def download_resume(applicant_id):
    cursor.execute("SELECT resume_file_name FROM applicant WHERE applicant_id=%s",(applicant_id,))
    applicant = cursor.fetchone()
    print(applicant)
    file_path = os.path.join(app.config['UPLOAD_FOLDER_RESUME'],applicant['resume_file_name'])
    return send_file(file_path,as_attachment=True)

# Contact Page
@app.route('/contact')
def contact():
    return render_template('home_page.html', params=params)

app.run(debug=True)