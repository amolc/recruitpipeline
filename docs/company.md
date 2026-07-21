# Company — Recruitme

## Overview

Companies are the root entity in the Recruitme multi-tenant architecture. Every other model (Stages, Applications, Job Positions, Automations, UserProfiles) has a `company` ForeignKey, making data isolation automatic. A superadmin manages all companies from the platform-wide admin, while recruiters operate within their own company's scoped panel.

---

## Model

**File:** `company/models.py`

### `Company`

| Field | Type | Details |
|---|---|---|
| `name` | `CharField(200)` | Company name, required |
| `slug` | `SlugField(100, unique)` | URL-safe identifier, used in paths: `/{slug}/...` |
| `brand_color` | `CharField(7)` | Hex color for branding (default `#f59e0b`) |
| `logo_url` | `URLField` | External logo URL, optional |
| `logo` | `ImageField` | Uploaded logo to `company_logos/`, optional |
| `website` | `URLField` | Company website (e.g. `https://acme.com`) |
| `email` | `EmailField` | Company email (domain-matched with website) |
| `address` | `TextField` | Street, city, state, zip |
| `summary` | `TextField` | Brief company description |
| `is_active` | `BooleanField` | Default `True`; toggled by superadmin |
| `created_at` | `DateTimeField` | Auto-set on creation |

### `CompanyEditRequest`

Used when a recruiter needs to edit company details. Changes go through a pending/approved/rejected workflow reviewed by superadmin.

| Field | Type | Details |
|---|---|---|
| `company` | `ForeignKey(Company)` | The company being edited |
| `requested_by` | `ForeignKey(User)` | Recruiter who submitted the request |
| `name` | `CharField(200)` | Proposed company name change |
| `website` | `URLField` | Proposed website change |
| `email` | `EmailField` | Proposed email change |
| `address` | `TextField` | Proposed address change |
| `summary` | `TextField` | Proposed summary change |
| `brand_color` | `CharField(7)` | Proposed brand color change |
| `logo` | `ImageField` | Proposed logo change |
| `status` | `CharField(20)` | `pending` / `approved` / `rejected` |
| `reviewed_by` | `ForeignKey(User)` | Superadmin who reviewed |
| `reviewed_at` | `DateTimeField` | When review was completed |
| `created_at` | `DateTimeField` | When request was submitted |

---

## Routes

### Superadmin — Company Management (`/superadmin/`)

All routes protected by `superadmin_required` (checks `UserRole(role='superadmin')`).

| Path | Page |
|---|---|
| `/superadmin/companies/` | List all companies |
| `/superadmin/companies/create/` | Create a company |
| `/superadmin/companies/<pk>/` | Company detail — open a company from the table |
| `/superadmin/companies/<pk>/edit/` | Edit company |

### Superadmin (Legacy) — `/adminpanel/`

Existing routes protected by `super_login_required` (checks `is_superuser`).

| Path | Page |
|---|---|
| `/adminpanel/companies/` | List all companies |
| `/adminpanel/companies/create/` | Create a company |
| `/adminpanel/companies/<pk>/` | Company detail |
| `/adminpanel/companies/<pk>/edit/` | Edit company |
| `/adminpanel/edit-requests/` | Review pending company edit requests |
| `/adminpanel/edit-requests/<pk>/` | Edit request detail with field-by-field diff |
| `/adminpanel/edit-requests/<pk>/approve/` | Approve edit request |
| `/adminpanel/edit-requests/<pk>/reject/` | Reject edit request |

### RecruitPanel — Recruiter Company Management (`/{slug}/panel/`)

| Path | Page |
|---|---|
| `/{slug}/panel/company/` | View own company details |
| `/{slug}/panel/company/edit/` | Edit company (creates `CompanyEditRequest`) |
| `/{slug}/panel/company/register/` | Register new company |
| `/{slug}/panel/company/switch/` | Switch between companies (multi-company users) |

---

## Templates

### Superadmin Templates

Location: `superadmin/templates/superadmin/`

#### `companies.html` — Company List
- Extends `base.html`
- Table columns: Name (bold), Brand (color dot + hex), Positions count, Candidates count, Users count, Status (Active/Inactive badge), Created date, Actions (View, Edit)
- **View** link opens company detail at `/superadmin/companies/<pk>/`
- **Edit** link opens company edit form at `/superadmin/companies/<pk>/edit/`
- "New Company" button in toolbar
- Company count displayed above table

#### `company_detail.html` — Company Detail (Open from Table)
- Extends `base.html`
- Brand color bar at top
- Edit Company button + active/inactive status indicator
- Stats cards: Candidates, Positions, Stages, Users
- Tables: Job Positions (title, location, openings, status), Recent Candidates (last 20), Team Members (username, role, superuser flag)
- Back to Companies link

#### `company_form.html` — Create/Edit Company
- Extends `base.html`
- Fields: Company Name (required), Brand Color (color picker), Address (textarea), Summary (textarea), Upload Logo (file input), Logo URL (external link), Is Active checkbox (edit mode only)
- Save + Cancel buttons

### Recruiter Templates

Location: `recruitpanel/templates/recruitpanel/`

#### `company_detail.html` — View Company
- Company name, website, email, address, summary, created date

#### `company_form.html` — Edit Company
- Editable fields submitted as `CompanyEditRequest` (not direct edit)

---

## Superadmin — Opening a Company from the Table

The company table at `/superadmin/companies/` displays all companies with counts and status. Each row has a **View** link that opens the company detail page.

### Flow

```
1. Superadmin logs in at /superadmin/login/ (phone + PIN)
2. Dashboard shows stats including total companies
3. Click "Companies" in sidebar → /superadmin/companies/
4. Company table lists all companies with columns above
5. Click "View" on any row → /superadmin/companies/<pk>/
6. Company detail page shows full company info + stats + data tables
7. From detail page, "Edit Company" button → /superadmin/companies/<pk>/edit/
```

### Implementation

- **View function:** `superadmin.views.company_list` — annotates companies with `candidate_count`, `position_count`, `user_count` from related models
- **View function:** `superadmin.views.company_detail` — fetches company, last 20 candidates, positions, members, and computes stats
- **URL routes:** `superadmin/urls.py` — `companies/`, `companies/<pk>/`, `companies/<pk>/edit/`
- **Auth:** `superadmin_required` decorator checks `UserRole(role='superadmin', is_active=True)`
- **Templates:** Use the same emerald-green light theme from `superadmin/base.html`

---

## Company Middleware

**File:** `conf/middleware.py`

`CompanyMiddleware` extracts the first URL path segment and looks up the `Company` by slug. It sets `request.company` for all company-scoped views.

**Excluded paths** (no company lookup):
`admin`, `super`, `superadmin`, `panel`, `candidate`, `api`, `static`, `media`, `register`, `recruitpanel`, `choose-role`, `login`

---

## Data Flow

### Company Creation (Superadmin)

```
1. Superadmin opens /superadmin/companies/create/
2. Fills in company name, brand color, address, summary, logo
3. Slug auto-generated from name (lowercase, hyphenated)
4. On save: slug collision check → append counter if needed
5. Company record created with is_active=True
6. Redirect to company list with success message
```

### Company Edit by Recruiter (via Edit Request)

```
1. Recruiter opens /{slug}/panel/company/edit/
2. Fills in proposed changes (name, website, email, address, summary, brand_color, logo)
3. CompanyEditRequest created with status=pending
4. Superadmin reviews at /superadmin/edit-requests/<pk>/
5. Field-by-field diff displayed
6. Superadmin approves → changes applied to Company, status=approved
7. Superadmin rejects → no changes, status=rejected
```

### Company Edit by Superadmin (Direct)

```
1. Superadmin opens /superadmin/companies/<pk>/edit/
2. Edits any field directly (no approval needed)
3. Slug regenerated if name changed (collision check applied)
4. Is Active checkbox toggles availability
5. Changes saved immediately, redirect to list
```

---

## Models Referenced (Multi-Tenant Data Model)

All models with `company` ForeignKey — data is scoped per-company:

| Model | File | Key Company-Scoped Fields |
|---|---|---|
| `Company` | `company/models.py` | Root entity |
| `CompanyEditRequest` | `company/models.py` | `company` FK |
| `Stage` | `api/models.py` | `company` FK, `key`, `label`, `order` |
| `Application` | `api/models.py` | `company` FK, candidate record |
| `JobPosition` | `api/models.py` | `company` FK, job listing |
| `Automation` | `api/models.py` | `company` FK, per-position rules |
| `UserProfile` | `api/models.py` | `company` FK, user's company assignment |
| `UserRole` | `api/models.py` | `company` FK (null for superadmin/candidate) |

---

## Auth Architecture

Two parallel auth systems exist (transition in progress):

| System | Auth Method | Decorator | Where Used |
|---|---|---|---|
| Legacy `is_superuser` | Username + Password | `super_login_required` | `adminpanel/` views |
| New `UserRole` | Phone + PIN | `superadmin_required` | `superadmin/` views |

Both systems grant the same company management access. The new `superadmin` app (`/superadmin/`) is the active target; `adminpanel/` superadmin views remain in place as-is.

---

## Implementation Order

1. **Company list view** — `superadmin/views.py`: `company_list` with annotations
2. **Company detail view** — `superadmin/views.py`: `company_detail` with stats
3. **Company edit view** — `superadmin/views.py`: `company_edit` with direct save
4. **URL routes** — `superadmin/urls.py`: wire all company routes
5. **Templates** — `companies.html`, `company_detail.html`, `company_form.html`
6. **Sidebar** — Update `base.html` to link Companies nav item
7. **Edit requests** — Add `CompanyEditRequest` review views to superadmin
