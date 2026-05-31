from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
import json
import datetime
import os
from werkzeug.utils import secure_filename
from flask_mail import Mail

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


@app.route('/create')
def home():
    return render_template('create_page.html')


@app.route('/login')
def login():
    return render_template('login.html')

app.run(debug=True)