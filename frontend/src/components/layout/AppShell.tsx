import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../hooks/useAuth';
import { useTheme } from '../../hooks/useTheme';
import { LANGUAGES, changeAppLanguage } from '../../i18n';
import type { LangCode } from '../../api/types';
import { Button } from '../ui';
import { MoonIcon, NavIcon, SunIcon } from '../ui/Icons';

const NAV_ITEMS = [
  { to: '/dashboard', key: 'nav.dashboard' },
  { to: '/profile', key: 'nav.profile' },
  { to: '/assessments', key: 'nav.assessments' },
  { to: '/intelligence', key: 'nav.intelligence' },
  { to: '/market', key: 'nav.market' },
  { to: '/careers', key: 'nav.careers' },
  { to: '/jobs', key: 'nav.jobs' },
  { to: '/courses', key: 'nav.courses' },
  { to: '/roadmap', key: 'nav.roadmap' },
  { to: '/mentor', key: 'nav.mentor' },
  { to: '/analytics', key: 'nav.analytics' },
  { to: '/settings', key: 'nav.settings' },
];

export function AppShell() {
  const { t, i18n } = useTranslation();
  const { user, logout } = useAuth();
  const { theme, toggle: toggleTheme } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (!mobileOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMobileOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [mobileOpen]);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-lg focus:bg-indigo-600 focus:px-4 focus:py-2 focus:text-white"
      >
        {t('common.skipToContent')}
      </a>

      <header className="sticky top-0 z-30 border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileOpen((v) => !v)}
              aria-label="Toggle navigation menu"
              aria-expanded={mobileOpen}
              className="lg:hidden rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm min-h-[44px]"
            >
              Menu
            </button>
            <Link to="/dashboard" className="flex items-center gap-2">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
                TS
              </span>
              <span className="text-lg font-bold tracking-tight">{t('brand')}</span>
            </Link>
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="topbar-lang" className="sr-only">
              {t('common.language')}
            </label>
            <select
              id="topbar-lang"
              aria-label={t('common.language')}
              value={i18n.language}
              onChange={(e) => void changeAppLanguage(e.target.value as LangCode)}
              className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-2.5 py-1.5 text-sm min-h-[38px]"
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.native} ({l.english})
                </option>
              ))}
            </select>

            <Button variant="secondary" size="sm" onClick={toggleTheme} aria-label={t('common.themeToggle')}>
              {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
              <span className="hidden sm:inline">{theme === 'dark' ? 'Light' : 'Dark'}</span>
            </Button>

            {user && (
              <span className="hidden sm:inline text-xs font-medium text-slate-600 dark:text-slate-300 px-2">
                {user.full_name}
              </span>
            )}
            <Button variant="ghost" size="sm" onClick={() => void logout()}>
              {t('common.logout')}
            </Button>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-7xl">
        <nav
          aria-label="Primary"
          className={`${
            mobileOpen ? 'fixed inset-y-0 left-0 z-40 w-64 bg-white dark:bg-slate-900 p-4 shadow-xl' : 'hidden'
          } lg:block lg:w-60 lg:shrink-0 lg:border-r lg:border-slate-200 dark:lg:border-slate-800 lg:p-4`}
        >
          {mobileOpen && (
            <div className="mb-3 flex justify-end lg:hidden">
              <Button variant="ghost" size="sm" onClick={() => setMobileOpen(false)}>
                Close
              </Button>
            </div>
          )}
          <ul className="space-y-1">
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  onClick={() => setMobileOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors min-h-[40px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ${
                      isActive
                        ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-200'
                        : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                    }`
                  }
                >
                  <NavIcon route={item.to} />
                  <span>{t(item.key)}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <main id="main-content" className="min-w-0 flex-1 p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
