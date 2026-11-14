import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../api/client';
import { errorMessage } from '../lib/errors';
import { safeUrl as safeHttpUrl } from '../lib/format';
import { Badge, Button, Card, DataNotice, ErrorState, PageHeader, ProgressBar, Spinner } from '../components/ui';

export default function JobDetailPage() {
  const { id } = useParams();
  const { t } = useTranslation();
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['job', id],
    queryFn: () => api.job(id!),
    enabled: Boolean(id),
  });

  if (isLoading) return <Spinner label={t('common.loading')} />;
  if (error || !data) return <ErrorState message={errorMessage(error, t)} onRetry={() => void refetch()} />;

  const safeUrl = safeHttpUrl(data.apply_url);
  const m = data.match;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${data.title} — ${data.company}`}
        subtitle={`${data.location} (${data.work_mode}) · ${data.salary.label === 'Not Disclosed' ? t('common.notDisclosed') : data.salary.label} · Source: ${data.source}`}
        actions={
          <>
            <DataNotice isDemo={data.is_demo} label={t('common.demoData')} />
            <Link to="/jobs">
              <Button variant="secondary" size="sm">
                {t('common.back')}
              </Button>
            </Link>
            {safeUrl && (
              <a href={safeUrl} target="_blank" rel="noopener noreferrer">
                <Button size="sm">{t('jobs.applyNow')}</Button>
              </a>
            )}
          </>
        }
      />

      <Card className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-bold">Compatibility Breakdown: {m.score}%</h2>
          <span className="text-xs text-slate-500">{t('common.compatibilityNote')}</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {Object.entries(m.components).map(([k, v]) => (
            <ProgressBar key={k} value={v} label={`${k} (${Math.round((m.weights[k as keyof typeof m.weights] ?? 0) * 100)}%)`} />
          ))}
        </div>
        <p className="text-sm text-slate-700 dark:text-slate-300">{m.explanation}</p>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="space-y-2 text-sm">
          <h2 className="font-semibold">Skill Match Diagnostics</h2>
          <p className="text-emerald-700 dark:text-emerald-400">
            <strong>Strong Matches:</strong>{' '}
            {m.strong_matches.length ? m.strong_matches.map((s) => `${s.skill} (${s.score}%)`).join(', ') : 'None yet'}
          </p>
          <p className="text-amber-700 dark:text-amber-400">
            <strong>Partial Matches:</strong>{' '}
            {m.partial_matches.length ? m.partial_matches.map((s) => `${s.skill} (${s.score}% / target ${s.target}%)`).join(', ') : 'None'}
          </p>
          <p className="text-rose-700 dark:text-rose-400">
            <strong>Missing Mandatory:</strong> {m.missing_mandatory.join(', ') || 'None'}
          </p>
          <p>
            <strong>Missing Preferred:</strong> {m.missing_preferred.join(', ') || 'None'}
          </p>
          <p>
            <strong>Not Yet Assessed:</strong> {m.not_assessed.join(', ') || 'None'}
          </p>
          {m.qualification_gaps.length > 0 && (
            <p className="text-amber-800 dark:text-amber-200">
              <strong>Qualification Gaps:</strong> {m.qualification_gaps.join(' ')}
            </p>
          )}
        </Card>

        <Card className="space-y-2 text-sm">
          <h2 className="font-semibold">Salary, Location & Description</h2>
          <p>
            <strong>{t('jobs.salaryFit')}:</strong> <Badge tone="indigo">{m.salary_fit.status}</Badge> — {m.salary_fit.message}
          </p>
          <p>
            <strong>{t('jobs.locationFit')}:</strong> <Badge tone="teal">{m.location_fit.status}</Badge> — {m.location_fit.message}
          </p>
          <p className="pt-2 text-xs text-slate-600 dark:text-slate-400">{data.description}</p>
        </Card>
      </div>

      {data.recommended_courses.length > 0 && (
        <Card className="space-y-3">
          <h2 className="text-base font-semibold">Recommended Courses for This Vacancy's Gaps</h2>
          <div className="grid gap-4 md:grid-cols-2">
            {data.recommended_courses.map((grp) => (
              <div key={grp.skill} className="rounded-lg border border-slate-200 dark:border-slate-800 p-3 space-y-2">
                <p className="font-semibold text-sm">{grp.skill}</p>
                {grp.courses.map((c) => {
                  const url = safeHttpUrl(c.url);
                  return (
                    <div key={c.id} className="text-xs flex items-center justify-between gap-2">
                      <span>
                        {c.title} ({c.platform} · {c.price.label})
                      </span>
                      {url && (
                        <a href={url} target="_blank" rel="noopener noreferrer" className="font-semibold text-indigo-600 dark:text-indigo-400 shrink-0">
                          Open →
                        </a>
                      )}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
