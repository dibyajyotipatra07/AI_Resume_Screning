import re
import spacy
from utils.pdf_reader import pdf_reader

nlp = spacy.load("en_core_web_sm")


MASTER_SKILLS = [
    "PLC", "DCS", "SCADA",
    "Control Panel Testing", "Electrical Testing",
    "Commissioning", "Testing",
    "Instrumentation", "Field Instrumentation",

    "Generator Controls", "Excitation Systems", "DAVR",
    "Substation", "Substation Automation",
    "Switchyard Controls", "SAS",
    "Electrical Metering System", "Electrical Interface System",
    "Thyristor Power Converters", "Relay Testing",

    "Wave Soldering", "PCB Assembly", "PCB Handling",
    "THT Assembly", "Soldering Techniques",
    "Soldering Defects", "Thermal Profiling",
    "Troubleshooting", "Quality Acceptance Standards",

    "CNC", "CNC Programming", "Turret Punch", "Press Brake",

    "FAT", "SAT", "AutoCAD", "MS Excel",
    "Quality Assurance", "Electrical Safety",
    "Industrial Automation"
]


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
    patterns = [
        r"(\d+)\+?\s+years?\s+of\s+experience",
        r"(\d+)\+?\s+years?\s+of\s+post qualification experience",
        r"(\d+)\+?\s+years?\s+of\s+hands[- ]on experience",
        r"(\d+)\+?\s+years?\s+of\s+site experience",
        r"(\d+)\+?\s+years?\s+experience"
    ]

    text = text.lower()

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))

    return 0


def extract_section(text, start_heading, end_headings):
    pattern = start_heading + r"(.*?)(?=" + "|".join(end_headings) + r"|$)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


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


def extract_skills(text):
    text_lower = text.lower()
    found_skills = []

    for skill in MASTER_SKILLS:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"

        if re.search(pattern, text_lower):
            found_skills.append(skill)

    return sorted(list(set(found_skills)))


def parse_resume(pdf_path):
    text = pdf_reader(pdf_path)

    role, match_label = extract_role_and_match(text)

    return {
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
        "resume_text": text
    }