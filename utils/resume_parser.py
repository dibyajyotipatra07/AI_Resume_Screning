import re
import spacy
from pdf_reader import pdf_reader

nlp = spacy.load("en_core_web_sm")


def extract_email(text):
    pattern = r"[\w\.-]+@[\w\.-]+\.\w+"
    matches = re.findall(pattern, text)
    return matches[0] if matches else ""


def extract_phone(text):
    pattern = r"(?:\+91[-\s]?)?[6-9]\d{4}[-\s]?\d{5}"
    matches = re.findall(pattern, text)
    return matches[0] if matches else ""


def extract_linkedin(text):
    pattern = r"(?:https?:\/\/)?(?:www\.)?linkedin\.com\/in\/[\w-]+"
    matches = re.findall(pattern, text)
    return matches[0] if matches else ""


def extract_github(text):
    pattern = r"(?:https?:\/\/)?(?:www\.)?github\.com\/[\w-]+"
    matches = re.findall(pattern, text)
    return matches[0] if matches else ""


def extract_name(text):
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    if not lines:
        return ""

    first_line = lines[0]

    first_line = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "", first_line)
    first_line = re.sub(r"(?:\+91[-\s]?)?[6-9]\d{4}[-\s]?\d{5}", "", first_line)
    first_line = first_line.strip()

    doc = nlp(first_line)

    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text

    return first_line


def extract_role_and_match(text):
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    if len(lines) < 2:
        return "", ""

    second_line = lines[1]

    if "|" in second_line:
        role, match_label = second_line.split("|", 1)
        return role.strip(), match_label.strip()

    return second_line.strip(), ""
def extract_experience_years(text):
    pattern = r"(\d+)\+?\s+years?\s+of\s+experience"
    matches = re.findall(pattern, text.lower())
    return int(matches[0]) if matches else 0


def extract_section(text, start_heading, end_headings):
    pattern = start_heading + r"(.*?)(?=" + "|".join(end_headings) + r"|$)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


def extract_skills(text):
    skills_text = extract_section(
        text,
        "Technical Skills",
        ["Certifications", "Education", "Employment History", "Technical Project"]
    )

    if not skills_text:
        return []

    skills = [skill.strip() for skill in skills_text.replace("\n", " ").split(",")]
    return [skill for skill in skills if skill]


def extract_certifications(text):
    cert_text = extract_section(
        text,
        "Certifications",
        ["Education", "Technical Skills", "Employment History"]
    )

    if not cert_text:
        return []

    certs = [cert.strip() for cert in cert_text.replace("\n", " ").split(",")]
    return [cert for cert in certs if cert]


def extract_education(text):
    edu_text = extract_section(
        text,
        "Education",
        ["Technical Skills", "Certifications", "Employment History", "Technical Project"]
    )

    return edu_text.strip()

def parse_resume(pdf_path):
    text = pdf_reader(pdf_path)

    role, match_label = extract_role_and_match(text)

    data = {
        "name": extract_name(text),
        "target_role": role,
        "match_label": match_label,
        "email": extract_email(text),
        "phone": extract_phone(text),
        "linkedin": extract_linkedin(text),
        "github": extract_github(text),
        "experience_years": extract_experience_years(text),
        "skills": extract_skills(text),
        "certifications": extract_certifications(text),
        "education": extract_education(text),
        "raw_text": text
    }

    return data

