import spacy
from spacy.matcher import PhraseMatcher
import pdfplumber

file = pdfplumber.open("job.pdf")
text = ""

for page in file.pages:
    text += page.extract_text()

nlp = spacy.load("en_core_web_sm")

def extract_job_title(text):
    phrase_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

    job_titles = [
        "Project Engineer",
        "Project Supervisor",
        "Python Developer",
        "Data Analyst",
        "Machine Learning Engineer",
        "Software Engineer"
    ]

    patterns = [nlp(title) for title in job_titles]

    phrase_matcher.add("JOB_TITLE", patterns)

    doc = nlp(text)

    matches = phrase_matcher(doc)

    titles = []

    for _, start, end in matches:
        titles.append(doc[start:end].text)

    return list(set(titles))

print(extract_job_title(text))