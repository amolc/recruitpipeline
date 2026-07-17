# User Model & Authentication — Recruitme

## Overview

A unified user model where **phone number** is the sole identifier and a **4-digit PIN** is the password. A single person can act in three roles — **superadmin**, **recruiter**, or **candidate** — each with its own independent login session.

---

## User Model

Replace Django's default `auth.User` with a custom `User` model.

| Field | Type | Notes |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `phone` | `CharField(15)` | **unique** — primary identifier, e.g. `+919876543210` |
| `pin` | `CharField(128)` | Hashed 4-digit PIN |
| `secretname` | `CharField(100)` | **required** — recovery secret, set on first registration |
| `email` | `EmailField` | blank, optional for notifications |
| `name` | `CharField(200)` | Full name, blank initially |
| `is_active` | `BooleanField` | default=True |
| `created_at` | `DateTimeField` | auto |
| `updated_at` | `DateTimeField` | auto |

**Settings:**
- `USERNAME_FIELD = 'phone'`
- `REQUIRED_FIELDS = []` (no email required on creation)
- `AUTH_USER_MODEL = 'api.User'`

---

## Role Model

A separate `UserRole` model links a user to one or more roles, each with role-specific context.

| Field | Type | Notes |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `user` | `ForeignKey(User)` | CASCADE |
| `role` | `CharField(20)` | choices: `superadmin`, `recruiter`, `candidate` |
| `company` | `ForeignKey(Company)` | **null, blank** — only for `recruiter` role |
| `is_active` | `BooleanField` | default=True |

**Constraints:**
- `unique_together = (user, role)` — one role entry per user per role type
- `company` is required when role=`recruiter`, null for `superadmin` and `candidate`

**Example:**
A person who is both a recruiter at "Acme Corp" and a candidate on the platform would have two `UserRole` rows:
```
1. user=Alice, role=recruiter, company=Acme Corp
2. user=Alice, role=candidate, company=null
```

---

## Authentication Flow

### Registration (first-time user)

Happens within the context of the portal the user is trying to access.

```
User visits /superadmin/register/
        or /recruiter/register/
        or /candidate/register/

        1. Enter phone number
        2. System checks if phone exists
           ├── New → prompt: "Create a 4-digit PIN"
           │         Submit → User + UserRole created
           │         Auto-login with role
           │         Redirect to dashboard
           │
           └── Exists → prompt: "Enter your 4-digit PIN"
                         Authenticate → check UserRole for this portal
                         ├── Has role → login, redirect to dashboard
                         └── No role → "You don't have access to this portal"
```

### Login (returning user)

```
User visits any portal's login page

        1. Enter phone number
        2. Enter 4-digit PIN
        3. Authenticate against User.pin (hashed)
        4. Check UserRole for the current portal's role
           ├── Has matching UserRole → login, set session role, redirect
           └── No matching UserRole → "No access to this portal"
```

### PIN Validation

- PIN is exactly 4 numeric digits
- Stored hashed using Django's `make_password` / `check_password`
- On creation: `user.pin = make_password(pin)`
- On login: `check_password(pin, user.pin)`

---

## Session Model (Per-Portal Sessions)

Each portal maintains its own independent session. The same user can be logged into multiple portals simultaneously in different browser contexts.

### Implementation

A custom `UserSession` model tracks active sessions per role:

| Field | Type | Notes |
|---|---|---|
| `id` | `BigAutoField` | PK |
| `user` | `ForeignKey(User)` | CASCADE |
| `role` | `CharField(20)` | superadmin / recruiter / candidate |
| `session_key` | `CharField(40)` | Django session key |
| `ip_address` | `GenericIPAddressField` | null |
| `user_agent` | `TextField` | blank |
| `created_at` | `DateTimeField` | auto |
| `last_activity` | `DateTimeField` | auto |

### How It Works

1. User logs into `/superadmin/login/` → Django creates a session → `UserSession` record saved with `role=superadmin`
2. Same user logs into `/candidate/login/` in another browser → separate Django session → `UserSession` record with `role=candidate`
3. Each session independently times out

### Auth Backend

A custom authentication backend `PhoneAuthBackend`:

```python
class PhoneAuthBackend(BaseBackend):
    def authenticate(self, request, phone=None, pin=None):
        try:
            user = User.objects.get(phone=phone)
            if check_password(pin, user.pin):
                return user
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        return User.objects.filter(pk=user_id).first()
```

### Login View Pattern (per portal)

```python
def superadmin_login(request):
    if request.method == 'POST':
        phone = request.POST['phone']
        pin = request.POST['pin']
        user = authenticate(request, phone=phone, pin=pin)
        if user and user.userrole_set.filter(role='superadmin', is_active=True).exists():
            login(request, user)
            request.session['role'] = 'superadmin'
            return redirect('superadmin_dashboard')
        # error handling...
    return render(request, 'superadmin/login.html')
```

---

## Portal Separation & Access Control

### Login URLs
| Portal | Login URL | Register URL |
|---|---|---|
| Superadmin | `/superadmin/login/` | `/superadmin/register/` |
| Recruiter | `/{company_slug}/login/` | `/{company_slug}/register/` |
| Candidate | `/candidate/login/` | `/candidate/register/` |

### Access Decorators

Each portal has its own decorator checking `session['role']`:

| Decorator | Checks |
|---|---|
| `@superadmin_required` | `is_authenticated` + `session['role'] == 'superadmin'` |
| `@recruiter_required` | `is_authenticated` + `session['role'] == 'recruiter'` |
| `@candidate_required` | `is_authenticated` + `session['role'] == 'candidate'` |

### Logout

Each portal's logout:
```
POST /superadmin/logout/   → clears session + UserSession → redirect to /superadmin/login/
POST /{slug}/logout/       → clears session + UserSession → redirect to /{slug}/login/
POST /candidate/logout/    → clears session + UserSession → redirect to /candidate/login/
```

Logout only destroys the current role's session. If the user is logged into another portal in a different browser, that session remains intact.

---

## Migration from Current System

### Current State
- Django's default `auth.User` with username/password
- `UserProfile` links users to companies with a role
- Superusers use `is_superuser` boolean
- Candidates are not yet linked to User model

### Migration Plan

1. **Create custom User model** with `phone` as `USERNAME_FIELD`
2. **Create `UserRole` model** to replace both `UserProfile` and `is_superuser`
3. **Create data migration** to migrate existing `auth.User` records:
   - For users without a profile: create `UserRole(role='superadmin')`
   - For users with a profile: create `UserRole(role='recruiter', company=profile.company)`
   - Phone can be initially populated from username or left blank for manual update
4. **Create `UserSession` model** for session tracking
5. **Update `AUTH_USER_MODEL`** setting (requires a fresh database or careful migration due to Django's `auth.User` dependency)
6. **Replace login views** in all three portals
7. **Add registration views** for each portal

---

## User Flow Diagrams

### First-Time Registration (as Candidate)

```
                    ┌──────────────────────────────────┐
                    │  /candidate/register/             │
                    │  "Sign up with your phone number" │
                    └──────────┬───────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Enter phone number  │
                    └──────────┬───────────┘
                               │
                               ▼
              ┌──────────────────────────────────────┐
              │  Phone exists in system?              │
              └──────────┬───────────────┬────────────┘
                         │               │
                      Yes │               │ No
                         │               │
                         ▼               ▼
          ┌────────────────────────┐  ┌─────────────────────────┐
          │ "Enter your 4-digit   │  │ "Create a 4-digit PIN"  │
          │  PIN to continue"     │  └───────────┬─────────────┘
          └──────────┬─────────────┘              │
                     │                            │
                     ▼                            ▼
          ┌──────────────────────┐     ┌──────────────────────┐
          │ authenticate(phone,  │     │ Create User           │
          │   pin)               │     │ + UserRole(candidate) │
          └──────────┬───────────┘     └──────────┬───────────┘
                     │                            │
                     ▼                            ▼
          ┌──────────────────────────────────────────┐
          │  login(request, user)                     │
          │  session['role'] = 'candidate'            │
          │  redirect → /candidate/dashboard/         │
          └──────────────────────────────────────────┘
```

### Returning User Login

```
                    ┌──────────────────────────────────┐
                    │  Navigate to portal login        │
                    │  e.g. /{slug}/login/             │
                    └──────────┬───────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Enter phone + PIN   │
                    └──────────┬───────────┘
                               │
                               ▼
              ┌──────────────────────────────────────┐
              │  authenticate(phone, pin) success?   │
              └──────────┬───────────────┬────────────┘
                         │               │
                       Yes │               │ No
                         │               │
                         ▼               ▼
          ┌────────────────────────┐  ┌────────────────────┐
          │  UserRole matches      │  │ "Invalid phone or │
          │  this portal's role?   │  │  PIN"             │
          └──────────┬─────────────┘  └────────────────────┘
                     │
              ┌──────┴──────┐
              │             │
            Yes │             │ No
              │             │
              ▼             ▼
   ┌──────────────────┐  ┌──────────────────────────┐
   │ login + set      │  │ "You do not have access  │
   │ session['role']  │  │  to this portal"         │
   │ redirect to      │  └──────────────────────────┘
   │ dashboard        │
   └──────────────────┘
```

---

## Forgot PIN Flow

Recovery is done via **secretname** — a word or phrase the user sets on first registration. This avoids needing SMS infrastructure for now (SMS OTP can be added later).

### User Model Addition

| Field | Type | Notes |
|---|---|---|
| `secretname` | `CharField(100)` | **required** — set on registration, used for PIN recovery |

### API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/auth/forgot-pin/` | Verify phone + secretname, return reset token |
| `POST` | `/api/auth/reset-pin/` | Set new PIN with valid reset token |

### Flow Diagram: Forgot PIN

```
                    ┌───────────────────────────────────────┐
                    │  Login page                            │
                    │  "Forgot PIN?" link → popup modal     │
                    └──────────┬────────────────────────────┘
                               │
                               ▼
               ┌──────────────────────────────────┐
               │  Popup: "Recover your PIN"       │
               │                                  │
               │  Phone number  [___________]     │
               │  Secretname    [___________]     │
               │                                  │
               │  [Submit]          [Cancel]      │
               └──────────┬───────────────────────┘
                          │
                          ▼
              ┌──────────────────────────────────────┐
              │  Phone + secretname match a user?     │
              └──────────┬───────────────┬────────────┘
                         │               │
                       Yes │               │ No
                         │               │
                         ▼               ▼
          ┌────────────────────────┐  ┌────────────────────────────┐
          │ Issue signed reset    │  │ "Phone or secretname not  │
          │ token (15 min expiry) │  │  recognized. Please try   │
          │ Show PIN reset form   │  │  again."                   │
          └──────────┬─────────────┘  └────────────────────────────┘
                     │
                     ▼
          ┌──────────────────────────────┐
          │  "Create a new 4-digit PIN"  │
          │  [____]  [____]              │
          │  Enter twice to confirm      │
          └──────────┬───────────────────┘
                     │
                     ▼
          ┌──────────────────────────────────────────┐
          │  POST /api/auth/reset-pin/                │
          │  reset_token + new_pin                    │
          │  Validate token → update user.pin         │
          └──────────┬────────────────────────────────┘
                     │
                     ▼
          ┌──────────────────────────────────────────┐
          │  "PIN reset successful!"                  │
          │  Redirect to login page                   │
          │  User logs in with new PIN (no SMS yet)   │
          └──────────────────────────────────────────┘
```

### Rate Limiting

- Max 5 forgot-PIN attempts per phone per hour (prevent brute force on secretname)
- Reset token expires after 15 minutes

### Integration with Registration

On registration, the user sets both their **4-digit PIN** and their **secretname**:

```
Register
  → Enter phone number
  → Create 4-digit PIN
  → Set secretname (e.g. "fluffy", "bluecar", "starwars")
  → User + UserRole created
  → Auto-login
```

The secretname hint displayed on the forgot PIN popup can optionally show the first and last character (e.g. "f***h") as a memory aid, configurable per portal later.

---

## Implementation Order

1. **Custom User model** — `phone` as `USERNAME_FIELD`, `pin` hashed, `name`, `email`
2. **`UserRole` model** — replaces `UserProfile` + `is_superuser`
3. **`UserSession` model** — tracks active sessions per role
4. **`PhoneAuthBackend`** — custom auth backend
5. **Settings** — `AUTH_USER_MODEL`, `AUTHENTICATION_BACKENDS`
6. **Data migration** — migrate existing users to new model
7. **Portal login views** — update all three portals with phone+PIN login
8. **Portal registration views** — new user creation with phone+PIN
9. **Access decorators** — `@superadmin_required`, `@recruiter_required`, `@candidate_required`
10. **Logout views** — destroy session + `UserSession` record
