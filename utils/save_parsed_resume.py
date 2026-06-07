import os
import json
from resume_parser import parse_resume


def clean_filename(name):
    if not name:
        return "unknown_candidate"

    name = name.strip().replace(" ", "_")
    return "".join(ch for ch in name if ch.isalnum() or ch in "_-")


def save_resume_json(pdf_path, output_folder="parsed_data/resumes"):
    os.makedirs(output_folder, exist_ok=True)

    resume_data = parse_resume(pdf_path)

    candidate_name = clean_filename(resume_data.get("name", ""))
    json_filename = f"{candidate_name}_parsed_resume.json"

    output_path = os.path.join(output_folder, json_filename)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(resume_data, file, indent=4, ensure_ascii=False)

    return output_path


if __name__ == "__main__":
    pdf_path = "sample_resumes/Weak_2_Ritika_Jain.pdf"

    saved_path = save_resume_json(pdf_path)

    print("Parsed resume JSON saved successfully:")
    print(saved_path)