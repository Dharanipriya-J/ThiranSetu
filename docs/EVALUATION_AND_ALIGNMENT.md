# ThiranSetu — Problem Statement Alignment, Architecture & Verification Report

## 1. Problem Statement Alignment Matrix

| Requirement / Module | Implementation Files | Status | Notes / Data Policy |
|---|---|---|---|
| **Module 1: Student Registration & Profile** | `backend/app/api/routers/auth.py`, `profile.py`, `backend/app/core/security.py`, `frontend/src/pages/RegisterPage.tsx`, `LoginPage.tsx`, `ProfilePage.tsx` | Implemented & Tested | scrypt password hashing, HS256 JWT with `token_version` revocation, separate current/preferred locations, relocation, work mode, salary expectations, preferred learning language. |
| **Module 2: Verified Skill Assessment Engine** | `backend/app/api/routers/assessments.py`, `backend/app/agents/skill_assessment.py`, `backend/app/data/questions_bank.json`, `frontend/src/pages/AssessmentsPage.tsx` | Implemented & Tested | Beginner/intermediate/advanced questions across Python, SQL, Excel, Power BI, ML, JS, Cloud, Cybersecurity; strong/weak topic breakdown; assessment history & reassessment recency weighting. |
| **Module 3: Skill Intelligence & Obsolescence** | `backend/app/agents/skill_intelligence.py`, `backend/app/data/skills.json`, `frontend/src/pages/IntelligencePage.tsx` | Implemented & Tested | Categorizes strong, weak, missing, emerging, stable, and declining-demand skills with rationale and next-step guidance. |
| **Module 4: Market Intelligence** | `backend/app/agents/market_intelligence.py`, `backend/app/api/routers/insights.py`, `frontend/src/pages/MarketPage.tsx` | Implemented & Tested | Displays high-demand, emerging, stable, and declining skills with source, date, geographical scope, and `Demonstration Data` labeling. |
| **Module 5: Dynamic Career Recommendation** | `backend/app/agents/career_matching.py`, `backend/app/services/scoring.py`, `backend/app/data/roles.json`, `frontend/src/pages/CareersPage.tsx` | Implemented & Tested | Ranks 9 career paths using 6-component explainable compatibility scoring; distinguishes Highly Recommended / Recommended / Potential Career / Requires Skill Development. |
| **Module 6: Company Requirement-Based Job Matching** | `backend/app/agents/job_matching.py`, `backend/app/api/routers/jobs.py`, `backend/app/data/jobs_demo.json`, `frontend/src/pages/JobsPage.tsx`, `JobDetailPage.tsx` | Implemented & Tested | Separates mandatory vs. preferred skills, evaluates salary/location/work-mode fit, links missing skills to courses, supports JD parsing (`POST /api/jobs/parse`), and opens external `apply_url`. |
| **Multilingual Course Discovery & Adaptive Roadmap** | `backend/app/agents/course_discovery.py`, `backend/app/api/routers/learning.py`, `backend/app/data/courses_demo.json`, `frontend/src/pages/CoursesPage.tsx`, `RoadmapPage.tsx` | Implemented & Tested | Recommends free/paid courses with syllabus-verified multilingual equivalence across 8 languages (`en`, `ta`, `hi`, `te`, `kn`, `ml`, `bn`, `mr`) and generates a 4-phase adaptive roadmap. |
| **AI Career Mentor & Analytics** | `backend/app/agents/career_mentor.py`, `orchestrator.py`, `frontend/src/pages/MentorPage.tsx`, `AnalyticsPage.tsx`, `SettingsPage.tsx` | Implemented & Tested | LangGraph 7-agent orchestrator + Gemini client with 300s SHA-256 cache and deterministic fallback; 8-language UI (`frontend/src/i18n/`). |

---

## 2. Evaluation Criteria Checklist

### Code Quality
- Clean separation of concerns across `core/`, `db/`, `schemas/`, `services/`, `agents/`, and `api/routers/` in the backend, and `api/`, `hooks/`, `components/`, `i18n/`, and `pages/` in the frontend.
- Backend linted with `ruff` (`backend/pyproject.toml`); frontend typechecked with `tsc -b` and bundled with Vite code splitting.

### Problem Statement Alignment
- Directly connects self-reported skills -> verified skill assessments -> skill gap & obsolescence intelligence -> market trends -> explainable career recommendations -> company vacancy matching -> multilingual course discovery & adaptive roadmap.
- Brand name appears strictly as `ThiranSetu` in English across all UI locales, code, and documentation.

### Security
- `backend/app/core/security.py`: scrypt password hashing with per-password salt + constant-time verification; HS256 JWT with `token_version` server-side invalidation on logout/password change.
- `backend/app/core/rate_limit.py`: in-memory rate limiting keyed by socket peer IP (resistant to spoofed `X-Forwarded-For` headers), 256 KB request body limit, and security response headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`).
- `backend/.env` is excluded via `.gitignore`.

### Efficiency
- `backend/app/services/gemini_client.py`: 300-second SHA-256 response cache reduces duplicate LLM calls and provides automatic deterministic fallback when offline or rate-limited.
- Frontend uses lazy-loaded i18n locale bundles (`frontend/src/i18n/index.ts`) and Vite chunk splitting.

### Testing
- **Backend**: `pytest` suite (`backend/tests/`) covering auth/profile, assessments/intelligence, and jobs/careers/courses/mentor/roadmap, plus `ruff check app tests`.
- **Frontend**: `vitest` + React Testing Library (`frontend/src/test/app.test.tsx`) plus `tsc -b && vite build`.

### Accessibility & Internationalization
- Semantic HTML landmarks (`<nav>`, `<main>`), form labels, keyboard-accessible controls, light/dark theme support (`useTheme.tsx`), and full 8-language UI switching (`en`, `ta`, `hi`, `te`, `kn`, `ml`, `bn`, `mr`).

---

## 3. Known Limitations & Demo Data Disclosures

1. **Demonstration Datasets**: `backend/app/data/jobs_demo.json` (10 sample Indian tech vacancies) and `backend/app/data/courses_demo.json` (18 sample courses) are curated demonstration records (`is_demo: true`), not live scraped feeds.
2. **External LLM Dependency**: Live Gemini responses require a valid `GEMINI_API_KEY` with available quota; otherwise, `gemini_client.py` seamlessly serves deterministic local fallback outputs.
3. **Local SQLite Storage**: Default configuration uses local SQLite (`thiransetu.db`) and in-memory rate limiting suitable for single-node local evaluation.
