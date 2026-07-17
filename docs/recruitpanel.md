# RecruitPanel — Recruiter Portal

## Overview

RecruitPanel is the per-company recruiter portal. Each company gets its own panel at `/{company_slug}/panel/` where their recruiting team manages candidates, job positions, pipeline stages, and hiring workflows.

On full migration, `adminpanel` will be removed and replaced entirely by `recruitpanel`.

---

## Authentication

RecruitPanel uses the unified auth system (phone + 4-digit PIN + secretname).

### User Model

See `docs/user.md` for the full user model. Relevant fields for recruitpanel:

| Field | Purpose |
|---|---|
| `phone` | Login identifier |
| `pin` | 4-digit password (hashed) |
| `secretname` | Recovery secret for forgot PIN |

### UserRole for Recruiters

Recruiters have a `UserRole` linking them to a specific company:

| Field | Value |
|---|---|
| `user` | FK → `User` |
| `role` | `recruiter` |
| `company` | FK → `Company` (the company they work for) |
| `sub_role` | `admin` / `recruiter` / `hiring_manager` / `viewer` |
| `is_active` | default=True |

### Role Permissions

| Feature | admin | recruiter | hiring_manager | viewer |
|---|---|---|---|---|
| View candidates | ✅ | ✅ | ✅ | ✅ |
| Move pipeline stages | ✅ | ✅ | ✅ | ❌ |
| Create/edit candidates | ✅ | ✅ | ❌ | ❌ |
| Manage job positions | ✅ | ✅ (own) | ❌ | ❌ |
| Manage pipeline stages | ✅ | ❌ | ❌ | ❌ |
| Manage team members | ✅ | ❌ | ❌ | ❌ |
| View analytics | ✅ | ✅ | ✅ | ✅ |
| Automation settings | ✅ | ❌ | ❌ | ❌ |

---

## Routes

All routes are scoped under `/{company_slug}/panel/`.

### Auth

| Path | Page |
|---|---|
| `/{slug}/panel/login/` | Recruiter login (phone + PIN) |
| `/{slug}/panel/logout/` | Logout → redirect to login |

### Dashboard

| Path | Page |
|---|---|
| `/{slug}/panel/` | Dashboard — overview stats, recent activity |
| `/{slug}/panel/dashboard/` | Same as above |

### Candidates

| Path | Page |
|---|---|
| `/{slug}/panel/candidates/` | List all candidates with search/filter |
| `/{slug}/panel/candidates/<pk>/` | Candidate detail |
| `/{slug}/panel/candidates/create/` | Add candidate manually |
| `/{slug}/panel/candidates/<pk>/edit/` | Edit candidate |
| `/{slug}/panel/candidates/<pk>/delete/` | Delete candidate |

### Pipeline / Board

| Path | Page |
|---|---|
| `/{slug}/panel/board/` | Kanban board — drag candidates across stages |
| `/{slug}/panel/pipeline/` | Pipeline stage configuration |
| `/{slug}/panel/pipeline/add/` | Add custom stage |
| `/{slug}/panel/pipeline/<key>/delete/` | Delete stage |
| `/{slug}/panel/pipeline/<key>/automation/` | Update automation for stage |

### Job Positions

| Path | Page |
|---|---|
| `/{slug}/panel/positions/` | List job positions |
| `/{slug}/panel/positions/create/` | Create position |
| `/{slug}/panel/positions/<pk>/` | Position detail |
| `/{slug}/panel/positions/<pk>/edit/` | Edit position |
| `/{slug}/panel/positions/<pk>/delete/` | Delete position |

### Screenings & Panelists

| Path | Page |
|---|---|
| `/{slug}/panel/screenings/` | Screening queue |
| `/{slug}/panel/panelist/` | Panelist management |

### Settings

| Path | Page |
|---|---|
| `/{slug}/panel/settings/` | Company settings (brand color, logo) |
| `/{slug}/panel/settings/team/` | Team member management (admin only) |

---

## Templates

Location: `recruitpanel/templates/recruitpanel/`

All templates use a light theme matching the Recruitme brand (emerald green primary). A single `base.html` provides the sidebar layout.

### Layout (`base.html`)
- Fixed left sidebar with:
  - Company name/logo at top
  - Nav: Dashboard, Board, Candidates, Positions, Pipeline, Screenings, Settings
  - User info + Logout at bottom
- Top header bar with breadcrumbs + notification area
- Main content area
- Messages block

### Page Details

#### Login (`login.html`)
- Centered card on company-branded background
- Phone number input + 4-digit PIN input
- "Forgot PIN?" link → opens secretname recovery popup
- On success: redirect to dashboard

#### Dashboard (`dashboard.html`)
- Stats row: Total Candidates, Active Positions, In Pipeline, Hired This Month
- Pipeline overview (compact stage view with counts)
- Recent activity feed (latest applications, stage changes)
- Quick actions: Add Candidate, Create Position

#### Board (`board.html`)
- Full Kanban board with columns for each pipeline stage
- Drag-and-drop candidate cards between stages
- Each card shows: name, position, experience, days in stage
- Click card → candidate detail modal/inline view
- Stage headers show count + automation indicator

#### Candidates List (`candidates.html`)
- Search bar (name, email, phone, position)
- Filters: Stage, Position, Date Range
- Table: Name, Contact, Position, Stage, Experience, Resume, Actions
- Bulk actions: Move stage, Delete
- Export button

#### Candidate Detail / Form (`candidate_form.html`, `candidate_detail.html`)
- Detail: Full profile view with all fields + resume download + stage history
- Form: Name, Email, Phone, Position, Experience, Resume upload, Cover letter, Stage selection, Notes

#### Positions List (`positions.html`)
- Table: Title, Location, Candidate count, Status toggle (Active/Inactive), Created date, Actions
- Filter by status

#### Position Form (`position_form.html`)
- Title, Description (rich text), Location, Base Salary, Hourly Rate, Requirements, Skills (tag input), Is Active

#### Pipeline Config (`pipeline.html`)
- List of stages with order, key, label
- Drag to reorder
- Add stage button
- Delete stage (with confirmation if candidates exist)
- Automation editor per stage (textarea for automation description)

#### Settings (`settings.html`)
- Company name, Brand color picker, Logo upload, Slug (read-only)
- Team members table with role badges + remove button
- Invite team member form

---

## Models Referenced

All models live in `api/models.py`:

| Model | Key Fields | Notes |
|---|---|---|
| `Company` | name, slug, brand_color, logo, is_active | Auto-generated on superadmin creation |
| `Application` | company, full_name, email, phone, position, experience, resume, status, submitted_at | The candidate record |
| `JobPosition` | company, title, description, location, skills, base_salary, hourly_rate, requirements, is_active | Per-company positions |
| `Stage` | company, key, label, order | Configurable per company |
| `Automation` | company, position, stage, description | Per-position automation rules |

---

## Data Flow

### Login Process
```
1. User enters phone + PIN at /{slug}/panel/login/
2. PhoneAuthBackend authenticates
3. UserRole lookup: role=recruiter, company matches slug
4. If valid: session['role'] = 'recruiter', session['company_id'] = company.id
5. Redirect to /{slug}/panel/dashboard/
```

### Scoping
- Every view filters by `session['company_id']`
- A recruiter at Company A cannot see Company B's data
- The middleware extracts company slug from URL, validates against session

### Registration Flow for Recruiters
- New recruiters are invited by a company admin (not self-registered)
- Admin creates user with phone → system sends credentials (phone + temporary PIN)
- First login prompts: "Set your 4-digit PIN" + "Set your secretname"

---

## Implementation Order

1. **Create `recruitpanel` app** — views, templates, urls
2. **Auth views** — login, logout with phone + PIN + `recruiter_required` decorator
3. **Dashboard** — overview stats + recent activity
4. **Candidates** — list, detail, create, edit, delete
5. **Board** — Kanban drag-and-drop pipeline
6. **Positions** — CRUD for job positions
7. **Pipeline config** — stage management + automation
8. **Screenings & Panelists** — port from adminpanel
9. **Settings** — company settings + team management
10. **Middleware** — `RecruitPanelMiddleware` to scope by company slug from URL
11. **Migrate data** — port existing data from adminpanel to recruitpanel
12. **Remove `adminpanel`** — once full parity is confirmed
