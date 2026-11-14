import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../api/client';
import { errorMessage } from '../lib/errors';
import { Badge, Card, ErrorState, PageHeader, Spinner } from '../components/ui';

export default function IntelligencePage() {
  const { t } = useTranslation();
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['intelligence'], queryFn: api.intelligence });

  if (isLoading) return <Spinner label={t('common.loading')} />;
  if (error || !data) return <ErrorState message={errorMessage(error, t)} onRetry={() => void refetch()} />;

  return (
    <div className="space-y-6">
      <PageHeader title={t('nav.intelligence')} subtitle={data.notice} />

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="space-y-2">
          <h2 className="font-semibold text-emerald-700 dark:text-emerald-400">Strong Verified Skills</h2>
          {data.strong.length === 0 ? (
            <p className="text-sm text-slate-600 dark:text-slate-400">Complete assessments to verify strengths.</p>
          ) : (
            data.strong.map((s) => (
              <div key={s.skill} className="flex justify-between text-sm">
                <span>{s.skill}</span>
                <Badge tone="emerald">{s.score}%</Badge>
              </div>
            ))
          )}
        </Card>

        <Card className="space-y-2">
          <h2 className="font-semibold text-rose-700 dark:text-rose-400">Weak Skills Requiring Improvement</h2>
          {data.weak.length === 0 ? (
            <p className="text-sm text-slate-600 dark:text-slate-400">No weak verified skills flagged.</p>
          ) : (
            data.weak.map((w) => (
              <div key={w.skill} className="rounded-lg bg-rose-50 dark:bg-rose-950/30 p-2.5 text-xs">
                <div className="flex justify-between font-semibold">
                  <span>{w.skill}</span>
                  <span>{w.score}%</span>
                </div>
                <p className="mt-1">{w.reason}</p>
              </div>
            ))
          )}
        </Card>

        <Card className="space-y-2">
          <h2 className="font-semibold text-amber-700 dark:text-amber-400">Missing Skills for Target Roles</h2>
          {data.missing.map((m) => (
            <div key={m.skill} className="flex items-center justify-between text-sm">
              <span>
                <strong>{m.skill}</strong>{' '}
                <span className="text-xs text-slate-500">({m.required_by.join(', ')})</span>
              </span>
              <Badge tone="indigo">{m.demand_count} vacancies</Badge>
            </div>
          ))}
        </Card>

        <Card className="space-y-2">
          <h2 className="font-semibold">Unverified Self-Reported Skills</h2>
          {data.unverified.length === 0 ? (
            <p className="text-sm text-slate-600 dark:text-slate-400">All listed skills are verified.</p>
          ) : (
            data.unverified.map((u) => (
              <div key={u.skill} className="flex items-center justify-between text-sm">
                <span>
                  {u.skill} ({u.self_reported_level})
                </span>
                <Link to={`/assessments?skill=${encodeURIComponent(u.skill)}`} className="text-xs font-semibold text-indigo-600 dark:text-indigo-400">
                  Verify Now →
                </Link>
              </div>
            ))
          )}
        </Card>
      </div>

      {data.outdated.length > 0 && (
        <Card className="space-y-3 border-amber-300 dark:border-amber-800">
          <h2 className="font-semibold text-amber-800 dark:text-amber-200">Outdated / Declining Technology Alerts</h2>
          {data.outdated.map((o) => (
            <div key={o.skill} className="rounded-lg bg-amber-50 dark:bg-amber-950/30 p-3 text-sm space-y-1">
              <p className="font-semibold">{o.skill}</p>
              <p>{o.issue}</p>
              <p className="text-xs">
                <strong>Recommendation:</strong> {o.recommendation}
              </p>
              <p className="text-xs text-slate-600 dark:text-slate-400">
                Evidence: {o.evidence} · Source: {o.source}
              </p>
            </div>
          ))}
        </Card>
      )}

      <Card className="space-y-3">
        <h2 className="font-semibold text-teal-700 dark:text-teal-400">Emerging High-Value Skills</h2>
        <div className="grid gap-3 sm:grid-cols-3">
          {data.emerging.map((e) => (
            <div key={e.skill} className="rounded-lg border border-slate-200 dark:border-slate-800 p-3 text-xs space-y-1">
              <p className="text-sm font-semibold">{e.skill}</p>
              <p>{e.reason}</p>
              <p className="text-slate-500">{e.evidence}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
