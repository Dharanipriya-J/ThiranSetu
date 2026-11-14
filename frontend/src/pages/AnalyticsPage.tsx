import { useQuery } from '@tanstack/react-query';
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useTranslation } from 'react-i18next';
import { api } from '../api/client';
import { errorMessage } from '../lib/errors';
import { Card, ErrorState, PageHeader, ProgressBar, Spinner } from '../components/ui';

export default function AnalyticsPage() {
  const { t } = useTranslation();
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['dashboard'], queryFn: api.dashboard });

  if (isLoading) return <Spinner label={t('common.loading')} />;
  if (error || !data) return <ErrorState message={errorMessage(error, t)} onRetry={() => void refetch()} />;

  const verifiedChartData = data.verified_skills
    .filter((s) => s.verified_score !== null)
    .map((s) => ({ skill: s.skill, score: s.verified_score ?? 0 }));

  const trendData = data.readiness_trend.map((pt, i) => ({
    run: `#${i + 1}`,
    readiness: pt.readiness,
    date: new Date(pt.date).toLocaleDateString(),
  }));

  return (
    <div className="space-y-6">
      <PageHeader title={t('nav.analytics')} subtitle="Verified skill scores, career readiness trend, and roadmap progress." />

      <ProgressBar value={data.roadmap_progress} label="Roadmap Completion" />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="space-y-3">
          <h2 className="text-base font-semibold">Verified Skill Proficiency (%)</h2>
          {verifiedChartData.length === 0 ? (
            <p className="text-sm text-slate-600 dark:text-slate-400">Complete an assessment to plot verified scores.</p>
          ) : (
            <div className="h-64 w-full" aria-hidden="true">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={verifiedChartData}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
                  <XAxis dataKey="skill" tick={{ fontSize: 12 }} />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Bar dataKey="score" fill="#4f46e5" name="Verified Score (%)" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
          <details className="text-xs">
            <summary className="cursor-pointer font-semibold text-indigo-600 dark:text-indigo-400">
              Table Summary (Accessible Alternative)
            </summary>
            <ul className="mt-2 space-y-1">
              {verifiedChartData.map((d) => (
                <li key={d.skill}>
                  {d.skill}: {d.score}%
                </li>
              ))}
            </ul>
          </details>
        </Card>

        <Card className="space-y-3">
          <h2 className="text-base font-semibold">Career Readiness Trend Across Agent Runs</h2>
          <div className="h-64 w-full" aria-hidden="true">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
                <XAxis dataKey="run" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Line type="monotone" dataKey="readiness" stroke="#0d9488" strokeWidth={2} name="Top Career Alignment (%)" />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <details className="text-xs">
            <summary className="cursor-pointer font-semibold text-indigo-600 dark:text-indigo-400">
              Table Summary (Accessible Alternative)
            </summary>
            <ul className="mt-2 space-y-1">
              {trendData.map((d) => (
                <li key={d.run}>
                  Run {d.run} ({d.date}): {d.readiness}%
                </li>
              ))}
            </ul>
          </details>
        </Card>
      </div>
    </div>
  );
}
