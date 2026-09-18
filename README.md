# ERP-JSTU

Enterprise Resource Planning system for **Jamalpur Science and Technology University**,
built from the project proposal dated 16 July 2026.

Every screen sits behind an entry gate that asks for a university e-mail address and a
**6-digit passkey issued by the administrator**. Nothing in the system is reachable until
that pair is verified.

---

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_demo         # demo data + demo passkeys
python manage.py createsuperuser   # your own Django admin login
python manage.py runserver
```

Open <http://127.0.0.1:8000/> — you land straight on the passkey screen.

### Demo sign-in

All seeded accounts use the passkey **`482913`**.

| Panel               | E-mail                       | Passkey  |
|---------------------|------------------------------|----------|
| Student             | `student001@jstu.edu.bd`     | `482913` |
| Teacher             | `mohammad.hasan@jstu.edu.bd` | `482913` |
| Admin / Registrar   | `registrar@jstu.edu.bd`      | `482913` |
| Controller of Exams | `exam@jstu.edu.bd`           | `482913` |
| Accounts Officer    | `accounts@jstu.edu.bd`       | `482913` |
| ICT Cell            | `ict@jstu.edu.bd`            | `482913` |

`seed_demo` also creates `student001` … `student040`. Every seeded account has the
Django password `jstu@2026` for `/admin/`.

---

## Issuing passkeys

Two routes, both administrator-only:

**Django admin** — `/admin/` → *Users* → open a user → **Entry passkey** inline.
Or select users in the list and run the action
*"Issue / regenerate a 6-digit entry passkey"*; the generated codes appear in the
confirmation banner.

**Admin Panel** — *System management → User & role management* → **Issue**, **Unlock**
or **Disable** per account. A newly issued code is shown once, in the banner.

Five wrong codes lock a passkey for 15 minutes. `GATE_MAX_ATTEMPTS` and
`GATE_LOCKOUT_MINUTES` in `erp_jstu/settings.py` control this.

---

## Apps

| App            | Contains |
|----------------|----------|
| `accounts`     | `User` (role + designation), `AccessPasskey`, `AuditLog`, gate views, gate middleware |
| `academics`    | Department, Program, Student, Teacher, Course, CourseOffer, EnrollmentDeadline, Enrollment, Marks, ExamRoutine, ClassRoutine, FormFillup, FeePayment, AdmitCard |
| `portal`       | Notice, WebsiteMenu, ComplaintSuggestion, CourseFeedback, Award, LeaveApplication, HouseAllotment, VehicleRequisition, Event, ResearchPost, Publication, ExamRemuneration, PostgraduateApplication |
| `studentpanel` | Student Panel — views, URLs, templates (proposal §7.1) |
| `teacherpanel` | Teacher Panel — views, URLs, templates (proposal §7.2) |
| `adminpanel`   | Admin / Registrar Panel — views, URLs, templates (proposal §7.3) |

The three panel apps hold no models; they render the interfaces over the shared models.

## Panels

**Student** (green) — profile, guardian and personal info, bank account, digital ID card,
internet and network info, university e-mail, notice board, admit card, exam result,
form fill-up, my enrollments, payment invoice, complaint/suggestion box, feedback form,
awards and achievements, help and support.

**Teacher** (blue) — marks assign, postgraduate marks and applications, class routine,
exam routine, my courses and students, leave application, house allotment, vehicle
reservation, event and meeting, research news/blog, my publications, exam remuneration,
BAURES repository, notice board, profile.

**Admin / Registrar** (dark navy + amber) — add course, manage course offer, enrollment
deadline, routine management, exam schedule, form fill-up management, student form
fill-up status, approval and finalization, admit card management, reports, website
control panel, notice management, complaint routing, staff requests, user and role
management, audit trail.

---

## Notes on the build

- Tailwind is loaded from the CDN and the component layer is declared **inside each base
  template** with `@apply` — there are no separate CSS files, per the brief.
- Left sidebars, the colour of each panel and the card layouts follow the proposal
  mockups.
- Anonymous complaints store **no** student foreign key at all (proposal §13), so
  anonymity holds at the database level rather than being hidden in the interface.
- `AuditLog` records every gate attempt, approval, publication and rejection with the
  originating IP.
- SQLite is the development default. For deployment, switch `DATABASES` in
  `erp_jstu/settings.py` to PostgreSQL or MySQL.

## Deployment

Export three variables and the security settings switch on by themselves — HTTPS
redirect, secure session and CSRF cookies, one-year HSTS, `X-Frame-Options: DENY`
and content-type nosniff (proposal §13). No file edits needed.

```bash
export JSTU_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(64))')"
export JSTU_DEBUG=0
export JSTU_ALLOWED_HOSTS="erp.jstu.edu.bd,www.jstu.edu.bd"

python manage.py collectstatic --no-input
python manage.py check --deploy      # passes with 0 issues
gunicorn erp_jstu.wsgi:application --bind 0.0.0.0:8000
```

Leave the variables unset and the development server keeps working over plain HTTP.

## Grading

Marks save on a 4.00 scale: 80+ A+ (4.00), 75 A (3.75), 70 A- (3.50), 65 B+ (3.25),
60 B (3.00), 55 B- (2.75), 50 C+ (2.50), 45 C (2.25), 40 D (2.00), below 40 F.
