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


@app.route('/')
def home():
    return render_template('login_page.html')

app.run(debug=True)