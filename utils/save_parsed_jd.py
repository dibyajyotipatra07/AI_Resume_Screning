import os
import json
from utils.jd_parser import JobDescriptionParser


def save_jd_json(pdf_path, output_folder="parsed_data/jobs"):
    os.makedirs(output_folder, exist_ok=True)

    parser = JobDescriptionParser(pdf_path)
    jd_data = parser.parse()

    output_path = os.path.join(output_folder, "parsed_job.json")

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(jd_data, file, indent=4, ensure_ascii=False)

    return output_path


if __name__ == "__main__":
    pdf_path = "job.pdf"
    saved_path = save_jd_json(pdf_path)
    print(f"Saved: {saved_path}")