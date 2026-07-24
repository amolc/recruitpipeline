import json
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
from dotenv import load_dotenv


load_dotenv()
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini')
OPENROUTER_BASE = 'https://openrouter.ai/api/v1'


EXTRACTION_PROMPT = """You are an expert CV/resume parser. Extract all structured information from the CV text below and return ONLY valid JSON with this exact structure:

{
  "summary": "A concise 2-3 sentence professional summary of the candidate",
  "skills": [
    {"name": "Skill Name", "category": "Technical/Soft/Language/Tool", "level": "expert/advanced/intermediate/beginner"}
  ],
  "experience": [
    {
      "company": "Company Name",
      "title": "Job Title",
      "start_date": "MMM YYYY",
      "end_date": "MMM YYYY or Present",
      "duration_years": 0,
      "description": "Brief description of role and achievements",
      "technologies": ["tech1", "tech2"]
    }
  ],
  "education": [
    {
      "institution": "University/College Name",
      "degree": "Degree Type (B.Sc, M.Sc, PhD, etc.)",
      "field": "Field of Study",
      "graduation_year": "YYYY",
      "gpa": "GPA if mentioned, otherwise null"
    }
  ],
  "certifications": [
    {
      "name": "Certification Name",
      "issuer": "Issuing Organization",
      "year": "YYYY or null"
    }
  ],
  "languages": [
    {"language": "Language Name", "proficiency": "native/fluent/intermediate/basic"}
  ],
  "contact": {
    "email": "email if found",
    "phone": "phone if found",
    "linkedin": "URL if found",
    "location": "location if found"
  },
  "total_experience_years": 0,
  "extracted_fields": ["summary", "skills", "experience", "education", "certifications", "languages"]
}

Extract EVERY piece of information visible in the CV. If a section is not present in the CV, use an empty array or null. Be thorough and accurate."""


def gen_with_ai(system_prompt, user_prompt, temperature=0.3, max_tokens=2048):
    if not OPENROUTER_API_KEY:
        return None
    try:
        with httpx.Client(timeout=120) as client:
            resp = client.post(
                f'{OPENROUTER_BASE}/chat/completions',
                headers={
                    'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'https://github.com/amolc/recruitpipeline',
                },
                json={
                    'model': OPENROUTER_MODEL,
                    'messages': [
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': user_prompt},
                    ],
                    'temperature': temperature,
                    'max_tokens': max_tokens,
                    'response_format': {'type': 'json_object'},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data['choices'][0]['message']['content']
            return json.loads(content)
    except Exception:
        return None


def extract_with_ai(text):
    if not OPENROUTER_API_KEY:
        return None

    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                f'{OPENROUTER_BASE}/chat/completions',
                headers={
                    'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'https://github.com/amolc/recruitpipeline',
                },
                json={
                    'model': OPENROUTER_MODEL,
                    'messages': [
                        {'role': 'system', 'content': EXTRACTION_PROMPT},
                        {'role': 'user', 'content': f'Extract all information from this CV:\n\n{text}'},
                    ],
                    'temperature': 0.1,
                    'max_tokens': 4096,
                    'response_format': {'type': 'json_object'},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data['choices'][0]['message']['content']
            return json.loads(content)
    except Exception:
        return None


def extract_text_from_docx(path):
    text = []
    with zipfile.ZipFile(path) as z:
        xml = z.read('word/document.xml')
        root = ET.fromstring(xml)
        for t in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
            if t.text:
                text.append(t.text)
    return '\n'.join(text)


def extract_text_from_pdf(path):
    try:
        import fitz
        doc = fitz.open(path)
        return '\n'.join(page.get_text() for page in doc)
    except ImportError:
        pass
    try:
        from pdfminer.high_level import extract_text
        return extract_text(path)
    except ImportError:
        pass
    import subprocess
    try:
        result = subprocess.run(['pdftotext', path, '-'], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return ''


def extract_text(file_path):
    path = Path(file_path) if isinstance(file_path, str) else file_path
    suffix = path.suffix.lower()
    if suffix == '.pdf':
        return extract_text_from_pdf(path)
    elif suffix == '.docx':
        return extract_text_from_docx(path)
    elif suffix == '.txt':
        return path.read_text(encoding='utf-8', errors='replace')
    return ''


_SECTION_PATTERNS = {
    'summary': re.compile(r'\b(summary|profile|about me|objective|professional summary)\b', re.IGNORECASE),
    'experience': re.compile(r'\b(experience|work history|employment|work experience|professional experience)\b', re.IGNORECASE),
    'education': re.compile(r'\b(education|academic background|qualifications|academic qualifications)\b', re.IGNORECASE),
    'skills': re.compile(r'\b(skills|technical skills|core competencies|key skills|expertise)\b', re.IGNORECASE),
    'certifications': re.compile(r'\b(certifications|certificates|licenses|accreditations)\b', re.IGNORECASE),
}


def _split_sections(text):
    lines = text.split('\n')
    section_map = {key: [] for key in _SECTION_PATTERNS}
    section_map['header'] = []
    current = 'header'
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        for key, pattern in _SECTION_PATTERNS.items():
            if pattern.search(stripped) and len(stripped) < 100:
                current = key
                break
        section_map[current].append(stripped)
    return section_map


def _parse_skills_fallback(lines):
    all_text = ' '.join(lines)
    for sep in ['|', '•', ',', '·', '/']:
        if sep in all_text:
            return [{'name': s.strip(), 'category': 'Unknown', 'level': None} for s in re.split(r'\s*' + re.escape(sep) + r'\s*', all_text) if s.strip()]
    return [{'name': s.strip('-*• '), 'category': 'Unknown', 'level': None} for s in lines if s.strip('-*• ')]


def _parse_experience_fallback(lines):
    entries = []
    current = {}
    date_pat = re.compile(r'(\b(19|20)\d{2}\b)\s*[-–—to]+\s*(\b(19|20)\d{2}\b|present|current|now)', re.IGNORECASE)
    for line in lines:
        if date_pat.search(line):
            if current:
                entries.append(current)
            current = {'company': line, 'title': '', 'description': '', 'start_date': '', 'end_date': '', 'technologies': []}
        elif current:
            current.setdefault('description', '')
            current['description'] += ' ' + line
        else:
            current = {'company': line, 'title': '', 'description': '', 'start_date': '', 'end_date': '', 'technologies': []}
    if current:
        entries.append(current)
    return entries


def _parse_education_fallback(lines):
    entries = []
    for line in lines:
        if re.search(r'\b(university|college|institute|school|bachelor|master|phd|b\.?sc|m\.?sc|b\.?a|m\.?a|b\.?tech|m\.?tech|diploma|high school)\b', line, re.IGNORECASE):
            entries.append({'institution': line, 'degree': '', 'field': '', 'graduation_year': None})
    return entries


def _parse_certifications_fallback(lines):
    return [{'name': line.strip('-*• '), 'issuer': None, 'year': None} for line in lines if line.strip('-*• ')]


def _normalise_structure(data):
    def arr(key):
        return data.get(key) or []

    def lst(items, keys):
        return [{k: (item.get(k) if item.get(k) else None) for k in keys} for item in (items or [])]

    return {
        'summary': data.get('summary') or '',
        'skills': lst(arr('skills'), ['name', 'category', 'level']),
        'experience': lst(arr('experience'), ['company', 'title', 'start_date', 'end_date', 'description', 'technologies']),
        'education': lst(arr('education'), ['institution', 'degree', 'field', 'graduation_year', 'gpa']),
        'certifications': lst(arr('certifications'), ['name', 'issuer', 'year']),
        'languages': lst(arr('languages'), ['language', 'proficiency']),
        'contact': data.get('contact') or {},
        'total_experience_years': data.get('total_experience_years'),
        'raw_text': data.get('raw_text', ''),
    }


def process_cv(file_path):
    raw_text = extract_text(file_path)
    if not raw_text.strip():
        return {
            'raw_text': '[No text extracted]',
            'summary': '',
            'skills': [],
            'experience': [],
            'education': [],
            'certifications': [],
            'languages': [],
            'contact': {},
            'total_experience_years': None,
        }

    ai_result = extract_with_ai(raw_text)
    if ai_result:
        ai_result['raw_text'] = raw_text
        return _normalise_structure(ai_result)

    sections = _split_sections(raw_text)
    return {
        'raw_text': raw_text,
        'summary': ' '.join(sections.get('summary', [])),
        'skills': _parse_skills_fallback(sections.get('skills', [])),
        'experience': _parse_experience_fallback(sections.get('experience', [])),
        'education': _parse_education_fallback(sections.get('education', [])),
        'certifications': _parse_certifications_fallback(sections.get('certifications', [])),
        'languages': [],
        'contact': {},
        'total_experience_years': None,
    }
