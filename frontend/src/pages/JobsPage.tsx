import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../api/client';
import type { ApplicationStatus, JobQuery } from '../api/types';
import { errorMessage } from '../lib/errors';
import { JobAddForm } from '../components/jobs/JobAddForm';
import { JobCard } from '../components/jobs/JobCard';
import { Button, Card, EmptyState, ErrorState, Input, PageHeader, Select, Spinner } from '../components/ui';

export default function JobsPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();

  const [tab, setTab] = useState<'browse' | 'tracker' | 'add'>('browse');
  const [query, setQuery] = useState<JobQuery>({ sort: 'score', page: 1, page_size: 10 });
  const [syncNotice, setSyncNotice] = useState('');

  const jobsQ = useQuery({ queryKey: ['jobs', query], queryFn: () => api.jobs(query) });
  const appsQ = useQuery({ queryKey: ['applications'], queryFn: api.applications });

  const saveMut = useMutation({
    mutationFn: (jobId: string | number) => api.saveJob(jobId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['jobs'] });
      void qc.invalidateQueries({ queryKey: ['applications'] });
    },
  });

  const syncMut = useMutation({
    mutationFn: () => api.syncJobs(),
    onSuccess: (res) => {
      setSyncNotice(res.message);
      void qc.invalidateQueries({ queryKey: ['jobs'] });
    },
    onError: (err) => setSyncNotice(errorMessage(err, t)),
  });

  const updateAppMut = useMutation({
    mutationFn: ({ id, status, notes }: { id: string | number; status?: ApplicationStatus; notes?: string }) =>
      api.updateApplication(id, { status, notes }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['applications'] }),
  });

  const deleteAppMut = useMutation({
    mutationFn: (id: string | number) => api.deleteApplication(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['applications'] });
      void qc.invalidateQueries({ queryKey: ['jobs'] });
    },
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('jobs.title')}
        subtitle={t('jobs.applyNotice')}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" onClick={() => syncMut.mutate()} disabled={syncMut.isPending}>
              {syncMut.isPending ? t('common.loading') : 'Sync Permitted Feed'}
            </Button>
            <Button size="sm" variant={tab === 'browse' ? 'primary' : 'secondary'} onClick={() => setTab('browse')}>
              Vacancies ({jobsQ.data?.total ?? 0})
            </Button>
            <Button size="sm" variant={tab === 'tracker' ? 'primary' : 'secondary'} onClick={() => setTab('tracker')}>
              {t('jobs.trackerTab')} ({appsQ.data?.length ?? 0})
            </Button>
            <Button size="sm" variant={tab === 'add' ? 'primary' : 'secondary'} onClick={() => setTab('add')}>
              {t('jobs.addTab')}
            </Button>
          </div>
        }
      />

      {syncNotice && (
        <Card className="text-xs text-slate-700 dark:text-slate-300">
          <p role="status">{syncNotice}</p>
        </Card>
      )}

      {tab === 'browse' && (
        <div className="space-y-4">
          <Card className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
            <Input
              label="Role / Keyword"
              placeholder="Data Analyst..."
              value={query.q ?? ''}
              onChange={(e) => setQuery({ ...query, q: e.target.value, page: 1 })}
            />
            <Input
              label="Company"
              placeholder="Zoho, TCS..."
              value={query.company ?? ''}
              onChange={(e) => setQuery({ ...query, company: e.target.value, page: 1 })}
            />
            <Input
              label="Location"
              placeholder="Chennai, Remote..."
              value={query.location ?? ''}
              onChange={(e) => setQuery({ ...query, location: e.target.value, page: 1 })}
            />
            <Select
              label="Work Mode"
              value={query.work_mode ?? ''}
              onChange={(e) => setQuery({ ...query, work_mode: e.target.value, page: 1 })}
            >
              <option value="">All</option>
              <option value="remote">Remote</option>
              <option value="hybrid">Hybrid</option>
              <option value="onsite">On-site</option>
            </Select>
            <Input
              label="Min Salary (LPA)"
              type="number"
              min="0"
              value={query.min_salary ?? ''}
              onChange={(e) => setQuery({ ...query, min_salary: e.target.value || undefined, page: 1 })}
            />
            <Select
              label="Sort By"
              value={query.sort ?? 'score'}
              onChange={(e) => setQuery({ ...query, sort: e.target.value as 'score' | 'date' | 'salary' })}
            >
              <option value="score">Compatibility Score</option>
              <option value="date">Posting Date</option>
              <option value="salary">Salary</option>
            </Select>
          </Card>

          {jobsQ.isLoading && <Spinner label={t('common.loading')} />}
          {jobsQ.error && <ErrorState message={errorMessage(jobsQ.error, t)} />}
          {jobsQ.data && jobsQ.data.items.length === 0 && (
            <EmptyState
              title={
                query.q || query.company || query.location || query.work_mode || query.min_salary
                  ? 'No matching vacancies'
                  : 'No verified company vacancies available yet'
              }
              description={
                query.q || query.company || query.location || query.work_mode || query.min_salary
                  ? 'Try clearing some filters or adding a new company vacancy.'
                  : 'Synthetic demonstration vacancies are excluded to preserve data integrity. Submit a real company job description or sync a permitted HTTPS job feed.'
              }
              action={
                <div className="flex flex-wrap justify-center gap-2">
                  {(query.q || query.company || query.location || query.work_mode || query.min_salary) && (
                    <Button variant="secondary" onClick={() => setQuery({ sort: 'score', page: 1, page_size: 10 })}>
                      {t('common.reset')}
                    </Button>
                  )}
                  <Button onClick={() => setTab('add')}>{t('jobs.addTab')}</Button>
                </div>
              }
            />
          )}

          <div className="space-y-4">
            {(jobsQ.data?.items ?? []).map((j) => (
              <JobCard key={j.id} job={j} onSave={(id) => saveMut.mutate(id)} saving={saveMut.isPending} />
            ))}
          </div>
        </div>
      )}

      {tab === 'tracker' && (
        <div className="space-y-4">
          {(appsQ.data ?? []).length === 0 ? (
            <EmptyState
              title="No saved jobs yet"
              description="Save a job from the Vacancies tab to track your preparation and applications."
            />
          ) : (
            (appsQ.data ?? []).map((app) => (
              <Card key={app.id} className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <Link to={`/jobs/${app.job.id}`} className="font-semibold text-indigo-600 dark:text-indigo-400 hover:underline">
                    {app.job.title} — {app.job.company}
                  </Link>
                  <p className="text-xs text-slate-500">
                    {app.job.score}% match · {app.job.salary.label}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    aria-label={`Status for ${app.job.title}`}
                    value={app.status}
                    onChange={(e) => updateAppMut.mutate({ id: app.id, status: e.target.value as ApplicationStatus })}
                    className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-2.5 py-1.5 text-sm"
                  >
                    <option value="saved">Saved</option>
                    <option value="applied">Applied (Self-Marked)</option>
                    <option value="interviewing">Interviewing</option>
                    <option value="offer">Offer</option>
                    <option value="rejected">Rejected</option>
                  </select>
                  <Button size="sm" variant="danger" onClick={() => deleteAppMut.mutate(app.id)}>
                    Remove
                  </Button>
                </div>
              </Card>
            ))
          )}
        </div>
      )}

      {tab === 'add' && (
        <JobAddForm
          onCreated={() => {
            setTab('browse');
            void qc.invalidateQueries({ queryKey: ['jobs'] });
            void qc.invalidateQueries({ queryKey: ['market'] });
            void qc.invalidateQueries({ queryKey: ['careers'] });
            void qc.invalidateQueries({ queryKey: ['dashboard'] });
          }}
        />
      )}
    </div>
  );
}
