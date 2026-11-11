
import fitz
from docx import Document


def extract_text(file_path):

    text = ""

    if file_path.lower().endswith(".pdf"):

        pdf = fitz.open(file_path)

        for page in pdf:
            text += page.get_text() + "\n"

        pdf.close()

    elif file_path.lower().endswith(".docx"):

        document = Document(file_path)

        for paragraph in document.paragraphs:
            text += paragraph.text + "\n"

    return text.strip()
