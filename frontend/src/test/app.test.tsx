import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axe from 'axe-core';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { I18nextProvider } from 'react-i18next';
import i18n, { changeAppLanguage } from '../i18n';
import en from '../i18n/locales/en.json';
import ta from '../i18n/locales/ta.json';
import hi from '../i18n/locales/hi.json';
import te from '../i18n/locales/te.json';
import kn from '../i18n/locales/kn.json';
import ml from '../i18n/locales/ml.json';
import bn from '../i18n/locales/bn.json';
import mr from '../i18n/locales/mr.json';
import { api, ApiError, getToken, setToken } from '../api/client';
import { AuthProvider } from '../hooks/useAuth';
import { ThemeProvider } from '../hooks/useTheme';
import { AppRoutes } from '../App';
import RegisterPage from '../pages/RegisterPage';
import MentorPage from '../pages/MentorPage';
import CoursesPage from '../pages/CoursesPage';
import DashboardPage from '../pages/DashboardPage';
import LandingPage from '../pages/LandingPage';
import { JobAddForm } from '../components/jobs/JobAddForm';

function flattenKeys(obj: Record<string, unknown>, prefix = ''): string[] {
  return Object.entries(obj).flatMap(([k, v]) => {
    const key = prefix ? `${prefix}.${k}` : k;
    return v && typeof v === 'object' && !Array.isArray(v) ? flattenKeys(v as Record<string, unknown>, key) : [key];
  });
}

function renderWithProviders(ui: React.ReactElement, initialEntries = ['/']) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ThemeProvider>
        <I18nextProvider i18n={i18n}>
          <MemoryRouter initialEntries={initialEntries}>
            <AuthProvider>{ui}</AuthProvider>
          </MemoryRouter>
        </I18nextProvider>
      </ThemeProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

describe('i18n parity & branding', () => {
  it('all 8 locale files share identical keys and keep ThiranSetu in English', () => {
    const expectedKeys = flattenKeys(en).sort();
    const locales = { ta, hi, te, kn, ml, bn, mr };
    for (const [code, data] of Object.entries(locales)) {
      expect(flattenKeys(data).sort(), `key mismatch in ${code}`).toEqual(expectedKeys);
      expect(data.brand, `brand must stay English in ${code}`).toBe('ThiranSetu');
    }
    expect(en.brand).toBe('ThiranSetu');
  });

  it('switches language and updates rendered text', async () => {
    await changeAppLanguage('ta');
    expect(i18n.language).toBe('ta');
    expect(i18n.t('nav.dashboard')).toBe(ta.nav.dashboard);
    await changeAppLanguage('en');
  });
});

describe('API client error handling', () => {
  it('maps 422, 429, and network failures to structured ApiError', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: [{ loc: ['body', 'password'], msg: 'too short' }] }), {
        status: 422,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    await expect(api.login({ email: 'a@b.com', password: '1' })).rejects.toMatchObject({
      kind: 'validation',
      status: 422,
      fieldErrors: { password: 'too short' },
    });

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Rate limited' }), {
        status: 429,
        headers: { 'Content-Type': 'application/json', 'Retry-After': '15' },
      }),
    );
    await expect(api.login({ email: 'a@b.com', password: '1' })).rejects.toMatchObject({
      kind: 'rate_limit',
      status: 429,
      retryAfter: 15,
    });

    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new TypeError('Failed to fetch'));
    try {
      await api.health();
      expect.fail('Expected ApiError');
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).kind).toBe('network');
    }
  });
});

describe('Auth, routing, and Mentor UI', () => {
  it('redirects unauthenticated users from /dashboard to /login', async () => {
    renderWithProviders(<AppRoutes />, ['/dashboard']);
    expect(await screen.findByRole('heading', { name: /sign in/i })).toBeInTheDocument();
  });

  it('validates registration password requirements client-side', async () => {
    const user = userEvent.setup();
    renderWithProviders(<RegisterPage />, ['/register']);
    await user.type(screen.getByLabelText(/full name/i), 'Aarav');
    await user.type(screen.getByLabelText(/email/i), 'aarav@example.com');
    await user.type(screen.getByLabelText(/password/i), 'short');
    await user.click(screen.getByRole('button', { name: /create account/i }));
    expect(await screen.findByText(/8\+ characters/i)).toBeInTheDocument();
  });

  it('mentor chat sends question and renders deterministic fallback badge', async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes('/api/mentor/suggestions')) {
        return new Response(JSON.stringify(['Which career suits me?']), { status: 200 });
      }
      if (url.includes('/api/mentor/chat')) {
        return new Response(
          JSON.stringify({
            reply: 'Data Analyst is your strongest match at 78%.',
            mode: 'deterministic',
            intent: 'career',
            sources: ['Verified Assessments', 'Career Rankings'],
          }),
          { status: 200 },
        );
      }
      return new Response('{}', { status: 404 });
    });

    renderWithProviders(<MentorPage />, ['/mentor']);
    const btn = await screen.findByRole('button', { name: 'Which career suits me?' });
    await user.click(btn);
    await waitFor(() => {
      expect(screen.getByText(/Data Analyst is your strongest match/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/Deterministic Fallback Mode/i)).toBeInTheDocument();
  });

  it('keeps access token strictly in memory and never writes ts_token to localStorage', () => {
    setToken('mem-only-token');
    expect(getToken()).toBe('mem-only-token');
    expect(localStorage.getItem('ts_token')).toBeNull();
    setToken(null);
  });

  it('JobAddForm extracts requirements and allows editing before saving', async () => {
    const user = userEvent.setup();
    const onCreated = vi.fn();
    let capturedBody: Record<string, unknown> = {};
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.includes('/api/jobs/extract')) {
        return new Response(
          JSON.stringify({
            mandatory_skills: ['Python'],
            preferred_skills: ['Docker'],
            experience_years: 1,
            education: 'B.Tech',
            location: 'Chennai',
            work_mode: 'hybrid',
            salary_min_lpa: 6,
            salary_max_lpa: 8,
          }),
          { status: 200 },
        );
      }
      if (url.endsWith('/api/jobs') && init?.method === 'POST') {
        capturedBody = JSON.parse(String(init.body));
        return new Response(JSON.stringify({ id: 99 }), { status: 201 });
      }
      return new Response('{}', { status: 404 });
    });

    renderWithProviders(<JobAddForm onCreated={onCreated} />);
    await user.type(screen.getByLabelText(/Company Name/i), 'Freshworks');
    await user.type(screen.getByLabelText(/Job Title/i), 'Data Engineer');
    await user.type(
      screen.getByLabelText(/Job Description/i),
      'Location: Chennai. Hybrid role. Mandatory: Python. Preferred: Docker. Salary: 6-8 LPA.',
    );
    await user.click(screen.getByRole('button', { name: /Preview Extracted Requirements/i }));
    const mandInput = await screen.findByLabelText(/Mandatory Skills/i);
    await waitFor(() => expect(mandInput).toHaveValue('Python'));
    await user.clear(mandInput);
    await user.type(mandInput, 'Python, SQL');
    await user.type(screen.getByLabelText(/Official Application URL/i), 'https://careers.freshworks.com/1');
    await user.click(screen.getByRole('button', { name: /Save & Match Vacancy/i }));

    await waitFor(() => expect(onCreated).toHaveBeenCalled());
    expect(capturedBody?.mandatory_skills).toEqual(['Python', 'SQL']);
  });

  it('DashboardPage renders structured Multi-Agent Orchestrator Trace', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          profile_completeness: 80,
          llm_mode: 'deterministic',
          verified_skills: [],
          strongest: [],
          weakest: [],
          missing_skills: [],
          outdated_alerts: [],
          emerging_skills: [],
          top_careers: [],
          top_jobs: [],
          salary_summary: { expected_lpa: 8, min_lpa: 5, jobs_meeting_minimum: 2, jobs_with_disclosed_salary: 3 },
          recommended_courses: [],
          roadmap_progress: 25,
          assessment_history: [],
          readiness_trend: [],
          target_role: null,
          agent_trace: [
            {
              order: 1,
              agent: 'Skill Assessment Agent',
              status: 'ok',
              duration_ms: 1.2,
              input_summary: 'trigger=manual, skills=2, jobs=10',
              output_summary: 'Evaluated 2 skills',
              summary: 'Evaluated 2 skills',
              decisions: ['Python: 85%'],
            },
          ],
        }),
        { status: 200 },
      ),
    );
    renderWithProviders(<DashboardPage />);
    expect(await screen.findByText(/#1 · Skill Assessment Agent/i)).toBeInTheDocument();
    expect(screen.getByText(/Evaluated 2 skills/i)).toBeInTheDocument();
  });

  it('CoursesPage displays availability_note when no courses match requested language', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes('/api/courses/recommended')) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      return new Response(
        JSON.stringify({
          items: [],
          total: 0,
          page: 1,
          page_size: 12,
          availability_note: 'No courses with primary teaching language matched; subtitles available.',
        }),
        { status: 200 },
      );
    });
    renderWithProviders(<CoursesPage />);
    expect(await screen.findByText(/subtitles available/i)).toBeInTheDocument();
  });

  it('passes automated axe-core accessibility checks on LandingPage and RegisterPage', async () => {
    const landing = renderWithProviders(<LandingPage />, ['/']);
    const landingResults = await axe.run(landing.container, { rules: { 'color-contrast': { enabled: false } } });
    expect(landingResults.violations).toEqual([]);
    landing.unmount();

    const reg = renderWithProviders(<RegisterPage />, ['/register']);
    const regResults = await axe.run(reg.container, { rules: { 'color-contrast': { enabled: false } } });
    expect(regResults.violations).toEqual([]);
  });
});
