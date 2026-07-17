# Candidate System — Recruitme

## Overview

A global candidate platform where candidates sign up, upload their master resume, get AI‑extracted profile data, search jobs by skills across all companies, and apply with auto‑generated tailored resumes and cover letters.

---

## Data Model

### New Models (`api/models.py`)

**Skill**

| Field | Type | Notes |
|---|---|---|
| `name` | `CharField(200)` | unique |
| `category` | `CharField(50)` | blank — Technical, Soft, Language, Tool, Domain… |

**Candidate**

| Field | Type | Notes |
|---|---|---|
| `user` | `OneToOneField(User)` | null‑able, linked on registration |
| `full_name` | `CharField(200)` | |
| `email` | `EmailField` | unique |
| `phone` | `CharField(30)` | blank |
| `resume` | `FileField` | upload_to=`candidate_resumes/` — master resume |
| `raw_text` | `TextField` | full extracted text |
| `summary` | `TextField` | AI‑generated professional summary |
| `skills` | `ManyToManyField(Skill)` | via `CandidateSkill` |
| `experience` | `JSONField` | `[{title, company, start_date, end_date, description}]` |
| `education` | `JSONField` | `[{degree, institution, year}]` |
| `certifications` | `JSONField` | `[{name, issuer, year}]` |
| `languages` | `JSONField` | `[{language, proficiency}]` |
| `contact` | `JSONField` | `{linkedin, github, website, location}` |
| `total_experience_years` | `FloatField` | null‑able |
| `created_at` | `DateTimeField` | auto |
| `updated_at` | `DateTimeField` | auto |

**CandidateSkill** (through table)

| Field | Type |
|---|---|
| `candidate` | FK → `Candidate` |
| `skill` | FK → `Skill` |
| `level` | `CharField(20)` — beginner / intermediate / advanced / expert |

### Modified Models

**JobPosition** — add:

| Field | Type |
|---|---|
| `skills` | `ManyToManyField(Skill)` | blank |

**Application** — add:

| Field | Type | Notes |
|---|---|---|
| `candidate` | `ForeignKey(Candidate)` | null‑able, SET_NULL |
| `tailored_resume` | `TextField` | AI‑generated per‑job resume text |
| `generated_cover_letter` | `TextField` | AI‑generated cover letter |

---

## Authentication

| Path | Page |
|---|---|
| `/candidate/login/` | Login (email + password) |
| `/candidate/register/` | Register |

- Uses Django's `User` model (same model as company users)
- `candidate_required` decorator to protect candidate routes
- Separate namespace from company admin

---

## API Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/api/candidates/extract/` | No | Upload resume → get extracted data (pre‑auth preview) |
| `GET` | `/api/candidates/me/` | Yes | Get own profile |
| `PUT` | `/api/candidates/me/` | Yes | Update profile fields |
| `POST` | `/api/candidates/me/resume/` | Yes | Upload new master resume → re‑extract |
| `GET` | `/api/candidates/me/applications/` | Yes | List own applications with status |
| `GET` | `/api/jobs/search/?skills=...` | No | Search jobs by skills across all companies |
| `GET` | `/api/skills/` | No | List all known skills (autocomplete) |
| `POST` | `/api/applications/<id>/tailor/` | Yes | Generate tailored resume + cover letter |

---

## Frontend Pages

| Path | Page | Description |
|---|---|---|
| `/candidate/login/` | Login | Email + password |
| `/candidate/register/` | Register | Name, email, password |
| `/candidate/dashboard/` | Dashboard | Stats, recent activity, upload/update resume CTA |
| `/candidate/profile/` | Profile | Editable sections: summary, skills, experience, education, certifications, languages |
| `/candidate/jobs/` | Job Search | Search bar + skill filter chips → results with match score |
| `/candidate/applications/` | Applications | History — company, job, status, tailored resume link |

---

## Resume Tailoring + Cover Letter Flow

1. Candidate uploads **master resume** → AI extracts skills/experience → populates `Candidate` profile
2. Candidate searches jobs by skills, finds a role
3. Clicks **"Apply"** → system calls `/api/applications/<id>/tailor/`:
   - **Tailored resume:** AI reorders/rewords experience to match the job description
   - **Cover letter:** AI writes a personalized letter from candidate profile + job details
4. Candidate reviews both in an inline editor, makes tweaks
5. On submit → `Application` is created with `tailored_resume`, `generated_cover_letter`, linked to `Candidate`

---

## Implementation Order

1. **Models + migrations** — `Skill`, `Candidate`, `CandidateSkill`, modify `JobPosition` + `Application`
2. **Seed migration** — pre-populate common skills (tech stacks, tools, roles, etc.)
3. **Auth** — register/login/logout views + `candidate_required` decorator
4. **CV extraction endpoint** — reuse `agents/extractor.py`, save into `Candidate` model
5. **Profile CRUD** — API + frontend dashboard/profile pages
6. **Job search** — skill‑based search across all companies (skill overlap scoring)
7. **Tailor + cover letter generation** — AI integration for per‑job customization
8. **Full apply flow** — browse → tailor → review → submit → track in applications page
