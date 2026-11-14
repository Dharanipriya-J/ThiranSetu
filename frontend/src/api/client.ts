import type {
  AgentTrigger,
  Application,
  ApplicationStatus,
  AssessmentHistoryItem,
  AssessmentResult,
  AssessmentSession,
  AvailableAssessment,
  CareerRecommendation,
  Course,
  CourseEquivalents,
  CourseGroup,
  CourseQuery,
  Dashboard,
  ExtractedRequirements,
  Health,
  JobCreate,
  JobDetail,
  JobQuery,
  JobSummary,
  LangCode,
  Level,
  LoginRequest,
  MarketReport,
  MentorReply,
  OrchestratorResult,
  Paginated,
  Profile,
  ProfileUpdate,
  RegisterRequest,
  Roadmap,
  Role,
  SkillIntelligence,
  SkillRef,
  StepStatus,
  TokenResponse,
  User,
  VerifiedSkill,
} from './types';

let memoryToken: string | null = null;

export type ApiErrorKind = 'unauthorized' | 'validation' | 'rate_limit' | 'network' | 'server' | 'not_found' | 'http';

/** Error thrown by every API call. `kind` maps to an i18n key under `errors.*`. */
export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number;
  /** Field name → message, populated for 422 responses. */
  readonly fieldErrors: Record<string, string>;
  /** Seconds, from the Retry-After header on 429. */
  readonly retryAfter: number | null;
  /** Server-provided `detail` string, when present. */
  readonly detail: string | null;

  constructor(
    kind: ApiErrorKind,
    status: number,
    message: string,
    opts: { fieldErrors?: Record<string, string>; retryAfter?: number | null; detail?: string | null } = {},
  ) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.status = status;
    this.fieldErrors = opts.fieldErrors ?? {};
    this.retryAfter = opts.retryAfter ?? null;
    this.detail = opts.detail ?? null;
  }
}

/** Returns the short-lived access token held strictly in memory (never localStorage). */
export function getToken(): string | null {
  return memoryToken;
}
export function setToken(token: string | null): void {
  memoryToken = token;
}

function readCsrfCookie(): string | null {
  try {
    const match = document.cookie.match(/(?:^|;\s*)ts_csrf=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : null;
  } catch {
    return null;
  }
}

type UnauthorizedHandler = () => void;
let onUnauthorized: UnauthorizedHandler = () => {
  window.location.assign('/login');
};
/** Lets the auth provider replace the default hard redirect with router navigation. */
export function setUnauthorizedHandler(handler: UnauthorizedHandler): void {
  onUnauthorized = handler;
}

interface FastApiValidationItem {
  loc?: (string | number)[];
  msg?: string;
}

function parseFieldErrors(detail: unknown): Record<string, string> {
  const out: Record<string, string> = {};
  if (Array.isArray(detail)) {
    for (const item of detail as FastApiValidationItem[]) {
      const loc = (item.loc ?? []).filter((p) => p !== 'body' && p !== 'query');
      const key = loc.length ? loc.join('.') : '_';
      if (!out[key]) out[key] = item.msg ?? 'Invalid value';
    }
  }
  return out;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  query?: Record<string, string | number | boolean | null | undefined>;
  /** Do not treat 401 as an expired session (e.g. bad login credentials). */
  skipAuthRedirect?: boolean;
}

export function buildQuery(query?: RequestOptions['query']): string {
  if (!query) return '';
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v === undefined || v === null || v === '') continue;
    params.set(k, String(v));
  }
  const s = params.toString();
  return s ? `?${s}` : '';
}

let refreshInFlight: Promise<TokenResponse | null> | null = null;

async function tryRefreshAccess(): Promise<TokenResponse | null> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    try {
      const headers: Record<string, string> = { Accept: 'application/json' };
      const csrf = readCsrfCookie();
      if (csrf) headers['X-CSRF-Token'] = csrf;
      const res = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers,
        credentials: 'include',
      });
      if (!res.ok) return null;
      const payload = (await res.json()) as TokenResponse;
      setToken(payload.access_token);
      return payload;
    } catch {
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

export async function request<T>(path: string, opts: RequestOptions = {}, _retried = false): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const csrf = readCsrfCookie();
  if (csrf && path.startsWith('/api/auth/')) headers['X-CSRF-Token'] = csrf;
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json';

  let res: Response;
  try {
    res = await fetch(`${path}${buildQuery(opts.query)}`, {
      method: opts.method ?? 'GET',
      headers,
      credentials: 'include',
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    });
  } catch {
    throw new ApiError('network', 0, 'Network error');
  }

  if (res.status === 204) return undefined as T;

  let data: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }

  if (res.ok) return data as T;

  const rawDetail = (data as { detail?: unknown } | null)?.detail;
  const detail = typeof rawDetail === 'string' ? rawDetail : null;

  if (res.status === 401) {
    if (!_retried && !opts.skipAuthRedirect && path !== '/api/auth/refresh') {
      const refreshed = await tryRefreshAccess();
      if (refreshed) return request<T>(path, opts, true);
    }
    if (!opts.skipAuthRedirect) {
      setToken(null);
      onUnauthorized();
    }
    throw new ApiError('unauthorized', 401, detail ?? 'Unauthorized', { detail });
  }
  if (res.status === 422) {
    const fieldErrors = parseFieldErrors(rawDetail);
    throw new ApiError('validation', 422, detail ?? 'Validation error', { fieldErrors, detail });
  }
  if (res.status === 429) {
    const ra = Number(res.headers.get('Retry-After'));
    throw new ApiError('rate_limit', 429, 'Too many requests', {
      retryAfter: Number.isFinite(ra) && ra > 0 ? ra : null,
      detail,
    });
  }
  if (res.status === 404) throw new ApiError('not_found', 404, detail ?? 'Not found', { detail });
  if (res.status >= 500) throw new ApiError('server', res.status, 'Server error', { detail });
  throw new ApiError('http', res.status, detail ?? `Request failed (${res.status})`, { detail });
}

const json = (method: string, body?: unknown) => ({ method, body });

export const api = {
  health: () => request<Health>('/api/health'),

  // Auth
  register: (body: RegisterRequest) =>
    request<TokenResponse>('/api/auth/register', { ...json('POST', body), skipAuthRedirect: true }),
  login: (body: LoginRequest) =>
    request<TokenResponse>('/api/auth/login', { ...json('POST', body), skipAuthRedirect: true }),
  refresh: () =>
    request<TokenResponse>('/api/auth/refresh', { method: 'POST', skipAuthRedirect: true }),
  logout: () => request<void>('/api/auth/logout', { method: 'POST', skipAuthRedirect: true }),
  me: () => request<User>('/api/auth/me'),

  // Profile & reference data
  getProfile: () => request<Profile>('/api/profile'),
  updateProfile: (body: ProfileUpdate) => request<Profile>('/api/profile', json('PUT', body)),
  skills: () => request<SkillRef[]>('/api/skills'),
  roles: () => request<Role[]>('/api/roles'),

  // Assessments
  availableAssessments: () => request<AvailableAssessment[]>('/api/assessments/available'),
  startAssessment: (skill: string, level: Level) =>
    request<AssessmentSession>('/api/assessments/start', json('POST', { skill, level })),
  submitAssessment: (attemptId: string | number, answers: Record<string, string>) =>
    request<AssessmentResult>(`/api/assessments/${encodeURIComponent(String(attemptId))}/submit`, json('POST', { answers })),
  assessmentHistory: () => request<AssessmentHistoryItem[]>('/api/assessments/history'),
  verifiedSkills: () => request<VerifiedSkill[]>('/api/skills/verified'),

  // Agents
  runAgents: (trigger: AgentTrigger) => request<OrchestratorResult>('/api/agents/run', json('POST', { trigger })),
  latestAgents: () => request<OrchestratorResult>('/api/agents/latest'),

  // Insights
  intelligence: () => request<SkillIntelligence>('/api/intelligence'),
  market: () => request<MarketReport>('/api/market'),
  careers: () => request<CareerRecommendation[]>('/api/careers'),
  setTargetCareer: (role_id: string) => request<Roadmap>('/api/careers/target', json('PUT', { role_id })),
  dashboard: () => request<Dashboard>('/api/dashboard'),

  // Jobs
  jobs: (q: JobQuery) => request<Paginated<JobSummary>>('/api/jobs', { query: { ...q } }),
  job: (id: string | number) => request<JobDetail>(`/api/jobs/${encodeURIComponent(String(id))}`),
  extractJob: (description: string) => request<ExtractedRequirements>('/api/jobs/extract', json('POST', { description })),
  createJob: (body: JobCreate) => request<JobDetail>('/api/jobs', json('POST', body)),
  syncJobs: () => request<{ status: string; mode: string; added: number; message: string }>('/api/jobs/sync', { method: 'POST' }),
  applications: () => request<Application[]>('/api/applications'),
  saveJob: (job_id: string | number) => request<Application>('/api/applications', json('POST', { job_id, status: 'saved' })),
  updateApplication: (id: string | number, body: { status?: ApplicationStatus; notes?: string }) =>
    request<Application>(`/api/applications/${encodeURIComponent(String(id))}`, json('PATCH', body)),
  deleteApplication: (id: string | number) =>
    request<void>(`/api/applications/${encodeURIComponent(String(id))}`, { method: 'DELETE' }),

  // Courses
  courses: (q: CourseQuery) => request<Paginated<Course>>('/api/courses', { query: { ...q } }),
  recommendedCourses: () => request<CourseGroup[]>('/api/courses/recommended'),
  courseEquivalents: (id: string | number, language: string) =>
    request<CourseEquivalents>(`/api/courses/${encodeURIComponent(String(id))}/equivalents`, { query: { language } }),

  // Roadmap
  roadmap: () => request<Roadmap>('/api/roadmap'),
  regenerateRoadmap: () => request<Roadmap>('/api/roadmap/regenerate', { method: 'POST' }),
  updateStep: (stepId: string | number, status: StepStatus) =>
    request<Roadmap>(`/api/roadmap/steps/${encodeURIComponent(String(stepId))}`, json('PATCH', { status })),

  // Mentor
  mentorSuggestions: () => request<string[]>('/api/mentor/suggestions'),
  mentorChat: (message: string, language: LangCode) =>
    request<MentorReply>('/api/mentor/chat', json('POST', { message, language })),
};
