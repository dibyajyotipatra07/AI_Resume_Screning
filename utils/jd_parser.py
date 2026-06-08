import re
import pdfplumber


SKILL_NAME_MAP = {
    "testing": "Testing",
    "commissioning": "Commissioning",
    "erection": "Erection",

    "control panel testing": "Control Panel Testing",
    "electrical testing": "Electrical Testing",

    "dcs": "DCS",
    "plc": "PLC",
    "plcs": "PLC",
    "distributed controls system": "Distributed Control System",
    "distributed control system": "Distributed Control System",
    "field instrumentation": "Field Instrumentation",

    "generator controls": "Generator Controls",
    "excitation systems": "Excitation Systems",
    "davr": "DAVR",
    "sync generator": "Sync Generator",
    "motors": "Motors",
    "thyristor power converters": "Thyristor Power Converters",
    "substation": "Substation",
    "switchyard controls": "Switchyard Controls",
    "sas": "SAS",
    "electrical metering system": "Electrical Metering System",
    "electrical interface system": "Electrical Interface System",

    "wave-soldering": "Wave Soldering",
    "wave soldering": "Wave Soldering",
    "tht assembly": "THT Assembly",
    "soldering techniques": "Soldering Techniques",
    "pcb handling": "PCB Handling",
    "soldering defects": "Soldering Defects",
    "thermal profiling": "Thermal Profiling",
    "troubleshooting": "Troubleshooting",
    "quality acceptance standards": "Quality Acceptance Standards",

    "cnc": "CNC",
    "turret punch": "Turret Punch",
    "press brake": "Press Brake",
}


class JobDescriptionParser:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.text = ""
        self.tables = []

    def clean(self, value):
        if value is None:
            return ""

        value = str(value)

        replacements = {
            "\n": " ",
            "￾": " ",
            "FTA -": "FTA-",
            "Superviso r": "Supervisor",
            "Instrumentati on": "Instrumentation",
            "Exciation": "Excitation",
            "Exci tation": "Excitation",
            "controls system": "control system",
            "Distributed controls system": "Distributed control system",
        }

        for old, new in replacements.items():
            value = value.replace(old, new)

        value = re.sub(r"\s+", " ", value)

        return value.strip()

    def extract_pdf_content(self):
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                self.text += "\n" + (page.extract_text() or "")

                for table in page.extract_tables():
                    if table:
                        self.tables.append(table)

        self.text = self.clean(self.text)

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

        age = re.search(r"UPPER AGE LIMIT:\s*(.*?)(?:EDUCATIONAL|$)", self.text, re.I)
        info["upper_age_limit"] = self.clean(age.group(1)) if age else ""

        return info

    def extract_important_dates(self):
        dates = {}

        patterns = {
            "online_application_start": r"Start of Online Application Submission:\s*(.*?)(?:Close of Online|$)",
            "online_application_close": r"Close of Online Application Submission:\s*(.*?)(?:Last date|$)",
            "hard_copy_last_date": r"Last date of receipt of hard copy.*?:\s*(.*?)(?:Last Date|$)",
            "far_flung_last_date": r"Last Date of receipt of Hard copies.*?areas\*?\s*:\s*(.*?)(?:$)"
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
        text = self.clean(discipline_text).lower()

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

        for branch in ["Electrical", "Electronics", "Instrumentation", "Mechanical"]:
            if branch.lower() in text:
                education["allowed_branches"].append(branch)

        return education

    def extract_flat_skills(self, text):
        text = self.clean(text).lower()

        skill_patterns = {
            "testing": [
                "testing",
                "commissioning",
                "erection",
                "control panel testing",
                "electrical testing"
            ],
            "automation_controls": [
                "dcs",
                "plc",
                "plcs",
                "distributed control system",
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
        seen = set()

        for category, keywords in skill_patterns.items():
            for keyword in keywords:
                if keyword in text:
                    skill_name = SKILL_NAME_MAP.get(keyword, keyword.title())
                    key = skill_name.lower()

                    if key not in seen:
                        skills.append({
                            "skill": skill_name,
                            "skill_category": category
                        })
                        seen.add(key)

        return skills

    def build_skill_requirements(self, position_code):
        position_code = position_code.upper()

        if position_code == "FTA-1":
            return {
                "scoring_type": "weighted",
                "core_skills": [
                    "Control Panel Testing",
                    "Electrical Testing",
                    "Testing"
                ],
                "bonus_skills": [
                    "Relay Testing",
                    "FAT",
                    "SAT",
                    "Traction Panel Testing",
                    "Customer Acceptance Testing"
                ]
            }

        if position_code in ["FTA-2", "FTA-5"]:
            return {
                "scoring_type": "grouped_alternative",
                "common_skills": [
                    "Erection",
                    "Commissioning",
                    "Testing"
                ],
                "skill_groups": [
                    {
                        "group_name": "Automation and Control Systems",
                        "skills": [
                            "Distributed Control System",
                            "DCS",
                            "PLC",
                            "Field Instrumentation"
                        ]
                    },
                    {
                        "group_name": "Electrical Systems",
                        "skills": [
                            "Generator Controls",
                            "Excitation Systems",
                            "DAVR",
                            "Sync Generator",
                            "Motors",
                            "Thyristor Power Converters",
                            "Substation",
                            "Switchyard Controls",
                            "SAS",
                            "Electrical Metering System",
                            "Electrical Interface System"
                        ]
                    }
                ]
            }

        if position_code == "FTA-3":
            return {
                "scoring_type": "weighted",
                "core_skills": [
                    "Wave Soldering",
                    "THT Assembly",
                    "PCB Handling"
                ],
                "bonus_skills": [
                    "Soldering Techniques",
                    "Soldering Defects",
                    "Thermal Profiling",
                    "Troubleshooting",
                    "Quality Acceptance Standards"
                ]
            }

        if position_code == "FTA-4":
            return {
                "scoring_type": "weighted",
                "core_skills": [
                    "CNC",
                    "Turret Punch",
                    "Press Brake"
                ],
                "bonus_skills": [
                    "CNC Programming",
                    "CNC Operation",
                    "AutoCAD",
                    "Quality Assurance"
                ]
            }

        return {
            "scoring_type": "normal",
            "required_skills": []
        }

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

                position = self.clean(position)
                function = self.clean(function)
                discipline = self.clean(discipline)
                experience = self.clean(experience)

                combined_text = f"{function} {discipline} {experience}"

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
                    "required_skills": self.extract_flat_skills(combined_text),
                    "skill_requirements": self.build_skill_requirements(fta_code)
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