# AI Resume Screening and Candidate Ranking System

## Project Overview

The **AI Resume Screening and Candidate Ranking System** is a web-based recruitment platform developed using **Flask**, **MySQL**, and **Natural Language Processing (NLP)** techniques. The system automates the recruitment process by parsing Job Descriptions (JDs), extracting information from candidate resumes, matching candidate skills with job requirements, ranking applicants based on AI-generated scores, and assisting recruiters in selecting the most suitable candidates.

This project was developed as part of an internship at **Bharat Heavy Electricals Limited (BHEL)**.

---

## Objectives

* Automate resume screening and candidate shortlisting.
* Reduce manual effort in recruitment.
* Improve candidate-job matching accuracy.
* Provide AI-based candidate ranking.
* Generate recruitment analytics and reports.

---

## Features

### Applicant Module

* Applicant Registration & Login
* Profile Management
* Resume Upload & Update
* Job Search & Filtering
* Job Application Submission
* Application Tracking
* Support / Contact Center

### Admin Module

* Admin Authentication
* Job Posting Management
* Job Description Upload
* Candidate Management
* Resume Screening
* AI-Based Candidate Ranking
* Candidate Analysis Dashboard
* Resume Preview
* Shortlisting & Selection
* Email Notifications
* Recruitment Reports

### AI Engine

* Resume Parsing
* Job Description Parsing
* Skill Extraction
* Education Matching
* Experience Matching
* Candidate Ranking
* Recommendation Generation

---

## Technology Stack

### Frontend

* HTML5
* CSS3
* JavaScript
* Jinja2 Templates

### Backend

* Python
* Flask

### Database

* MySQL

### Libraries Used

```text
Flask
mysql-connector-python
pdfplumber
spaCy
re
json
os
datetime
Flask-Mail
```

---

## System Architecture

```text
Applicant
    |
    V
Upload Resume
    |
    V
Resume Parser
    |
    V
Extract Skills / Education / Experience
    |
    V
AI Matching Engine
    |
    V
Job Description Parser
    |
    V
Candidate Ranking
    |
    V
Admin Dashboard
    |
    V
Shortlist / Reject / Select
    |
    V
Email Notification
```

---

## Database Tables

### Admin

```text
admin
```

Stores recruiter information.

### Applicant

```text
applicant
```

Stores applicant information.

### Jobs

```text
jobs
```

Stores job postings and uploaded job descriptions.

### Applications

```text
applications
```

Stores candidate applications and AI screening results.

---

## Project Structure

```text
AI_Resume_Screening/
│
├── app.py
├── config.json
│
├── static/
│   ├── css/
│   ├── assets/
│   ├── resume/
│   └── jd/
│
├── templates/
│
├── utils/
│   ├── pdf_reader.py
│   ├── resume_parser.py
│   ├── jd_parser.py
│   ├── skill_matcher.py
│   ├── ranking_engine.py
│
├── parsed_data/
│   ├── resumes/
│   └── jd/
│
└── README.md
```

---

## AI Screening Process

### Step 1: Job Description Parsing

The uploaded Job Description PDF is parsed to extract:

* Job Title
* Position Code
* Required Skills
* Educational Requirements
* Experience Requirements
* Vacancy Details

### Step 2: Resume Parsing

The uploaded Resume PDF is parsed to extract:

* Candidate Name
* Skills
* Education
* Experience
* Certifications
* Contact Information

### Step 3: Skill Matching

The system compares:

```text
Resume Skills
VS
JD Skills
```

and calculates a skill match percentage.

### Step 4: Candidate Ranking

Final score is calculated using:

```text
Final Score =
(0.65 × Skill Score)
+ (0.20 × Experience Score)
+ (0.15 × Education Score)
```

### Step 5: Recommendation

Based on final score:

```text
80% and Above     -> Highly Recommended
60% - 79%         -> Recommended
40% - 59%         -> Average Match
Below 40%         -> Not Recommended
```

---

## Email Notification System

The system automatically sends emails when:

### Selected Candidate

```text
Congratulations Email
```

### Future Scope

```text
Interview Invitation Email
Shortlist Notification Email
Rejection Email
```

---

## Installation

### Clone Repository

```bash
git clone https://github.com/your-repository-name.git
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Environment

Windows:

```bash
venv\Scripts\activate
```

Linux:

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Database

Create MySQL database:

```sql
CREATE DATABASE ai_resume_screening;
```

Import required tables.

### Run Application

```bash
python app.py
```

Application runs at:

```text
http://127.0.0.1:5000
```

---

## Testing Summary

| Module             | Status |
| ------------------ | ------ |
| Authentication     | Passed |
| Job Posting        | Passed |
| Resume Upload      | Passed |
| Resume Parsing     | Passed |
| JD Parsing         | Passed |
| Candidate Ranking  | Passed |
| AI Screening       | Passed |
| Resume Preview     | Passed |
| Email Notification | Passed |
| Reports            | Passed |

---

## Future Enhancements

* Interview Scheduling
* Advanced NLP Skill Matching
* Password Hashing
* AI Chatbot Support
* Candidate Recommendation Engine
* Recruitment Analytics Dashboard
* Multi-Company Recruitment Support
* Cloud Deployment

---

## Conclusion

The AI Resume Screening and Candidate Ranking System successfully automates the recruitment workflow by reducing manual resume screening efforts and providing objective AI-based candidate evaluation. The system improves recruitment efficiency, enhances candidate-job matching accuracy, and assists recruiters in making faster and more informed hiring decisions.

---

**Developed By:** 
**Organization:** Bharat Heavy Electricals Limited (BHEL)
**Technology:** Flask, MySQL, Python, NLP, HTML, CSS, JavaScript
**Project Type:** Internship Project – AI Resume Screeing and Ranking System