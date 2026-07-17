# Superadmin App — Recruitme

## Overview

A dedicated superadmin dashboard for internal management of the entire Recruitme platform. Staff log in at `/superadmin/` to manage companies, candidates, job positions, users, and view platform-wide analytics.

---

## Routes

| Path | Page |
|---|---|
| `/superadmin/` | Redirect to `/superadmin/dashboard/` |
| `/superadmin/login/` | Superadmin login page |
| `/superadmin/logout/` | Logout → redirect to `/superadmin/login/` |
| `/superadmin/dashboard/` | Platform-wide dashboard with stats |
| `/superadmin/companies/` | List all companies |
| `/superadmin/companies/create/` | Create a company |
| `/superadmin/companies/<pk>/` | Company detail |
| `/superadmin/companies/<pk>/edit/` | Edit company |
| `/superadmin/companies/<pk>/delete/` | Delete company |
| `/superadmin/candidates/` | List all candidates (global) |
| `/superadmin/candidates/<pk>/` | Candidate detail |
| `/superadmin/candidates/<pk>/delete/` | Delete candidate |
| `/superadmin/positions/` | List all job positions (global) |
| `/superadmin/positions/<pk>/` | Position detail |
| `/superadmin/positions/<pk>/edit/` | Edit position |
| `/superadmin/positions/<pk>/delete/` | Delete position |
| `/superadmin/positions/create/` | Create position |
| `/superadmin/users/` | List all platform users |
| `/superadmin/users/create/` | Create user |
| `/superadmin/users/<pk>/edit/` | Edit user |
| `/superadmin/users/<pk>/delete/` | Delete user |
| `/superadmin/skills/` | List all skills |
| `/superadmin/skills/create/` | Create a skill |
| `/superadmin/skills/<pk>/edit/` | Edit skill |
| `/superadmin/skills/<pk>/delete/` | Delete skill |

---

## Authentication

- **Login page:** `/superadmin/login/` — email + password form
- **Access:** Only Django `is_superuser` users allowed
- **Decorator:** `superadmin_required` — checks `is_authenticated` + `is_superuser`, redirects to `/superadmin/login/` if not
- **Logout:** `/superadmin/logout/` — clears session, redirects to `/superadmin/login/`

---

## Architecture & Implementation

### App: `superadmin`

Replace the existing stub at `superadmin/` with a full Django app containing its own views, templates, and URL config.

**Key design decisions:**
- **No middleware dependency** — superadmin routes (all under `/superadmin/`) are excluded from `CompanyMiddleware` so `request.company` is always `None`
- **Separation of concerns** — superadmin lives in its own app, completely decoupled from `adminpanel/`
- **Existing `adminpanel/` views remain** — company-scoped admin (`/{slug}/admin/...`) stays untouched for per-company recruiting teams

### Needed Changes in Existing Code

1. **`conf/middleware.py`** — Add `'superadmin'` to the exclusion list so `/superadmin/` never attempts a company lookup
2. **`conf/urls.py`** — Add `path('superadmin/', include('superadmin.urls'))` before the slug-catchall routes
3. **`conf/settings.py`** — Add `'superadmin'` to `INSTALLED_APPS`

### Templates

Location: `superadmin/templates/superadmin/`

All templates use a light/professional theme consistent with the Recruitme brand (emerald green primary, white backgrounds). A single `base.html` provides the sidebar layout.

**Layout (`base.html`):**
- Fixed left sidebar (240px) with:
  - Recruitme logo (links to dashboard)
  - Navigation: Dashboard, Companies, Candidates, Positions, Skills, Users
  - Logout link at bottom
- Top header bar with user name
- Main content area
- Messages block for success/error notifications

### Page Details

#### Login (`login.html`)
- Clean centered card layout
- Username + Password fields
- Error message display for invalid credentials
- Redirects to `/superadmin/dashboard/` on success

#### Dashboard (`dashboard.html`)
- Stats cards row: Total Companies, Total Candidates, Total Positions, Total Users
- Second stats row: Active Jobs Today, New Applicants (30d), Skills in Database
- Recent activity: Latest 10 applicants with company/job/date
- Quick action buttons: Create Company, Add User, View All Candidates

#### Companies — List (`companies.html`)
- Table: Name (linked), Brand Color dot, Active/Inactive badge, Positions count, Candidates count, Users count, Created date, Actions (View, Edit, Delete)
- Search/filter bar

#### Companies — Create/Edit (`company_form.html`)
- Fields: Company Name, Slug (auto-generated from name, editable), Brand Color (color picker), Logo URL, Upload Logo, Is Active checkbox
- On create: auto-generates default pipeline stages and automation rules

#### Companies — Detail (`company_detail.html`)
- Company info header with brand color bar
- Stats: Candidates, Positions, Stages, Users
- Tables: Job Positions (with status toggle), Team Members (username, role)
- Edit button, Back to list

#### Candidates — List (`candidates.html`)
- Search by name/email/position
- Filter by Company dropdown
- Table: Name, Email, Company badge, Position, Status pill, Submitted date, Resume link

#### Positions — List (`positions.html`)
- Filter by Company dropdown
- Table: Title, Company badge, Location, Required Skills (tag pills), Status, Created date
- Actions: View, Edit, Delete

#### Users — List (`users.html`)
- Table: Username, Email, Company badge, Role pill, Superadmin badge, Active indicator, Last login
- Create User button

#### Users — Create/Edit (`user_form.html`)
- Fields: Username, Email, Password (create only), Company dropdown, Role dropdown (Admin / Recruiter / Hiring Manager), Super Admin toggle, Is Active toggle

#### Skills — List (`skills.html`)
- Table: Name, Category pill, Candidates count, Positions count
- Search bar, Create Skill button

#### Skills — Create/Edit (`skill_form.html`)
- Fields: Name, Category dropdown (Technical, Soft, Language, Tool, Domain)

---

## Models Referenced

All models already exist in `api/models.py`:

| Model | Key Fields | CRUD |
|---|---|---|
| `Company` | name, slug, brand_color, logo, is_active, created_at | Full |
| `Application` (candidate) | full_name, email, phone, position, company, status, resume, submitted_at | Read + Delete |
| `JobPosition` | title, company, description, location, skills, is_active, created_at | Full |
| `User` + `UserProfile` | username, email, is_superuser, profile.company, profile.role | Full |
| `Skill` | name, category | Full |

---

## Implementation Order

1. **Middleware** — Add `'superadmin'` to exclusion list in `CompanyMiddleware`
2. **Settings** — Add `'superadmin'` to `INSTALLED_APPS`
3. **URLs** — Wire `superadmin/urls.py` into `conf/urls.py` before slug catchalls
4. **Superadmin views** — Rebuild `superadmin/views.py` with all CRUD views + `superadmin_required` decorator
5. **Templates** — Create all template files with the light theme sidebar layout
6. **URL config** — `superadmin/urls.py` mapping all routes to views
7. **Existing `/adminpanel/` superadmin routes** — Left in place as-is, no breaking changes
