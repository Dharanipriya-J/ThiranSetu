import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import type { JobSummary } from '../../api/types';
import { safeUrl as safeHttpUrl } from '../../lib/format';
import { Badge, Button, Card, DataNotice } from '../ui';

interface JobCardProps {
  job: JobSummary;
  onSave: (jobId: string | number) => void;
  saving: boolean;
}

export function JobCard({ job, onSave, saving }: JobCardProps) {
  const { t } = useTranslation();
  const safeUrl = safeHttpUrl(job.apply_url);

  return (
    <Card className="space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Link to={`/jobs/${job.id}`} className="text-lg font-bold text-indigo-600 dark:text-indigo-400 hover:underline">
              {job.title}
            </Link>
            <Badge tone="indigo">{job.score}% match</Badge>
            <Badge
              tone={
                job.verification_status === 'Verified'
                  ? 'emerald'
                  : job.verification_status === 'Pending Verification'
                    ? 'amber'
                    : 'rose'
              }
            >
              {job.verification_status ?? 'Verified'}
            </Badge>
            <DataNotice isDemo={job.is_demo} label={t('common.demoData')} />
          </div>
          <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
            {job.company} · {job.location} ({job.work_mode}) · Exp: {job.experience_min_years}+ yrs
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Salary: <strong>{job.salary.label === 'Not Disclosed' ? t('common.notDisclosed') : job.salary.label}</strong>
            {' · '}Source: {job.source}
            {' · '}Posted: {job.posted_date}
            {job.last_verified_date ? ` · Verified: ${job.last_verified_date}` : ''}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="secondary" disabled={job.saved || saving} onClick={() => onSave(job.id)}>
            {job.saved ? t('jobs.saved') : t('jobs.saveJob')}
          </Button>
          <Link to={`/jobs/${job.id}`}>
            <Button size="sm" variant="secondary">
              Skill Gap Analysis
            </Button>
          </Link>
          {safeUrl && (
            <a href={safeUrl} target="_blank" rel="noopener noreferrer">
              <Button size="sm">{t('jobs.applyNow')}</Button>
            </a>
          )}
        </div>
      </div>

      <div className="grid gap-2 sm:grid-cols-3 text-xs">
        <div>
          <strong>{t('jobs.mandatorySkills')}:</strong> {job.mandatory_skills.join(', ') || '—'}
        </div>
        <div className="text-emerald-700 dark:text-emerald-400">
          <strong>Matching:</strong> {job.matching_skills.join(', ') || 'None yet'}
        </div>
        <div className="text-rose-700 dark:text-rose-400">
          <strong>{t('jobs.missingSkills')}:</strong> {job.missing_skills.join(', ') || 'None'}
        </div>
      </div>
    </Card>
  );
}
