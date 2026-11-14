import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../api/client';
import type { StepStatus } from '../api/types';
import { errorMessage } from '../lib/errors';
import { safeUrl as safeHttpUrl } from '../lib/format';
import { Badge, Button, Card, ErrorState, PageHeader, ProgressBar, Spinner } from '../components/ui';

export default function RoadmapPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();

  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['roadmap'], queryFn: api.roadmap });

  const stepMut = useMutation({
    mutationFn: ({ id, status }: { id: string | number; status: StepStatus }) => api.updateStep(id, status),
    onSuccess: (updated) => {
      qc.setQueryData(['roadmap'], updated);
      void qc.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  const regenMut = useMutation({
    mutationFn: api.regenerateRoadmap,
    onSuccess: (updated) => {
      qc.setQueryData(['roadmap'], updated);
      void qc.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  if (isLoading) return <Spinner label={t('common.loading')} />;
  if (error || !data) return <ErrorState message={errorMessage(error, t)} onRetry={() => void refetch()} />;

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('roadmap.title')}
        subtitle={
          (data.target_role ? `Target Career: ${data.target_role.title} · ` : '') + data.reason
        }
        actions={
          <Button size="sm" onClick={() => regenMut.mutate()} disabled={regenMut.isPending}>
            {regenMut.isPending ? t('common.loading') : t('roadmap.regenerate')}
          </Button>
        }
      />

      <ProgressBar value={data.progress_percent} label="Overall Learning Progress" />

      <div className="space-y-4">
        {data.steps.map((st) => {
          const courseUrl = st.course ? safeHttpUrl(st.course.url) : null;
          return (
            <Card key={st.id} className="space-y-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-base font-bold">
                      Step {st.order}: {st.skill}
                    </span>
                    <Badge tone={st.priority === 'high' ? 'rose' : st.priority === 'medium' ? 'amber' : 'indigo'}>
                      {st.priority} priority
                    </Badge>
                    <Badge tone="neutral">~{st.estimated_hours}h</Badge>
                    {st.current_score !== null && (
                      <Badge tone="teal">
                        Current: {st.current_score}% / Target: {st.target_score}%
                      </Badge>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">{st.reason}</p>
                </div>

                <div className="flex items-center gap-2">
                  <select
                    aria-label={`Status for step ${st.order}: ${st.skill}`}
                    value={st.status}
                    onChange={(e) => stepMut.mutate({ id: st.id, status: e.target.value as StepStatus })}
                    className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-2.5 py-1.5 text-sm"
                  >
                    <option value="not_started">Not Started</option>
                    <option value="in_progress">In Progress</option>
                    <option value="completed">Completed</option>
                  </select>
                  {st.reassessment_required && (
                    <Link to={`/assessments?skill=${encodeURIComponent(st.skill)}`}>
                      <Button size="sm">{t('roadmap.reassess')}</Button>
                    </Link>
                  )}
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 text-xs">
                <p>
                  <strong>Practical Exercise:</strong> {st.exercise}
                </p>
                <p>
                  <strong>Mini-Project:</strong> {st.project}
                </p>
              </div>

              {st.course && (
                <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 px-3 py-2 text-xs">
                  <span>
                    <strong>Recommended Course:</strong> {st.course.title} ({st.course.platform} · {st.course.price.label})
                  </span>
                  {courseUrl && (
                    <a href={courseUrl} target="_blank" rel="noopener noreferrer" className="font-semibold text-indigo-600 dark:text-indigo-400">
                      Open Course →
                    </a>
                  )}
                </div>
              )}

              {st.reassessment_required && (
                <p className="text-xs font-medium text-amber-700 dark:text-amber-300">{t('roadmap.reassessRequired')}</p>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
