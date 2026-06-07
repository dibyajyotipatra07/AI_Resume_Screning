import re
import json
import pdfplumber


class JobDescriptionParser:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.text = ""
        self.tables = []

    def clean(self, value):
        if value is None:
            return ""

        value = str(value)
        value = value.replace("\n", " ")
        value = value.replace("￾", " ")
        value = value.replace("FTA -", "FTA-")
        value = re.sub(r"\s+", " ", value)

        return value.strip()

    def extract_pdf_content(self):
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                self.text += "\n" + (page.extract_text() or "")

                tables = page.extract_tables()
                for table in tables:
                    if table:
                        self.tables.append(table)

    def extract_basic_info(self):
        info = {}

        adv = re.search(
            r"Advertisement\s+No\.?\s*[:\-]?\s*([A-Z]+\s*\d+/\d+)",
            self.text,
            re.I
        )
        info["advertisement_no"] = self.clean(adv.group(1)) if adv else ""

        email = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", self.text)
        info["email"] = email.group(0) if email else ""

        org = re.search(r"(Bharat Heavy Electricals Limited)", self.text, re.I)
        info["organization"] = self.clean(org.group(1)) if org else ""

        total = re.search(r"NO OF VACANCIES ARE\s*(\d+)", self.text, re.I)
        info["total_vacancies"] = int(total.group(1)) if total else None

        age = re.search(r"UPPER AGE LIMIT:\s*(.*?)(?:\n|$)", self.text, re.I)
        info["upper_age_limit"] = self.clean(age.group(1)) if age else ""

        return info

    def extract_important_dates(self):
        dates = {}

        patterns = {
            "online_application_start": r"Start of Online Application Submission:\s*(.*)",
            "online_application_close": r"Close of Online Application Submission:\s*(.*)",
            "hard_copy_last_date": r"Last date of receipt of hard copy.*?:\s*(.*)",
            "far_flung_last_date": r"Last Date of receipt of Hard copies.*?areas\*?\s*:\s*(.*)"
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, self.text, re.I)
            dates[key] = self.clean(match.group(1)) if match else ""

        return dates

    def extract_qualification_summary(self):
        match = re.search(
            r"EDUCATIONAL QUALIFICATION REQUIREMENT:\s*(.*?)(?=DETAILS OF EXPERIENCE REQUIREMENTS:)",
            self.text,
            re.I | re.S
        )

        return self.clean(match.group(1)) if match else ""

    def extract_common_eligibility(self):
        return {
            "minimum_experience": "Minimum 1 year relevant post qualification work experience",
            "qualification_rule": self.extract_qualification_summary(),
            "upper_age_limit": self.extract_basic_info().get("upper_age_limit", "")
        }

    def extract_remuneration(self):
        remuneration = {}

        for table in self.tables:
            if not table or not table[0]:
                continue

            header = " ".join(self.clean(cell) for cell in table[0] if cell)

            if "POST" in header.upper() and "COMPENSATION" in header.upper():
                for row in table[1:]:
                    if len(row) >= 3:
                        post = self.clean(row[0])
                        compensation = self.clean(row[1])
                        medical = self.clean(row[2])

                        if post:
                            remuneration[post] = {
                                "compensation": compensation,
                                "medical_benefits": medical
                            }

        return remuneration

    def extract_education_details(self, discipline_text):
        text = discipline_text.lower()

        education = {
            "qualification_level": "",
            "allowed_branches": [],
            "minimum_marks": "60% aggregate, 50% for SC/ST",
            "mode": "Full-Time"
        }

        if "degree" in text:
            education["qualification_level"] = "Degree / B.Tech / B.E"
        elif "diploma" in text:
            education["qualification_level"] = "Diploma"

        branches = [
            "Electrical",
            "Electronics",
            "Instrumentation",
            "Mechanical"
        ]

        for branch in branches:
            if branch.lower() in text:
                education["allowed_branches"].append(branch)

        return education

    def extract_skills(self, text):
        text_lower = text.lower()

        skill_patterns = {
            "testing": [
                "control panel testing",
                "electrical testing",
                "testing",
                "commissioning"
            ],
            "automation_controls": [
                "dcs",
                "plc",
                "distributed controls system",
                "field instrumentation"
            ],
            "electrical_systems": [
                "generator controls",
                "excitation systems",
                "davr",
                "sync generator",
                "motors",
                "thyristor power converters",
                "substation",
                "switchyard controls",
                "sas",
                "electrical metering system",
                "electrical interface system"
            ],
            "production_pcb": [
                "wave-soldering",
                "wave soldering",
                "tht assembly",
                "soldering techniques",
                "pcb handling",
                "soldering defects",
                "thermal profiling",
                "troubleshooting",
                "quality acceptance standards"
            ],
            "cnc_mechanical": [
                "cnc",
                "turret punch",
                "press brake"
            ]
        }

        skills = []

        for category, keywords in skill_patterns.items():
            for keyword in keywords:
                if keyword in text_lower:
                    skills.append({
                        "skill": keyword.title(),
                        "skill_category": category
                    })

        unique = []
        seen = set()

        for item in skills:
            key = item["skill"].lower()
            if key not in seen:
                unique.append(item)
                seen.add(key)

        return unique

    def extract_fta_positions(self):
        positions = []
        last_position = ""

        for table in self.tables:
            table_text = " ".join(
                self.clean(cell)
                for row in table
                for cell in row
                if cell
            )

            if "FTA" not in table_text:
                continue

            for row in table:
                cleaned = [self.clean(cell) for cell in row]
                row_text = " ".join(cleaned)

                fta_match = re.search(r"FTA\s*-?\s*\d+", row_text, re.I)
                if not fta_match:
                    continue

                fta_code = fta_match.group(0).replace(" ", "").upper()

                if len(cleaned) < 7:
                    continue

                sl_no = cleaned[0]
                position = cleaned[1]
                function = cleaned[3]
                vacancy = cleaned[4]
                discipline = cleaned[5]
                experience = cleaned[6]

                if position:
                    last_position = position
                else:
                    position = last_position

                combined_skill_text = f"{function} {discipline} {experience}"

                positions.append({
                    "sl_no": sl_no,
                    "position_code": fta_code,
                    "position_title": position,
                    "job_category": position,
                    "function": function,
                    "vacancy": int(vacancy) if str(vacancy).isdigit() else vacancy,
                    "discipline": discipline,
                    "education": self.extract_education_details(discipline),
                    "experience_required": {
                        "minimum_years": 1,
                        "description": experience
                    },
                    "required_skills": self.extract_skills(combined_skill_text)
                })

        return positions

    def parse(self):
        self.extract_pdf_content()

        return {
            "basic_info": self.extract_basic_info(),
            "common_eligibility": self.extract_common_eligibility(),
            "important_dates": self.extract_important_dates(),
            "remuneration": self.extract_remuneration(),
            "positions": self.extract_fta_positions()
        }
