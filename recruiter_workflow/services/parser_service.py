import os
from typing import Optional

from pypdf import PdfReader
from docx import Document


def extract_text(file_path: str) -> str:
    """Extract text from a PDF or DOCX file. Returns raw text."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return _extract_pdf(file_path)
    elif ext == ".docx":
        return _extract_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: '{ext}'. Only .pdf and .docx are supported.")


def _extract_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages)


def _extract_docx(file_path: str) -> str:
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def parse_resume_sections(raw_text: str) -> dict[str, Optional[str]]:
    """Heuristic-based parsing of raw resume text into structured sections."""
    lines = raw_text.split("\n")
    sections = {
        "candidate_name": None,
        "email": None,
        "phone": None,
        "education": None,
        "skills": None,
        "projects": None,
        "experience": None,
        "certifications": None,
    }

    current_section: Optional[str] = None
    section_content: dict[str, list[str]] = {
        "education": [],
        "skills": [],
        "projects": [],
        "experience": [],
        "certifications": [],
    }

    import re

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Extract email
        if not sections["email"]:
            clean_str = re.sub(r'(?i)envel[^\w]*pe', '', stripped)
            email_match = re.search(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", clean_str)
            if email_match:
                sections["email"] = email_match.group(0)

        # Extract phone
        if not sections["phone"]:
            phone_match = re.search(
                r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", stripped
            )
            if phone_match:
                sections["phone"] = phone_match.group(0)

        # Section headers
        lower = stripped.lower()
        header_match = re.match(
            r"^(education|skills|projects|experience|certifications|work\s*experience|technical\s*skills)[:\s]*$",
            lower,
        )
        if header_match:
            key = header_match.group(1)
            # Normalise keys
            if key == "work experience":
                key = "experience"
            elif key == "technical skills":
                key = "skills"
            current_section = key
            continue

        # Name heuristic: first non-empty, non-email, non-phone, short line
        if not sections["candidate_name"] and len(stripped) < 60 and not re.search(r"[@()\d{5,}]", stripped):
            sections["candidate_name"] = stripped

        if current_section and current_section in section_content:
            section_content[current_section].append(stripped)

    for key, lines_list in section_content.items():
        if lines_list:
            sections[key] = "\n".join(lines_list)

    return sections
