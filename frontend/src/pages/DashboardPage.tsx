import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useTranslation } from 'react-i18next';
import { api } from '../api/client';
import { errorMessage } from '../lib/errors';
import { Badge, Button, Card, ErrorState, PageHeader, ProgressBar, Spinner } from '../components/ui';

export default function DashboardPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboard'],
    queryFn: api.dashboard,
  });

  const refreshAgents = useMutation({
    mutationFn: () => api.runAgents('manual'),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['dashboard'] }),
  });

  if (isLoading) return <Spinner label={t('common.loading')} />;
  if (error || !data) return <ErrorState message={errorMessage(error, t)} onRetry={() => void refetch()} />;

  const verifiedOnly = data.verified_skills.filter((s) => s.verified_score !== null);

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('dashboard.title')}
        subtitle={
          data.target_role ? `Target Career: ${data.target_role.title}` : 'Set your target career and verify your skills.'
        }
        actions={
          <>
            <Badge tone={data.llm_mode === 'gemini' ? 'emerald' : 'amber'}>
              {data.llm_mode === 'gemini' ? t('common.geminiMode') : t('common.deterministicMode')}
            </Badge>
            <Button size="sm" onClick={() => refreshAgents.mutate()} disabled={refreshAgents.isPending}>
              {refreshAgents.isPending ? t('common.loading') : t('dashboard.runAgents')}
            </Button>
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{t('dashboard.completeness')}</p>
          <p className="mt-2 text-2xl font-bold">{data.profile_completeness}%</p>
          <div className="mt-3">
            <ProgressBar value={data.profile_completeness} />
          </div>
          <Link to="/profile" className="mt-3 inline-block text-xs font-semibold text-indigo-600 dark:text-indigo-400">
            Edit Profile →
          </Link>
        </Card>

        <Card>
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{t('dashboard.verifiedSkills')}</p>
          <p className="mt-2 text-2xl font-bold">
            {verifiedOnly.length} / {data.verified_skills.length}
          </p>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">Verified through assessments</p>
          <Link to="/assessments" className="mt-3 inline-block text-xs font-semibold text-indigo-600 dark:text-indigo-400">
            Take Assessment →
          </Link>
        </Card>

        <Card>
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{t('dashboard.roadmapProgress')}</p>
          <p className="mt-2 text-2xl font-bold">{data.roadmap_progress}%</p>
          <div className="mt-3">
            <ProgressBar value={data.roadmap_progress} />
          </div>
          <Link to="/roadmap" className="mt-3 inline-block text-xs font-semibold text-indigo-600 dark:text-indigo-400">
            Open Roadmap →
          </Link>
        </Card>

        <Card>
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{t('dashboard.salaryOverview')}</p>
          <p className="mt-2 text-2xl font-bold">
            {data.salary_summary.jobs_meeting_minimum} / {data.salary_summary.jobs_with_disclosed_salary}
          </p>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
            Top matches meeting {data.salary_summary.min_lpa ? `₹${data.salary_summary.min_lpa} LPA min` : 'disclosed ranges'}
          </p>
        </Card>
      </div>

      {verifiedOnly.length > 0 && (
        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold">Verified Skill Proficiency Overview</h2>
            <Link to="/analytics" className="text-xs font-semibold text-indigo-600 dark:text-indigo-400">
              Full Analytics →
            </Link>
          </div>
          <div className="h-52 w-full" aria-hidden="true">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={verifiedOnly.map((s) => ({ skill: s.skill, score: s.verified_score ?? 0 }))}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                <XAxis dataKey="skill" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Bar dataKey="score" fill="#4f46e5" radius={[4, 4, 0, 0]} name="Verified Score (%)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <details className="text-xs">
            <summary className="cursor-pointer font-semibold text-indigo-600 dark:text-indigo-400">
              Accessible Score Breakdown
            </summary>
            <ul className="mt-2 flex flex-wrap gap-3">
              {verifiedOnly.map((s) => (
                <li key={s.skill}>
                  {s.skill}: <strong>{s.verified_score}%</strong>
                </li>
              ))}
            </ul>
          </details>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold">{t('dashboard.topCareers')}</h2>
            <Link to="/careers" className="text-xs font-semibold text-indigo-600 dark:text-indigo-400">
              View All →
            </Link>
          </div>
          <div className="space-y-2.5">
            {data.top_careers.map((c) => (
              <div key={c.role_id} className="rounded-lg border border-slate-200 dark:border-slate-800 p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">{c.title}</span>
                  <Badge tone={c.score >= 78 ? 'emerald' : c.score >= 60 ? 'indigo' : 'amber'}>
                    {c.score}% · {c.label}
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                  Missing: {c.missing_skills.length ? c.missing_skills.join(', ') : 'None'}
                </p>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">{t('common.compatibilityNote')}</p>
        </Card>

        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold">{t('dashboard.topJobs')}</h2>
            <Link to="/jobs" className="text-xs font-semibold text-indigo-600 dark:text-indigo-400">
              Browse Jobs →
            </Link>
          </div>
          <div className="space-y-2.5">
            {data.top_jobs.map((j) => (
              <Link
                key={j.id}
                to={`/jobs/${j.id}`}
                className="block rounded-lg border border-slate-200 dark:border-slate-800 p-3 hover:border-indigo-500"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">
                    {j.title} — {j.company}
                  </span>
                  <Badge tone="indigo">{j.score}% match</Badge>
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
                  <span>{j.location} ({j.work_mode})</span>
                  <span>·</span>
                  <span>{j.salary.label}</span>
                  {j.is_demo && <Badge tone="amber">{t('common.demoData')}</Badge>}
                </div>
              </Link>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="space-y-3">
          <h2 className="text-base font-semibold">Skill Signals & Alerts</h2>
          <div className="space-y-2 text-sm">
            <p>
              <strong>Strongest:</strong>{' '}
              {data.strongest.length ? data.strongest.map((s) => `${s.skill} (${s.score}%)`).join(', ') : 'Complete an assessment'}
            </p>
            <p>
              <strong>Weakest:</strong>{' '}
              {data.weakest.length ? data.weakest.map((s) => `${s.skill} (${s.score}%)`).join(', ') : 'None flagged'}
            </p>
            <p>
              <strong>Missing for target/interests:</strong>{' '}
              {data.missing_skills.length ? data.missing_skills.join(', ') : 'None'}
            </p>
            {data.outdated_alerts.length > 0 && (
              <div className="rounded-lg bg-amber-50 dark:bg-amber-950/40 p-3 text-xs text-amber-900 dark:text-amber-200">
                <strong>{t('dashboard.outdatedAlerts')}:</strong>{' '}
                {data.outdated_alerts.map((a) => `${a.skill}: ${a.recommendation}`).join(' | ')}
              </div>
            )}
          </div>
        </Card>

        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold">Multi-Agent Orchestrator Trace</h2>
            <Link to="/settings" className="text-xs font-semibold text-indigo-600 dark:text-indigo-400">
              Details →
            </Link>
          </div>
          <ol className="space-y-2 text-xs">
            {data.agent_trace.map((tr, idx) => (
              <li key={`${tr.agent}-${idx}`} className="rounded-lg bg-slate-50 dark:bg-slate-800/60 p-2.5 space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold">
                    #{tr.order ?? idx + 1} · {tr.agent}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <Badge tone={tr.status === 'ok' ? 'emerald' : tr.status === 'error' ? 'rose' : 'amber'}>
                      {tr.status}
                    </Badge>
                    <span className="text-[11px] text-slate-500">{tr.duration_ms}ms</span>
                  </div>
                </div>
                {tr.input_summary && (
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">
                    <strong>Input:</strong> {tr.input_summary}
                  </p>
                )}
                <p className="text-slate-700 dark:text-slate-300">
                  <strong>Output:</strong> {tr.output_summary ?? tr.summary}
                </p>
                {tr.decisions && tr.decisions.length > 0 && (
                  <p className="text-[11px] text-indigo-700 dark:text-indigo-300">
                    <strong>Decisions:</strong> {tr.decisions.slice(0, 2).join(' · ')}
                  </p>
                )}
              </li>
            ))}
          </ol>
        </Card>
      </div>
    </div>
  );
}
