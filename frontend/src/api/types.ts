// TypeScript mirror of docs/API.md — keep in sync with the backend contract.

export type LangCode = 'en' | 'ta' | 'hi' | 'te' | 'kn' | 'ml' | 'bn' | 'mr';
export type Level = 'beginner' | 'intermediate' | 'advanced';
export type WorkMode = 'remote' | 'hybrid' | 'onsite' | 'any';
export type LlmMode = 'gemini' | 'deterministic';

// System
export interface Health {
  status: string;
  version: string;
  llm_mode: LlmMode;
}

// Auth
export interface User {
  id: number | string;
  email: string;
  full_name: string;
  created_at: string;
}
export interface TokenResponse {
  access_token: string;
  token_type: 'bearer';
  user: User;
}
export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}
export interface LoginRequest {
  email: string;
  password: string;
}

// Profile
export interface TechnicalSkill {
  name: string;
  self_level: Level;
}
export interface Project {
  title: string;
  description: string;
  skills: string[];
}
export interface Certification {
  name: string;
  issuer: string;
  year: number | null;
}
export interface Profile {
  full_name: string;
  education: string;
  college: string;
  graduation_year: number | null;
  technical_skills: TechnicalSkill[];
  soft_skills: string[];
  projects: Project[];
  certifications: Certification[];
  experience_years: number;
  experience_summary: string;
  career_interests: string[];
  target_role: string | null;
  current_location: string;
  preferred_locations: string[];
  willing_to_relocate: boolean;
  work_mode: WorkMode;
  expected_salary_lpa: number | null;
  min_salary_lpa: number | null;
  learning_language: LangCode;
  app_language: LangCode;
  completeness: number;
}
export type ProfileUpdate = Partial<Omit<Profile, 'completeness'>>;

// Reference data
export interface SkillRef {
  name: string;
  category: string;
  assessable: boolean;
}
export interface RoleSkill {
  skill: string;
  weight: number;
  importance: 'core' | 'supporting';
}
export interface Role {
  id: string;
  title: string;
  description: string;
  skills: RoleSkill[];
}

// Assessments
export interface AvailableAssessment {
  skill: string;
  levels: Level[];
  question_count: number;
}
export type QuestionType = 'mcq' | 'code_output' | 'debugging' | 'scenario';
export interface Question {
  id: string;
  type: QuestionType;
  topic: string;
  prompt: string;
  code: string | null;
  options: string[] | null;
}
export interface AssessmentSession {
  attempt_id: string | number;
  skill: string;
  level: Level;
  questions: Question[];
}
export type Proficiency = 'not_verified' | Level;
export interface TopicBreakdown {
  topic: string;
  correct: number;
  total: number;
  percent: number;
}
export interface ReviewItem {
  question_id: string;
  prompt: string;
  correct: boolean;
  your_answer: string;
  correct_answer: string;
  explanation: string;
}
export interface AssessmentResult {
  attempt_id: string | number;
  skill: string;
  level: Level;
  score: number;
  correct: number;
  total: number;
  topic_breakdown: TopicBreakdown[];
  strong_topics: string[];
  weak_topics: string[];
  recommendations: string[];
  verified_score: number | null;
  proficiency: Proficiency;
  review: ReviewItem[];
}
export interface AssessmentHistoryItem {
  attempt_id: string | number;
  skill: string;
  level: Level;
  score: number;
  completed_at: string;
}
export interface VerifiedSkill {
  skill: string;
  self_reported_level: Level | null;
  verified_score: number | null;
  proficiency: Proficiency;
  attempts: number;
  last_assessed: string | null;
  strong_topics: string[];
  weak_topics: string[];
  status: 'verified' | 'self_reported' | 'assessed_only';
}

// Skill intelligence
export interface SkillEvidence {
  skill: string;
  reason: string;
  evidence: string;
}
export interface SkillIntelligence {
  strong: { skill: string; score: number; reason: string }[];
  weak: { skill: string; score: number; reason: string; weak_topics: string[] }[];
  missing: { skill: string; required_by: string[]; demand_count: number }[];
  emerging: SkillEvidence[];
  declining: SkillEvidence[];
  outdated: { skill: string; issue: string; recommendation: string; evidence: string; source: string }[];
  unverified: { skill: string; self_reported_level: Level | null }[];
  targeted_practice: string[];
  notice: string;
}

// Market
export interface MarketReport {
  data_source: {
    label: string;
    is_demo: boolean;
    vacancies_analyzed: number;
    as_of: string;
    scope: string;
  };
  top_skills: {
    skill: string;
    demand_count: number;
    share_percent: number;
    mandatory_count: number;
    preferred_count: number;
  }[];
  role_demand: { role_id: string; title: string; vacancies: number }[];
  emerging: SkillEvidence[];
  stable: string[];
  declining: SkillEvidence[];
  notes: string[];
}

// Careers
export type CareerComponentKey = 'skill_match' | 'interest' | 'market_demand' | 'location' | 'salary' | 'experience';
export type CareerLabel = 'Highly Recommended' | 'Recommended' | 'Potential Career' | 'Requires Skill Development';
export interface CareerRecommendation {
  role_id: string;
  title: string;
  score: number;
  label: CareerLabel;
  components: Record<CareerComponentKey, number>;
  weights: Record<CareerComponentKey, number>;
  matching_skills: { skill: string; score: number }[];
  improve_skills: { skill: string; score: number; target: number }[];
  missing_skills: string[];
  demand_level: 'high' | 'medium' | 'low';
  vacancies: number;
  salary_range: null | { min_lpa: number; max_lpa: number; source: string };
  location_fit: string;
  explanation: string;
  learning_path: string[];
  is_target: boolean;
}

// Jobs
export interface Salary {
  min_lpa: number | null;
  max_lpa: number | null;
  disclosed: boolean;
  label: string;
}
export interface JobSummary {
  id: string | number;
  company: string;
  title: string;
  location: string;
  work_mode: WorkMode;
  salary: Salary;
  experience_min_years: number;
  posted_date: string;
  last_verified_date?: string | null;
  deadline: string | null;
  apply_url: string;
  source: string;
  is_demo: boolean;
  verification_status?: string;
  mandatory_skills: string[];
  preferred_skills: string[];
  matching_skills: string[];
  missing_skills: string[];
  score: number;
  saved: boolean;
}
export type JobComponentKey = 'mandatory' | 'preferred' | 'experience' | 'education' | 'location' | 'salary';
export type SalaryFitStatus =
  | 'meets'
  | 'overlap'
  | 'below_expectation'
  | 'below_minimum'
  | 'not_disclosed'
  | 'no_preference';
export type LocationFitStatus = 'match' | 'remote' | 'relocation' | 'mismatch' | 'no_preference';
export interface JobMatch {
  score: number;
  components: Record<JobComponentKey, number>;
  weights: Record<JobComponentKey, number>;
  strong_matches: { skill: string; score: number }[];
  partial_matches: { skill: string; score: number; target: number }[];
  missing_mandatory: string[];
  missing_preferred: string[];
  not_assessed: string[];
  qualification_gaps: string[];
  salary_fit: { status: SalaryFitStatus; message: string };
  location_fit: { status: LocationFitStatus; message: string };
  explanation: string;
}
export interface JobDetail extends JobSummary {
  description: string;
  education: string;
  match: JobMatch;
  recommended_courses: CourseGroup[];
}
export interface JobQuery {
  q?: string;
  company?: string;
  location?: string;
  work_mode?: string;
  min_salary?: string;
  max_experience?: string;
  min_score?: string;
  sort?: 'score' | 'date' | 'salary';
  page?: number;
  page_size?: number;
}
export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  availability_note?: string | null;
}
export interface ExtractedRequirements {
  mandatory_skills: string[];
  preferred_skills: string[];
  experience_years: number | null;
  education: string | null;
  location?: string;
  work_mode?: WorkMode | null;
  salary_min_lpa?: number | null;
  salary_max_lpa?: number | null;
}
export interface JobCreate {
  company: string;
  title: string;
  description: string;
  mandatory_skills?: string[];
  preferred_skills?: string[];
  location: string;
  work_mode: WorkMode;
  salary_min_lpa?: number | null;
  salary_max_lpa?: number | null;
  experience_min_years: number;
  education: string;
  posted_date: string;
  deadline?: string | null;
  apply_url: string;
  source: string;
}
export type ApplicationStatus = 'saved' | 'applied' | 'interviewing' | 'offer' | 'rejected';
export interface Application {
  id: string | number;
  job: JobSummary;
  status: ApplicationStatus;
  notes: string;
  updated_at: string;
}

// Courses
export interface Course {
  id: string | number;
  title: string;
  platform: string;
  provider: string;
  url: string | null;
  language: string;
  audio_languages: string[];
  subtitle_languages: string[];
  difficulty: string;
  duration_hours: number | null;
  price: { is_free: boolean; label: string };
  rating: null | { value: number; source: string };
  skills: string[];
  outcomes: string[];
  verification: string;
  is_verified?: boolean;
}
export interface CourseGroup {
  skill: string;
  reason: string;
  courses: Course[];
}
export interface CourseQuery {
  skill?: string;
  platform?: string;
  language?: string;
  audio_language?: string;
  subtitle_language?: string;
  price?: '' | 'free' | 'paid';
  difficulty?: string;
  max_hours?: string;
  min_rating?: string;
  verified_only?: boolean;
  q?: string;
  page?: number;
  page_size?: number;
}
export interface CourseEquivalents {
  course: Course;
  language: string;
  equivalents: {
    course: Course;
    overlap_percent: number;
    shared_skills: string[];
    shared_outcomes: string[];
    equivalence_status?: 'syllabus_verified' | 'potential_skill_overlap';
    verdict: string;
  }[];
}

// Roadmap
export type StepStatus = 'not_started' | 'in_progress' | 'completed';
export interface RoadmapStep {
  id: string | number;
  order: number;
  skill: string;
  priority: 'high' | 'medium' | 'low';
  reason: string;
  course: Course | null;
  estimated_hours: number;
  exercise: string;
  project: string;
  status: StepStatus;
  reassessment_required: boolean;
  current_score: number | null;
  target_score: number;
}
export interface Roadmap {
  target_role: { id: string; title: string } | null;
  generated_at: string;
  reason: string;
  progress_percent: number;
  steps: RoadmapStep[];
}

// Mentor
export interface MentorReply {
  reply: string;
  mode: LlmMode;
  intent: string;
  sources: string[];
}

// Orchestrator
export type AgentTrigger =
  | 'manual'
  | 'profile_updated'
  | 'assessment_completed'
  | 'goal_changed'
  | 'learning_completed'
  | 'job_added';
export interface AgentTraceItem {
  order?: number;
  agent: string;
  status: 'ok' | 'skipped' | 'error';
  duration_ms: number;
  task_performed?: string;
  input_summary?: string;
  output_summary?: string;
  summary: string;
  decisions: string[];
}
export interface OrchestratorResult {
  run_id: string | number;
  created_at: string;
  trigger: AgentTrigger;
  llm_mode: LlmMode;
  trace: AgentTraceItem[];
  skill_intelligence: SkillIntelligence;
  market: MarketReport;
  careers: CareerRecommendation[];
  top_jobs: JobSummary[];
  recommended_courses: CourseGroup[];
  roadmap: Roadmap;
  mentor_brief: string;
}

// Dashboard
export interface Dashboard {
  profile_completeness: number;
  llm_mode: LlmMode;
  verified_skills: VerifiedSkill[];
  strongest: SkillIntelligence['strong'];
  weakest: SkillIntelligence['weak'];
  missing_skills: string[];
  outdated_alerts: SkillIntelligence['outdated'];
  emerging_skills: SkillEvidence[];
  top_careers: CareerRecommendation[];
  top_jobs: JobSummary[];
  salary_summary: {
    expected_lpa: number | null;
    min_lpa: number | null;
    jobs_meeting_minimum: number;
    jobs_with_disclosed_salary: number;
  };
  recommended_courses: Course[];
  roadmap_progress: number;
  assessment_history: AssessmentHistoryItem[];
  readiness_trend: { date: string; readiness: number }[];
  target_role: { id: string; title: string } | null;
  agent_trace: AgentTraceItem[];
}
