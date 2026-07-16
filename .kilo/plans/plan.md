# Multi-Tenant Recruitment Pipeline — Database Plan

## Context

Adding multi-company support to the existing single-tenant pipeline. Each company has its own login credentials, staff, positions, and pipeline stages.

## Models

### Company (new)
| Field | Type | Notes |
|-------|------|-------|
| id | AutoField PK | |
| name | CharField(200) | |
| email | EmailField | unique, used for login |
| password | CharField(128) | Django-hashed |
| phone | CharField(30) | blank |
| website | URLField | blank |
| logo | ImageField | blank, upload_to='logos/' |
| is_active | BooleanField | default=True |
| created_at | DateTimeField | auto_now_add |

### Staff (new)
| Field | Type | Notes |
|-------|------|-------|
| id | AutoField PK | |
| user | OneToOneField→auth.User | |
| company | ForeignKey→Company | related_name='staff' |
| role | CharField(20) | choices: owner, recruiter, hiring_manager, viewer |
| is_active | BooleanField | default=True |

### JobPosition (modified)
- **Add:** `company` ForeignKey→Company (required, CASCADE)
- **Drop:** `unique=True` on `title`
- **Add:** `unique_together = (company, title)`

### Stage (modified — per-company)
- **Add:** `company` ForeignKey→Company (required, CASCADE)
- **Drop:** `unique=True` on `key`
- **Add:** `unique_together = (company, key)`

### Application (modified)
- **Add:** `company` ForeignKey→Company (CASCADE)
- **Replace:** `position` (free-text) → `job_position` ForeignKey→JobPosition (null=True, blank=True)
- **Replace:** `status` (CharField) → `stage` ForeignKey→Stage (null=True, blank=True)

### Automation (modified)
- **Drop:** `position` ForeignKey + `stage` CharField
- **Add:** `company` ForeignKey→Company (CASCADE)
- **Add:** `stage` ForeignKey→Stage (CASCADE)
- **New unique_together:** `(company, stage)`

### CVExtract (unchanged)

## Authentication

- **Company login:** custom auth backend authenticates against Company.email + Company.password via `django.contrib.auth.hashers.check_password`
- **Staff login:** standard Django auth.User login
- **Admin login:** existing superuser (coexists with both)

## Migration Strategy

1. Create bootstrap Company ("Solar Solutions") for existing data
2. Migrate existing global Stages → assign to bootstrap company
3. Migrate existing JobPositions → assign to bootstrap company
4. Migrate Application.position text → best-effort FK match
5. Migrate Application.status char → FK match to Stage.key

## Queryset Scoping

- All adminpanel views filter by `request.company` (stored in session)
- Superusers bypass company scoping
