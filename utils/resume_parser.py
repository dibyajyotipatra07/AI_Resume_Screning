import re
import spacy

# load NLP Module
nlp = spacy.load("en_core_web_sm")

# For Mail ID of Candidates
def extract_email(text):
    global mail_pattern
    mail_pattern = r"([\w.%-]+@[A-Za-z]+\.[A-Za-z]{2,3})"
    return re.findall(mail_pattern,text)[0]

# For Phone Mumber Match
def extract_phn(text):
    global phn_pattern
    phn_pattern = r"((?:\+91[-\s]?)?[6-9]\d{4}[-\s]?\d{5})"
    return re.findall(phn_pattern,text)[0]

# For Linkedin Match
def extract_linkedin(text):
    linkedin_pattern = r"(linkedin.com\/in\/[\w-]+)"
    matches =  re.findall(linkedin_pattern,text)[0] or ""
    if matches:
        return matches[0]
    else:
        return ""

# For Github Match
def extract_git(text):
    git_pattern = r"(github.com\/[\w-]+)"
    matches = re.findall(git_pattern,text)
    if matches:
        return matches[0]
    else:
        return ""

# For Name of the Applicant
def extract_name(text):
    
    # Consider only the first few line
    first_line = text.split('\n')[0]
    
    # Removing Mail id and phn no for better NER
    top_text = re.sub(mail_pattern,"", first_line).strip()
    top_text = re.sub(phn_pattern,"", first_line).strip()
    
    # Defining Doc  
    doc = nlp(top_text)
    sent1 = list(doc.sents)[0]
    name = ""
    
    # Using NER for nam extraction
    for ent in sent1.ents:
        if ent.label_ == "PERSON":
            name += ent.text

    # If NER fails Backup
    if len(name.split()) > 1:
        return name
    else:
        return top_text