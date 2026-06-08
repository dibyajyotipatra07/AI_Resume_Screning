import re
import json
from sentence_transformers import SentenceTransformer, util


model = SentenceTransformer("all-MiniLM-L6-v2")


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def normalize_skill(skill):
    skill = skill.lower().strip()
    skill = skill.replace("-", " ")
    skill = skill.replace("/", " ")
    skill = skill.replace("&", " and ")
    skill = re.sub(r"\s+", " ", skill)

    synonym_map = {
        "plcs": "plc",
        "programmable logic controller": "plc",
        "programmable logic controllers": "plc",

        "distributed controls system": "dcs",
        "distributed control system": "dcs",
        "distributed control systems": "dcs",

        "substation automation system": "sas",
        "substation automation": "sas",

        "digital automatic voltage regulator": "davr",

        "wave soldering machine": "wave soldering",

        "field instruments": "field instrumentation",
        "instrumentation": "field instrumentation",

        "panel testing": "control panel testing",
        "control panels testing": "control panel testing",

        "electrical system testing": "electrical testing",

        "cnc programming": "cnc",
        "cnc operation": "cnc",

        "ms excel": "excel"
    }

    return synonym_map.get(skill, skill)


def get_position_by_code(jd_data, position_code):
    for position in jd_data.get("positions", []):
        if position.get("position_code", "").upper() == position_code.upper():
            return position

    return None


def calculate_skill_score(resume_skills, jd_skills, threshold=0.55):
    if not resume_skills or not jd_skills:
        return {
            "score": 0,
            "matched_skills": [],
            "missing_skills": jd_skills,
            "details": []
        }

    normalized_resume = [normalize_skill(skill) for skill in resume_skills]
    normalized_jd = [normalize_skill(skill) for skill in jd_skills]

    resume_embeddings = model.encode(normalized_resume, convert_to_tensor=True)
    jd_embeddings = model.encode(normalized_jd, convert_to_tensor=True)

    similarity_matrix = util.cos_sim(jd_embeddings, resume_embeddings)

    matched = []
    missing = []
    details = []

    for i, jd_skill in enumerate(jd_skills):
        best_score = float(similarity_matrix[i].max())
        best_index = int(similarity_matrix[i].argmax())

        best_resume_skill = resume_skills[best_index]

        exact_match = normalized_jd[i] in normalized_resume
        semantic_match = best_score >= threshold
        final_match = exact_match or semantic_match

        if final_match:
            matched.append(jd_skill)
        else:
            missing.append(jd_skill)

        details.append({
            "jd_skill": jd_skill,
            "best_resume_skill": best_resume_skill,
            "similarity": round(best_score * 100, 2),
            "exact_match": exact_match,
            "semantic_match": semantic_match,
            "matched": final_match
        })

    score = (len(matched) / len(jd_skills)) * 100

    return {
        "score": round(score, 2),
        "matched_skills": matched,
        "missing_skills": missing,
        "details": details
    }


def normal_skill_matching(resume_skills, skill_requirements):
    jd_skills = skill_requirements.get("required_skills", [])

    result = calculate_skill_score(resume_skills, jd_skills)

    return {
        "scoring_type": "normal",
        "final_skill_score": result["score"],
        "matched_skills": result["matched_skills"],
        "missing_skills": result["missing_skills"],
        "match_details": result["details"]
    }


def grouped_skill_matching(resume_skills, skill_requirements):
    common_skills = skill_requirements.get("common_skills", [])
    skill_groups = skill_requirements.get("skill_groups", [])

    common_result = calculate_skill_score(resume_skills, common_skills)

    group_results = []

    for group in skill_groups:
        group_result = calculate_skill_score(
            resume_skills,
            group.get("skills", [])
        )

        group_results.append({
            "group_name": group.get("group_name", ""),
            "score": group_result["score"],
            "matched_skills": group_result["matched_skills"],
            "missing_skills": group_result["missing_skills"],
            "details": group_result["details"]
        })

    if group_results:
        best_group = max(group_results, key=lambda x: x["score"])
    else:
        best_group = {
            "group_name": "",
            "score": 0,
            "matched_skills": [],
            "missing_skills": [],
            "details": []
        }

    final_score = (common_result["score"] * 0.30) + (best_group["score"] * 0.70)

    return {
        "scoring_type": "grouped_alternative",
        "final_skill_score": round(final_score, 2),

        "common_skill_score": common_result["score"],
        "common_matched_skills": common_result["matched_skills"],
        "common_missing_skills": common_result["missing_skills"],

        "best_group_name": best_group["group_name"],
        "best_group_score": best_group["score"],
        "best_group_matched_skills": best_group["matched_skills"],
        "best_group_missing_skills": best_group["missing_skills"],

        "all_group_results": group_results
    }


def match_skills(resume_data, jd_data, position_code):
    position = get_position_by_code(jd_data, position_code)

    if not position:
        return {
            "error": f"Position code {position_code} not found"
        }

    resume_skills = resume_data.get("skills", [])

    skill_requirements = position.get("skill_requirements", {
        "scoring_type": "normal",
        "required_skills": [
            item.get("skill", "")
            for item in position.get("required_skills", [])
        ]
    })

    scoring_type = skill_requirements.get("scoring_type", "normal")

    if scoring_type == "grouped_alternative":
        result = grouped_skill_matching(resume_skills, skill_requirements)

    elif scoring_type == "weighted":
        result = weighted_skill_matching(resume_skills, skill_requirements)

    else:
        result = normal_skill_matching(resume_skills, skill_requirements)

    return {
        "candidate_name": resume_data.get("name", ""),
        "position_code": position_code,
        "position_title": position.get("position_title", ""),
        "function": position.get("function", ""),
        "resume_skills": resume_skills,
        **result
    }
    
def weighted_skill_matching(resume_skills, skill_requirements):
    core_skills = skill_requirements.get("core_skills", [])
    bonus_skills = skill_requirements.get("bonus_skills", [])

    core_result = calculate_skill_score(resume_skills, core_skills)
    bonus_result = calculate_skill_score(resume_skills, bonus_skills)

    final_score = (
        core_result["score"] * 0.80 +
        bonus_result["score"] * 0.20
    )

    return {
        "scoring_type": "weighted",
        "final_skill_score": round(final_score, 2),

        "core_skill_score": core_result["score"],
        "core_matched_skills": core_result["matched_skills"],
        "core_missing_skills": core_result["missing_skills"],

        "bonus_skill_score": bonus_result["score"],
        "bonus_matched_skills": bonus_result["matched_skills"],
        "bonus_missing_skills": bonus_result["missing_skills"],

        "match_details": {
            "core_details": core_result["details"],
            "bonus_details": bonus_result["details"]
        }
    }


if __name__ == "__main__":
    resume_path = "parsed_data/resumes/Ritika_Jain_parsed_resume.json"
    jd_path = "parsed_data/jobs/parsed_job.json"

    resume_data = load_json(resume_path)
    jd_data = load_json(jd_path)

    result = match_skills(resume_data, jd_data, "FTA-2")

    print(json.dumps(result, indent=4, ensure_ascii=False))