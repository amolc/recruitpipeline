# RecruitPipeline — Multi-Tenant Recruitment ATS

A Django-based Applicant Tracking System (ATS) built for recruitment agencies and companies to manage their hiring pipeline. Supports **multiple companies** with isolated data, custom pipelines, and branded career pages.

---

## Features

- **Multi-Tenant Architecture** — Each company gets isolated data, custom pipeline stages, and a branded career page
- **Kanban Board** — Drag-and-drop pipeline management with left/right arrow controls
- **Pipeline Stages** — Fully customizable stages per company (add, reorder, delete)
- **Automation Descriptions** — Per-stage automation rules editable per position or globally
- **Candidate Management** — Full CRUD with search, filter by stage/position
- **Job Position Management** — Create, edit, activate/deactivate positions per company
- **Career Pages** — Each company gets a branded public application page at `/{slug}/apply/`
- **CV Parsing** — AI-powered resume extraction via OpenRouter API with fallback regex parsing
- **Admin Dashboard** — Recruiter-focused dark-theme interface

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 6.0, Python 3.13 |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Frontend | Server-rendered Django templates + vanilla JS |
| Styling | Custom CSS (dark theme) with Inter font, dynamic brand colors per company |
| CV Parsing | OpenRouter AI (GPT-4o-mini), PyMuPDF, pdfminer.six |
| Static Server | Express 5 (dev, port 3000) |
| CI/CD | GitHub Actions → PM2 on Ubuntu |

---

## Project Structure

```
recruitpipeline/
├── conf/                        # Django project config
│   ├── settings.py              # Settings (DB, middleware, apps, CORS)
│   ├── urls.py                  # Root URL routing (tenant-aware)
│   ├── middleware.py             # CompanyMiddleware (slug extraction)
│   ├── wsgi.py / asgi.py        # WSGI/ASGI entry points
├── api/                         # Data models + REST API
│   ├── models.py                # Company, Stage, Application, JobPosition, Automation, UserProfile
│   ├── views.py                 # submit_application, update_status, list_positions
│   └── admin.py                 # Django admin config for all models
├── frontend/                    # Public-facing pages
│   ├── views.py                 # landing (company selector), apply (career page)
│   └── templates/frontend/
│       ├── landing.html         # Landing page — company list + login/apply links
│       └── apply.html           # Per-company branded career page with application form
├── adminpanel/                  # Recruiter dashboard (13 templates)
│   ├── views.py                 # All dashboard views (auth, CRUD, board, pipeline)
│   ├── urls.py                  # URL patterns for company-scoped admin
│   ├── templates/adminpanel/
│   │   ├── base.html            # Dynamic sidebar + header with company branding
│   │   ├── login.html           # Company-specific login page
│   │   ├── board.html           # Kanban board with drag-and-drop + automation strip
│   │   ├── candidate_list.html  # Searchable/filterable candidate table
│   │   ├── candidate_detail.html
│   │   ├── candidate_form.html  # Add/Edit candidate form
│   │   ├── candidate_confirm_delete.html
│   │   ├── job_positions.html   # Position list + add form
│   │   ├── job_position_detail.html  # Position info + automation editor + Kanban
│   │   ├── job_position_form.html
│   │   ├── pipeline.html        # Stage grid with automation editor + add/delete
│   │   ├── panelist.html        # Placeholder
│   │   └── screenings.html      # Placeholder
│   ├── templatetags/            # Custom template filters
│   └── management/commands/     # Seed commands
├── agents/                      # CV parsing & AI extraction app
│   ├── extractor.py             # Resume text extraction (PDF/DOCX/TXT) + AI parsing via OpenRouter
│   ├── views.py                 # CV extraction API endpoint
│   └── models.py                # CVExtract model
├── uploads/resumes/             # Uploaded resume files
├── manage.py                    # Django CLI entry point
├── recruit.js                   # Express dev server (port 3000)
├── requirements.txt             # Python dependencies
└── package.json                 # Node.js dependencies
```

---

## Multi-Tenant Architecture

Uses **path-based tenancy** — each company is identified by a URL slug:

```
http://localhost:8000/                → Landing page (company selector)
http://localhost:8000/solarsolutions/ → SolarSolutions home (redirects to board or login)
http://localhost:8000/solarsolutions/board/
http://localhost:8000/solarsolutions/apply/
http://localhost:8000/greenenergy/    → GreenEnergy home
```

### How it works

1. **CompanyMiddleware** extracts the first path segment (e.g., `solarsolutions`) and looks up the `Company` object
2. Sets `request.company` for all downstream views
3. All models have a `company` ForeignKey ensuring complete data isolation
4. Every queryset is filtered by `request.company`
5. Templates use `{{ company.name }}` and `{{ company.brand_color }}` for dynamic branding

### Data Model

```
Company
  ├── Stage (pipeline stages per company)
  ├── JobPosition (positions per company)
  ├── Application (candidates per company)
  ├── Automation (automation descriptions per position+stage)
  └── UserProfile (users → company membership)
```

---

## Quick Start

### Setup

```bash
# Clone repository
git clone <repo-url> && cd recruitpipeline

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
source venv/bin/activate       # Linux/macOS

# Install Python dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create a company
python manage.py shell -c "
from api.models import Company
Company.objects.create(name='MyCompany', slug='mycompany', brand_color='#f59e0b')
"

# Create superuser
python manage.py create_default_admin

# Seed pipeline stages, positions, and automations
python manage.py seed_stages --company=mycompany
python manage.py seed_positions --company=mycompany
python manage.py seed_automations --company=mycompany

# Start Django dev server
python manage.py runserver
```

---

## Navigation Guide

### 1. Landing Page → `http://localhost:8000/`

Shows a list of all registered companies. Each company has:
- **Apply** — Opens the public career page for that company
- **Login** — Opens the recruiter login page for that company

### 2. Public Career Page → `http://localhost:8000/{slug}/apply/`

A branded application form for each company. Candidates can:
- View the company's open positions (dynamically loaded from database)
- Fill in their details (name, email, phone, experience)
- Upload a resume (PDF/DOC/DOCX)
- Submit their application
- See a success confirmation

### 3. Recruiter Login → `http://localhost:8000/{slug}/login/`

- Default credentials: `admin` / `admin123` (superuser — access any company)
- The login page shows the company name for branding
- After login, redirects to the candidates list

### 4. Candidates List → `http://localhost:8000/{slug}/candidates/`

- Search by name, email, position, or phone
- Filter by pipeline stage
- View, Edit, Delete candidates
- Add new candidates manually

### 5. Kanban Board → `http://localhost:8000/{slug}/board/`

- **Pipeline automation strip** at top — shows what actions happen at each stage
  - Click the pencil icon to edit automation descriptions inline
- **Drag-and-drop columns** — move candidate cards between stages
- **Left/Right arrows** — advance or regress candidates through stages
- Each column shows the stage name and candidate count

### 6. Job Positions → `http://localhost:8000/{slug}/job-positions/`

- List all positions with active/inactive status
- Add new positions (type name and click "Add")
- Delete positions
- Click a position to view details

### 7. Position Detail → `http://localhost:8000/{slug}/job-positions/{id}/`

- **Info panel** — title, salary, location, description, requirements
- **Automation editor** — per-stage automation descriptions specific to this position
- **Application Kanban** — filtered to show only candidates for this position
- **Edit button** — modify position details

### 8. Pipeline Management → `http://localhost:8000/{slug}/pipeline/`

- Grid view of all pipeline stages with their automation descriptions
- **Edit automations** inline (applies globally to all positions)
- **Add Stage** — create new pipeline stages with name and position
- **Delete Stage** — remove a stage (candidates in deleted stage move to "New")

### 9. Panelist / Screenings → `http://localhost:8000/{slug}/panelist/`

Placeholder pages for future features.

### 10. Django Admin → `http://localhost:8000/admin/`

Super admin interface for managing companies, users, and all data directly.

---

## API Endpoints

All API endpoints are scoped to a company and accessed via `/{slug}/api/`.

| Method | Endpoint | Description |
|---|---|---|
| POST | `/{slug}/api/apply/` | Submit a job application (FormData with file upload) |
| POST | `/{slug}/api/apply/{id}/status/` | Update a candidate's pipeline stage |
| GET | `/{slug}/api/positions/` | List active job positions for the company |
| POST | `/{slug}/api/extract/` | Extract CV data via AI (requires OpenRouter API key) |

---

## CV Parsing

The CV extractor supports PDF, DOCX, and TXT files. It uses OpenRouter AI (GPT-4o-mini) for structured extraction with a regex-based fallback pipeline.

1. **AI extraction** (primary) — sends text to OpenRouter API, returns structured JSON
2. **Regex fallback** — splits text by sections (skills, experience, education, certifications)
3. **Text extraction** — uses PyMuPDF (fast) or pdfminer.six (fallback) for PDFs

### Usage

```bash
# Via management command
python manage.py cvreader <application_id>

# Via API
curl -X POST http://localhost:8000/{slug}/api/extract/ \
  -F "application_id=1"
```

Requires `OPENROUTER_API_KEY` in `.env` file.

---

## Seed Data

Default pipeline stages (13):

| Stage | Automation |
|---|---|
| New | Send acknowledgement email, Parse resume, Auto-tag by position |
| Need Info | Detect incomplete fields, Send follow-up, Flag for review |
| Screening | Auto-screen with keywords, Run assessment, Schedule phone screen |
| Qualified | Send confirmation, Add to talent pool, Notify manager |
| Contacted | Track email opens, Auto-follow-up after 3 days |
| Assessment | Generate link, Set deadline, Auto-grade |
| Interview | Auto-schedule, Send invite + prep materials, 24h reminder |
| Selected | Notify HR, Initiate offer packet, Trigger background check |
| Background Check | Send authorization, Track via API, Flag results |
| Offer Sent | Generate letter, Send via DocuSign, Track signature |
| Accepted | Trigger onboarding, Send welcome packet, Create employee record |
| Onboarded | Schedule orientation, Assign equipment, Send 30-day survey |
| Rejected | Send rejection email, Add to talent pool, Request feedback |

---

## Adding a New Company

```bash
# Create company
python manage.py shell -c "
from api.models import Company
Company.objects.create(name='Acme Corp', slug='acme', brand_color='#3b82f6')
"

# Seed data
python manage.py seed_stages --company=acme
python manage.py seed_positions --company=acme
python manage.py seed_automations --company=acme

# Create a user for this company
python manage.py shell -c "
from django.contrib.auth import get_user_model
from api.models import Company, UserProfile
User = get_user_model()
user, _ = User.objects.get_or_create(username='recruiter')
user.set_password('recruiter123')
user.save()
company = Company.objects.get(slug='acme')
UserProfile.objects.create(user=user, company=company, role='recruiter')
"
```

---

## Deployment

The app includes a GitHub Actions workflow (`.github/workflows/deploy.yaml`) that deploys to an Ubuntu server on push to `main`. It uses PM2 to manage the Django process.

The Express static server (`recruit.js`) runs on port 3000 for dev.

---

## License

MIT
