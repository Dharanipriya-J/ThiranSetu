import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../hooks/useAuth';
import { useTheme } from '../hooks/useTheme';
import { LANGUAGES, changeAppLanguage } from '../i18n';
import type { LangCode } from '../api/types';
import { Badge, Button, Card } from '../components/ui';
import { MoonIcon, SunIcon } from '../components/ui/Icons';

const AGENTS = [
  { name: '1. Skill Assessment Agent', desc: 'Tests claimed skills with MCQs, code-output, debugging, and scenario tasks.' },
  { name: '2. Skill Intelligence Agent', desc: 'Separates verified scores from self-reports and flags weak or outdated tech.' },
  { name: '3. Market Intelligence Agent', desc: 'Analyses active company vacancies for mandatory & emerging skill demand.' },
  { name: '4. Career Matching Agent', desc: 'Ranks 9+ careers using 6 transparent weights across skills, location & salary.' },
  { name: '5. Job Requirement Agent', desc: 'Extracts company mandatory/preferred skills and computes exact job gaps.' },
  { name: '6. Course Discovery Agent', desc: 'Finds gap-targeted courses with multilingual syllabus equivalence.' },
  { name: '7. AI Career Mentor Agent', desc: 'Answers career, salary, and company questions from your real profile state.' },
];

export default function LandingPage() {
  const { t, i18n } = useTranslation();
  const { isAuthenticated } = useAuth();
  const { theme, toggle: toggleTheme } = useTheme();

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <header className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-2.5">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
              TS
            </span>
            <div>
              <span className="text-lg font-bold">{t('brand')}</span>
              <p className="text-xs text-slate-500 dark:text-slate-400">{t('tagline')}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <select
              aria-label={t('common.language')}
              value={i18n.language}
              onChange={(e) => void changeAppLanguage(e.target.value as LangCode)}
              className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-2.5 py-1.5 text-sm"
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.native}
                </option>
              ))}
            </select>
            <Button variant="secondary" size="sm" onClick={toggleTheme} aria-label={t('common.themeToggle')}>
              {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
              <span className="hidden sm:inline">{theme === 'dark' ? 'Light' : 'Dark'}</span>
            </Button>
            {isAuthenticated ? (
              <Link to="/dashboard">
                <Button size="sm">{t('nav.dashboard')}</Button>
              </Link>
            ) : (
              <Link to="/login">
                <Button variant="secondary" size="sm">{t('landing.ctaLogin')}</Button>
              </Link>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-12 space-y-14">
        <section className="rounded-2xl bg-gradient-to-br from-indigo-600 to-teal-700 p-8 sm:p-12 text-white shadow-lg">
          <Badge tone="neutral" className="bg-white/20 text-white mb-4">
            LangGraph Multi-Agent Platform · 8 Indian Languages
          </Badge>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight max-w-3xl">
            {t('landing.heroTitle')}
          </h1>
          <p className="mt-4 max-w-2xl text-base text-indigo-100">{t('landing.heroSubtitle')}</p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link to={isAuthenticated ? '/dashboard' : '/register'}>
              <Button className="bg-white text-indigo-700 hover:bg-indigo-50">{t('landing.ctaStart')}</Button>
            </Link>
            <Link to="/login">
              <Button variant="secondary" className="border-white/40 bg-transparent text-white hover:bg-white/10">
                {t('landing.ctaLogin')}
              </Button>
            </Link>
          </div>
        </section>

        <section>
          <h2 className="text-2xl font-bold mb-6">{t('landing.agentsTitle')}</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {AGENTS.map((a) => (
              <Card key={a.name}>
                <h3 className="font-semibold text-indigo-600 dark:text-indigo-400">{a.name}</h3>
                <p className="mt-1.5 text-sm text-slate-600 dark:text-slate-400">{a.desc}</p>
              </Card>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
