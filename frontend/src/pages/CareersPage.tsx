import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { api } from '../api/client';
import { errorMessage } from '../lib/errors';
import { Badge, Button, Card, ErrorState, PageHeader, ProgressBar, Spinner } from '../components/ui';

export default function CareersPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [notice, setNotice] = useState('');

  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['careers'], queryFn: api.careers });

  const setTargetMut = useMutation({
    mutationFn: (roleId: string) => api.setTargetCareer(roleId),
    onSuccess: (_roadmap, roleId) => {
      void qc.invalidateQueries({ queryKey: ['careers'] });
      void qc.invalidateQueries({ queryKey: ['roadmap'] });
      void qc.invalidateQueries({ queryKey: ['dashboard'] });
      setNotice(`Target career updated to ${roleId} and learning roadmap recalculated.`);
    },
  });

  if (isLoading) return <Spinner label={t('common.loading')} />;
  if (error || !data) return <ErrorState message={errorMessage(error, t)} onRetry={() => void refetch()} />;

  return (
    <div className="space-y-6">
      <PageHeader title={t('nav.careers')} subtitle={t('common.compatibilityNote')} />

      {notice && (
        <p role="status" className="rounded-lg bg-emerald-50 dark:bg-emerald-950/50 p-3 text-sm text-emerald-800 dark:text-emerald-200">
          {notice}
        </p>
      )}

      <div className="space-y-4">
        {data.map((c) => (
          <Card key={c.role_id} className="space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-lg font-bold">{c.title}</h2>
                  {c.is_target && <Badge tone="indigo">Target Career</Badge>}
                  <Badge tone={c.score >= 78 ? 'emerald' : c.score >= 60 ? 'indigo' : 'amber'}>
                    {c.score}% · {c.label}
                  </Badge>
                  <Badge tone="neutral">
                    Demand: {c.demand_level} ({c.vacancies} openings)
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">{c.explanation}</p>
              </div>
              <Button
                size="sm"
                variant={c.is_target ? 'secondary' : 'primary'}
                disabled={c.is_target || setTargetMut.isPending}
                onClick={() => setTargetMut.mutate(c.role_id)}
              >
                {c.is_target ? 'Current Target' : 'Set as Target Career'}
              </Button>
            </div>

            <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
              {Object.entries(c.components).map(([key, val]) => (
                <ProgressBar key={key} value={val} label={`${key.replace('_', ' ')} (${Math.round((c.weights[key as keyof typeof c.weights] ?? 0) * 100)}%)`} />
              ))}
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-xs">
              <div>
                <strong className="text-emerald-700 dark:text-emerald-400">Matching Skills:</strong>{' '}
                {c.matching_skills.length ? c.matching_skills.map((s) => `${s.skill} (${s.score}%)`).join(', ') : 'None yet'}
              </div>
              <div>
                <strong className="text-amber-700 dark:text-amber-400">Improve:</strong>{' '}
                {c.improve_skills.length ? c.improve_skills.map((s) => `${s.skill} (${s.score}%)`).join(', ') : 'None'}
              </div>
              <div>
                <strong className="text-rose-700 dark:text-rose-400">Missing:</strong>{' '}
                {c.missing_skills.length ? c.missing_skills.join(', ') : 'None'}
              </div>
              <div>
                <strong>Salary Range:</strong>{' '}
                {c.salary_range
                  ? `₹${c.salary_range.min_lpa}–${c.salary_range.max_lpa} LPA (${c.salary_range.source})`
                  : t('common.notDisclosed')}
              </div>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              <strong>Location Fit:</strong> {c.location_fit} · <strong>Suggested Learning Path:</strong>{' '}
              {c.learning_path.length ? c.learning_path.join(' → ') : 'All core skills verified!'}
            </p>
          </Card>
        ))}
      </div>
    </div>
  );
}
