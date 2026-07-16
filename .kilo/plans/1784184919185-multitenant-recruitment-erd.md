# Recruitment Pipeline — Multi-Tenant Database Architecture (ERD + Plan)

## Context

The current Django project (`api`, `agents`, `adminpanel`, `frontend`) is single-tenant:
- `JobPosition.title` is globally unique — no company association.
- `Application.position` is free-text (not linked to `JobPosition`).
- `Stage` and `Automation` are **global/system-wide**, so every company shares one pipeline.

Goal: make the pipeline manageable per company. Introduce a `Company` model, each
company has `Staff`, owns `JobPosition`s, and has its **own** ordered pipeline of
`Stage`s with per-stage `Automation`s. This is a multi-tenant (by company) redesign.

Confirmed decisions:
1. **Per-company stages** — each `Company` owns its own ordered `Stage` rows + `Automation`s.
2. **Staff = `auth.User` + `Profile` model** (FK to Company, with role) — reuse Django auth.

## Current Models (from `api/models.py`, `agents/models.py`)
- `Stage(key, label, order)` — global
- `Application(full_name, email, phone, position[text], experience, resume, cover_letter, status[key], submitted_at)`
- `JobPosition(title[unique], description, base_salary, hourly_rate, location, requirements, is_active, created_at)`
- `Automation(position→JobPosition, stage[key], description)` — unique (position, stage)
- `CVExtract(application→Application, raw_text, summary, skills, experience, education, certifications, languages, contact, total_experience_years, extracted_at, status)`

## Proposed ERD (entities & relationships)

```
                         +-------------------+
                         |     auth.User     |   (Django built-in)
                         +-------------------+
                                  | 1
                                  |
                                  | 1
                         +-------------------+
                         |     Profile       |   NEW  (agents or api app)
                         +-------------------+
                         | id                |
                         | user  (1:1 User)  |
                         | company (FK)      |
                         | role  (choices)   |  e.g. owner, recruiter, hiring_manager, viewer
                         | is_active         |
                         +-------------------+
                                  |
                                  | *
                                  v
                         +-------------------+
                         |    Company        |   NEW
                         +-------------------+
                         | id                |
                         | name (unique)     |
                         | slug              |
                         | domain / logo     |
                         | created_at        |
                         +-------------------+
                                  | 1
                                  | *
        +-------------------------+--------------------------+
        | *                                                  | *
        v                                                    v
+-------------------+                          +------------------------+
|   JobPosition     |  1                       |        Stage          |  NEW (per-company)
+-------------------+  *                       +------------------------+
| id                |<-+                       | id                     |
| company (FK)      |  | *                     | company (FK)           |
| title             |  |                       | key                    |
| description       |  |                       | label                  |
| base_salary       |  |                       | order                  |
| hourly_rate       |  |                       +------------------------+
| location          |  |                                 | 1
| requirements      |  |                                 | *
| is_active         |  |                                 v
| created_at        |  |                       +------------------------+
+-------------------+  |                       |      Automation        |  (re-pointed)
        | 1            |                       +------------------------+
        | *            |                       | id                     |
        v              |                       | company (FK) NEW       |
+-------------------+  |                       | stage (FK→Stage) NEW   |
|   Application     |  |                       | description            |
+-------------------+  |                       +------------------------+
| id                |  |
| company (FK) NEW  |  |
| job_position (FK) |--+   (replaces free-text `position`)
| full_name         |      (nullable: applied before a position existed)
| email             |      (nullable: applied before a position existed)
| phone             |
| experience        |
| resume            |
| cover_letter      |
| stage (FK→Stage)  |   (replaces `status` key)
| submitted_at      |
+-------------------+
        | 1
        | *
        v
+-------------------+
|    CVExtract      |   (unchanged; FK→Application kept)
+-------------------+
```

### Relationship summary
- `Company 1 ── * Profile` (staff); `Profile 1 ── 1 auth.User`
- `Company 1 ── * JobPosition`
- `Company 1 ── * Stage` (ordered pipeline, per-company)
- `Company 1 ── * Automation`; `Stage 1 ── * Automation` (unique per company+stage)
- `Company 1 ── * Application`; `JobPosition 1 ── * Application`
- `Application * ── 1 Stage` (current pipeline step); `Application 1 ── * CVExtract`

## Data-model changes (implementation tasks)
1. **Company** (new, in `api/models.py`): `name` (unique), `slug`, optional `domain`, `logo`, `created_at`.
2. **Profile** (new): `user` OneToOne→User, `company` FK→Company, `role` (choices), `is_active`. Add `get_company()` helper.
3. **JobPosition**: add `company` FK (cascade); drop global `unique=True` on `title` → `unique_together`/`UniqueConstraint` on `(company, title)`.
4. **Stage**: add `company` FK (cascade). `unique_together = (company, key)`. Seed a default ordered set per new company.
5. **Automation**: replace `position` FK + `stage` char with `company` FK and `stage` FK→Stage; `unique_together = (company, stage)`.
6. **Application**: add `company` FK; replace free-text `position` with `job_position` FK→JobPosition (null=True, blank=True); replace `status` char with `stage` FK→Stage (null=True). Keep backward-compatible `status_label()` via `stage.label`.
7. **CVExtract**: unchanged (already FK→api.Application).
8. Remove the module-level `STAGES`/`STAGE_KEYS` global constants from `api/models.py`; stages become data owned by each company.

## Migration / rollout considerations
- Existing global `Stage` rows and `Automation`(position, stage) must be migrated: assign to a default "system" or first `Company`, or seed a fresh default pipeline per company on creation.
- `Application.position` free-text → requires a data-migration mapping existing text to new `JobPosition`/`Stage` or leaving `job_position`/`stage` null and backfilling.
- `JobPosition.title` unique change requires dropping the global unique constraint and creating a per-company constraint; handle duplicate titles across companies.
- Decide whether to create one bootstrap `Company` for existing data, or treat existing rows as "unassigned" until reassigned.

## Validation
- `python manage.py makemigrations && migrate` succeeds with no integrity errors.
- `python manage.py check`.
- Admin: `Company` and `Profile` registered; `JobPosition`, `Stage`, `Automation`, `Application` show `company` filter and scoped querysets.
- A quick test that two companies can have Stages with the same `key` but different `company` (proves per-company pipeline isolation).

## Open questions (not blocking)
- Should `Stage.order` be global integers per company, or a linked-list `next_stage` FK? Ordered integer is simplest; confirm.
- Multi-tenancy enforcement: scope all API/admin querysets by `request.user.profile.company` (out of scope for ERD, note for implementation).
- Soft-delete vs hard-delete for Company; recommend cascade with safeguard.
