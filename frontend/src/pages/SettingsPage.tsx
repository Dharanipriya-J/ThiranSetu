import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { api } from '../api/client';
import type { LangCode } from '../api/types';
import { useAuth } from '../hooks/useAuth';
import { useTheme } from '../hooks/useTheme';
import { LANGUAGES, changeAppLanguage } from '../i18n';
import { errorMessage } from '../lib/errors';
import { Badge, Button, Card, ErrorState, PageHeader, Select, Spinner } from '../components/ui';

export default function SettingsPage() {
  const { t, i18n } = useTranslation();
  const { logout } = useAuth();
  const { theme, toggle: toggleTheme } = useTheme();
  const qc = useQueryClient();

  const profileQ = useQuery({ queryKey: ['profile'], queryFn: api.getProfile });
  const agentsQ = useQuery({ queryKey: ['agents-latest'], queryFn: api.latestAgents });

  const learnLangMut = useMutation({
    mutationFn: (lang: LangCode) => api.updateProfile({ learning_language: lang }),
    onSuccess: (updated) => {
      qc.setQueryData(['profile'], updated);
      void qc.invalidateQueries({ queryKey: ['recommended-courses'] });
    },
  });

  const runAgentsMut = useMutation({
    mutationFn: () => api.runAgents('manual'),
    onSuccess: (res) => {
      qc.setQueryData(['agents-latest'], res);
      void qc.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  if (agentsQ.isLoading || profileQ.isLoading) return <Spinner label={t('common.loading')} />;
  if (agentsQ.error) return <ErrorState message={errorMessage(agentsQ.error, t)} />;

  const latest = agentsQ.data;

  return (
    <div className="space-y-6">
      <PageHeader title={t('nav.settings')} subtitle="Language preferences, theme, and multi-agent orchestrator trace." />

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="space-y-4">
          <h2 className="text-base font-semibold">Language & Appearance</h2>
          <Select
            label={t('common.language')}
            value={i18n.language}
            onChange={(e) => void changeAppLanguage(e.target.value as LangCode)}
          >
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.native} ({l.english})
              </option>
            ))}
          </Select>

          <Select
            label="Preferred Course Learning Language (Separate from UI)"
            value={profileQ.data?.learning_language ?? 'en'}
            onChange={(e) => learnLangMut.mutate(e.target.value as LangCode)}
          >
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.native} ({l.english})
              </option>
            ))}
          </Select>

          <div className="flex items-center justify-between pt-2">
            <span className="text-sm font-medium">Theme ({theme})</span>
            <Button size="sm" variant="secondary" onClick={toggleTheme}>
              {t('common.themeToggle')}
            </Button>
          </div>
          <div className="pt-2">
            <Button size="sm" variant="danger" onClick={() => void logout()}>
              {t('common.logout')}
            </Button>
          </div>
        </Card>

        {latest && (
          <Card className="space-y-3">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-base font-semibold">Multi-Agent Collaboration Trace</h2>
              <Button size="sm" onClick={() => runAgentsMut.mutate()} disabled={runAgentsMut.isPending}>
                {runAgentsMut.isPending ? t('common.loading') : 'Run Orchestrator'}
              </Button>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Trigger: <strong>{latest.trigger}</strong> · Mode:{' '}
              <Badge tone={latest.llm_mode === 'gemini' ? 'emerald' : 'amber'}>{latest.llm_mode}</Badge>
            </p>
            <div className="space-y-2">
              {latest.trace.map((tr) => (
                <div key={tr.agent} className="rounded-lg border border-slate-200 dark:border-slate-800 p-2.5 text-xs space-y-1">
                  <div className="flex justify-between font-semibold">
                    <span>{tr.agent}</span>
                    <span>
                      {tr.status} · {tr.duration_ms}ms
                    </span>
                  </div>
                  <p>{tr.summary}</p>
                  {tr.decisions.length > 0 && (
                    <p className="text-slate-500">Decisions: {tr.decisions.join(' | ')}</p>
                  )}
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
