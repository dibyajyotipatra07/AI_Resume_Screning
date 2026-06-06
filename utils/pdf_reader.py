import pdfplumber

# PDF reader
def pdf_reader(pdf_path):
    text =""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text