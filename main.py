import re
import os
import pdfplumber
data = pdfplumber.open('job.pdf')
print(data.pages[0].extract_text())