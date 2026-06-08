import os
import json
import re
from skill_matcher import load_json, match_skills


def get_position(jd_data, position_code):
    for position in jd_data.get("positions", []):
        if position.get("position_code", "").upper() == position_code.upper():
            return position
    return None


def extract_resume_position_code(resume_data):
    text = resume_data.get("target_role", "")
    match = re.search(r"FTA-\d+", text, re.I)
    return match.group(0).upper() if match else ""


def is_candidate_applied_for_position(resume_data, position_code):
    return extract_resume_position_code(resume_data) == position_code.upper()


def calculate_experience_score(resume_data, position):
    candidate_exp = resume_data.get("experience_years", 0)
    position_code = position.get("position_code", "")

    ideal_experience = {
        "FTA-1": 5,
        "FTA-2": 6,
        "FTA-3": 5,
        "FTA-4": 4,
        "FTA-5": 5
    }

    ideal_years = ideal_experience.get(position_code, 3)

    score = (candidate_exp / ideal_years) * 100

    return round(min(score, 100), 2)


def calculate_education_score(resume_data, position):
    resume_edu = resume_data.get("education", "").lower()
    required_edu = position.get("education", {})

    qualification = required_edu.get("qualification_level", "").lower()
    branches = required_edu.get("allowed_branches", [])

    score = 0

    if "degree" in qualification:
        if any(word in resume_edu for word in ["degree", "b.tech", "b.e", "engineering"]):
            score += 50

    if "diploma" in qualification:
        if any(word in resume_edu for word in ["diploma", "engineering"]):
            score += 50

    for branch in branches:
        if branch.lower() in resume_edu:
            score += 50
            break

    return min(score, 100)


def rank_single_candidate(resume_data, jd_data, position_code):
    position = get_position(jd_data, position_code)

    if not position:
        return None

    skill_result = match_skills(resume_data, jd_data, position_code)

    skill_score = skill_result.get("final_skill_score", 0)
    experience_score = calculate_experience_score(resume_data, position)
    education_score = calculate_education_score(resume_data, position)

    final_score = (
        skill_score * 0.65 +
        experience_score * 0.20 +
        education_score * 0.15
    )

    return {
        "candidate_name": resume_data.get("name", ""),
        "applied_role": resume_data.get("target_role", ""),
        "position_code": position_code,
        "position_title": position.get("position_title", ""),
        "function": position.get("function", ""),

        "skill_score": round(skill_score, 2),
        "experience_score": round(experience_score, 2),
        "education_score": round(education_score, 2),
        "final_score": round(final_score, 2),

        "skill_matching_type": skill_result.get("scoring_type", ""),
        "skill_details": skill_result
    }


def rank_all_resumes_for_job(resume_folder, jd_path, position_code):
    jd_data = load_json(jd_path)

    results = []

    for file in os.listdir(resume_folder):
        if file.lower().endswith(".json"):
            resume_path = os.path.join(resume_folder, file)

            with open(resume_path, "r", encoding="utf-8") as f:
                resume_data = json.load(f)

            if not is_candidate_applied_for_position(resume_data, position_code):
                continue

            result = rank_single_candidate(resume_data, jd_data, position_code)

            if result:
                results.append(result)

    results.sort(key=lambda x: x["final_score"], reverse=True)

    for index, item in enumerate(results, start=1):
        item["rank"] = index

    return results


def rank_all_jobs(resume_folder, jd_path):
    jd_data = load_json(jd_path)

    all_job_results = {}

    for position in jd_data.get("positions", []):
        position_code = position.get("position_code")

        ranked_candidates = rank_all_resumes_for_job(
            resume_folder=resume_folder,
            jd_path=jd_path,
            position_code=position_code
        )

        all_job_results[position_code] = ranked_candidates

    return all_job_results


def save_ranking_results(results, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=4, ensure_ascii=False)

    return output_path