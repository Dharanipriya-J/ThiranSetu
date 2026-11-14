# ThiranSetu — API Reference

Base URL (local): `http://localhost:8000` · Interactive docs: `http://localhost:8000/docs`

All endpoints except `/api/health`, `/api/auth/register`, `/api/auth/login`, `/api/skills`, `/api/roles` require
`Authorization: Bearer <access_token>`. Errors are returned as `{"detail": "<message>"}` (422 for validation errors uses FastAPI's default list format).
Rate-limited endpoints return `429` with `Retry-After`.

Skill names are canonical strings (e.g. `"Python"`, `"SQL"`, `"Power BI"`, `"Node.js"`). Levels: `beginner | intermediate | advanced`.

---

## System
| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | `{status, version, llm_mode: "gemini" \| "deterministic"}` |

## Auth (rate limited)
| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/api/auth/register` | `{email, password (>=8, letter+digit), full_name}` | `201 TokenResponse` |
| POST | `/api/auth/login` | `{email, password}` | `TokenResponse` (401 on bad credentials) |
| POST | `/api/auth/logout` | – | `204` (server-side token revocation via token version) |
| GET | `/api/auth/me` | – | `User` |

`TokenResponse = {access_token, token_type: "bearer", user: User}`
`User = {id, email, full_name, created_at}`

## Profile
| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/api/profile` | – | `Profile` |
| PUT | `/api/profile` | `ProfileUpdate` (all fields optional) | `Profile` (triggers agent re-run with `profile_updated` or `goal_changed`) |

```
Profile = {
  full_name, education, college, graduation_year: int|null,
  technical_skills: [{name, self_level}], soft_skills: [str],
  projects: [{title, description, skills: [str]}],
  certifications: [{name, issuer, year: int|null}],
  experience_years: number, experience_summary: str,
  career_interests: [role_id], target_role: role_id|null,
  current_location: str, preferred_locations: [str], willing_to_relocate: bool,
  work_mode: "remote"|"hybrid"|"onsite"|"any",
  expected_salary_lpa: number|null, min_salary_lpa: number|null,
  learning_language: lang_code, app_language: lang_code,
  completeness: int (0-100, read-only)
}
lang_code = en|ta|hi|te|kn|ml|bn|mr
```

## Reference data
| Method | Path | Response |
|---|---|---|
| GET | `/api/skills` | `[{name, category, assessable: bool}]` |
| GET | `/api/roles` | `[{id, title, description, skills: [{skill, weight, importance: "core"\|"supporting"}]}]` |

## Assessments
| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/api/assessments/available` | – | `[{skill, levels: [level], question_count}]` |
| POST | `/api/assessments/start` | `{skill, level}` | `AssessmentSession` |
| POST | `/api/assessments/{attempt_id}/submit` | `{answers: {question_id: answer_string}}` | `AssessmentResult` |
| GET | `/api/assessments/history` | – | `[{attempt_id, skill, level, score, completed_at}]` |
| GET | `/api/skills/verified` | – | `[VerifiedSkill]` |

```
AssessmentSession = {attempt_id, skill, level, questions: [
  {id, type: "mcq"|"code_output"|"debugging"|"scenario", topic, prompt, code: str|null, options: [str]|null}
]}   // correct answers are never sent to the client
// mcq/debugging/scenario: answer = the selected option text. code_output: free-text answer.

AssessmentResult = {attempt_id, skill, level, score (0-100), correct, total,
  topic_breakdown: [{topic, correct, total, percent}], strong_topics: [str], weak_topics: [str],
  recommendations: [str], verified_score, proficiency: "not_verified"|"beginner"|"intermediate"|"advanced",
  review: [{question_id, prompt, correct: bool, your_answer, correct_answer, explanation}]}

VerifiedSkill = {skill, self_reported_level: level|null, verified_score: number|null,
  proficiency, attempts: int, last_assessed: datetime|null, strong_topics, weak_topics, status: "verified"|"self_reported"|"assessed_only"}
```
`verified_score` is a recency-weighted average of the latest (max 3) attempts — one test never permanently classifies a learner.

## Agentic orchestrator
| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/api/agents/run` | `{trigger: "manual"\|"profile_updated"\|"assessment_completed"\|"goal_changed"\|"learning_completed"}` | `OrchestratorResult` |
| GET | `/api/agents/latest` | – | `OrchestratorResult` (runs once if none exists) |

```
OrchestratorResult = {run_id, created_at, trigger, llm_mode,
  trace: [{agent, status: "ok"|"skipped"|"error", duration_ms, summary, decisions: [str]}],
  skill_intelligence: SkillIntelligence, market: MarketReport, careers: [CareerRecommendation],
  top_jobs: [JobSummary], recommended_courses: [CourseGroup], roadmap: Roadmap, mentor_brief: str}
```

## Insights
| Method | Path | Response |
|---|---|---|
| GET | `/api/intelligence` | `SkillIntelligence` |
| GET | `/api/market` | `MarketReport` |
| GET | `/api/careers` | `[CareerRecommendation]` |
| PUT | `/api/careers/target` | body `{role_id}` → `Roadmap` (goal change → recalculation) |
| GET | `/api/dashboard` | `Dashboard` |

```
SkillIntelligence = {
  strong: [{skill, score, reason}], weak: [{skill, score, reason, weak_topics}],
  missing: [{skill, required_by: [role title], demand_count}],
  emerging: [{skill, reason, evidence}], declining: [{skill, reason, evidence}],
  outdated: [{skill, issue, recommendation, evidence, source}],
  unverified: [{skill, self_reported_level}], targeted_practice: [str], notice: str }

MarketReport = { data_source: {label, is_demo: bool, vacancies_analyzed, as_of, scope},
  top_skills: [{skill, demand_count, share_percent, mandatory_count, preferred_count}],
  role_demand: [{role_id, title, vacancies}], emerging: [{skill, reason, evidence}],
  stable: [str], declining: [{skill, reason, evidence}], notes: [str] }

CareerRecommendation = { role_id, title, score (0-100), label: "Highly Recommended"|"Recommended"|"Potential Career"|"Requires Skill Development",
  components: {skill_match, interest, market_demand, location, salary, experience},   // each 0-100
  weights: {same keys: number}, matching_skills: [{skill, score}], improve_skills: [{skill, score, target}],
  missing_skills: [str], demand_level: "high"|"medium"|"low", vacancies: int,
  salary_range: null | {min_lpa, max_lpa, source},  // from platform vacancies only, else null
  location_fit: str, explanation: str, learning_path: [str], is_target: bool }
```

## Jobs
| Method | Path | Body / Query | Response |
|---|---|---|---|
| GET | `/api/jobs` | `q, company, location, work_mode, min_salary, max_experience, min_score, sort=score\|date\|salary, page=1, page_size=10` | `{items: [JobSummary], total, page, page_size}` |
| GET | `/api/jobs/{id}` | – | `JobDetail` |
| POST | `/api/jobs/extract` | `{description}` | `{mandatory_skills, preferred_skills, experience_years, education}` |
| POST | `/api/jobs` | `JobCreate` | `JobDetail` (requirements auto-extracted from description) |
| GET | `/api/applications` | – | `[Application]` |
| POST | `/api/applications` | `{job_id, status?: "saved"}` | `Application` |
| PATCH | `/api/applications/{id}` | `{status?, notes?}` | `Application` |
| DELETE | `/api/applications/{id}` | – | `204` |

```
JobSummary = { id, company, title, location, work_mode, salary: {min_lpa, max_lpa, disclosed: bool, label},
  experience_min_years, posted_date, deadline, apply_url, source, is_demo: bool,
  mandatory_skills, preferred_skills, matching_skills, missing_skills, score, saved: bool }

JobDetail = JobSummary + { description, education, match: {
  score, components: {mandatory, preferred, experience, education, location, salary}, weights,
  strong_matches: [{skill, score}], partial_matches: [{skill, score, target}],
  missing_mandatory: [str], missing_preferred: [str], not_assessed: [str],
  qualification_gaps: [str], salary_fit: {status: "meets"|"overlap"|"below_expectation"|"below_minimum"|"not_disclosed"|"no_preference", message},
  location_fit: {status: "match"|"remote"|"relocation"|"mismatch"|"no_preference", message},
  explanation: str }, recommended_courses: [CourseGroup] }

JobCreate = { company, title, description (>=50 chars), location, work_mode, salary_min_lpa?, salary_max_lpa?,
  experience_min_years, education, posted_date (YYYY-MM-DD), deadline?, apply_url (https only), source }

Application = { id, job: JobSummary, status: "saved"|"applied"|"interviewing"|"offer"|"rejected", notes, updated_at }
```
`applied` is set **only by the learner** — the platform never submits applications; "Apply Now" opens `apply_url` in a new tab.

## Courses
| Method | Path | Query | Response |
|---|---|---|---|
| GET | `/api/courses` | `skill, platform, language, audio_language, subtitle_language, price=free\|paid, difficulty, max_hours, min_rating, q, page, page_size` | `{items: [Course], total, page, page_size}` |
| GET | `/api/courses/recommended` | – | `[CourseGroup]` |
| GET | `/api/courses/{id}/equivalents` | `language` | `{course, language, equivalents: [{course, overlap_percent, shared_skills, shared_outcomes, verdict}]}` |

```
Course = { id, title, platform, provider, url, language, audio_languages: [str], subtitle_languages: [str],
  difficulty, duration_hours: number|null, price: {is_free, label}, rating: null | {value, source},
  skills: [str], outcomes: [str], verification: str }
CourseGroup = { skill, reason, courses: [Course] }
```

## Roadmap
| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/api/roadmap` | – | `Roadmap` |
| POST | `/api/roadmap/regenerate` | – | `Roadmap` |
| PATCH | `/api/roadmap/steps/{step_id}` | `{status: "not_started"\|"in_progress"\|"completed"}` | `Roadmap` |

```
Roadmap = { target_role: {id, title}|null, generated_at, reason, progress_percent, steps: [
  {id, order, skill, priority: "high"|"medium"|"low", reason, course: Course|null, estimated_hours,
   exercise, project, status, reassessment_required: bool, current_score: number|null, target_score}] }
```
Completing a step sets `reassessment_required=true`; passing a reassessment updates scores, careers, job matches and regenerates the roadmap.

## AI Career Mentor (rate limited)
| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/api/mentor/suggestions` | – | `[str]` |
| POST | `/api/mentor/chat` | `{message (1-1000 chars), language: lang_code}` | `{reply, mode: "gemini"\|"deterministic", intent, sources: [str]}` |

## Dashboard
```
Dashboard = { profile_completeness, llm_mode, verified_skills: [VerifiedSkill], strongest: [..], weakest: [..],
  missing_skills: [str], outdated_alerts: [..], emerging_skills: [..], top_careers: [CareerRecommendation] (3),
  top_jobs: [JobSummary] (3), salary_summary: {expected_lpa, min_lpa, jobs_meeting_minimum, jobs_with_disclosed_salary},
  recommended_courses: [Course] (3), roadmap_progress: int, assessment_history: [..], readiness_trend: [{date, readiness}],
  target_role: {id, title}|null, agent_trace: [..] }
```
