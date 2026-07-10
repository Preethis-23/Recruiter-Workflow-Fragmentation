import sqlite3
from pypdf import PdfReader
from docx import Document
from sentence_transformers import SentenceTransformer

# Initialize Sentence Transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_docx(file_path):
    doc = Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def create_database():
    conn = sqlite3.connect('recruiter_workflow.db')
    cursor = conn.cursor()
    
    with open('schema.sql', 'r') as file:
        sql_script = file.read()
    
    cursor.executescript(sql_script)
    conn.commit()
    conn.close()

def calculate_similarity(text1, text2):
    embeddings1 = model.encode([text1])
    embeddings2 = model.encode([text2])
    similarity = cosine_similarity(embeddings1, embeddings2)[0][0]
    return similarity

if __name__ == '__main__':
    create_database()
