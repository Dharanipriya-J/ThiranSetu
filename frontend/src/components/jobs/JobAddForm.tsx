import { useState, type FormEvent } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { api } from '../../api/client';
import type { ExtractedRequirements } from '../../api/types';
import { errorMessage } from '../../lib/errors';
import { Button, Card, Input, Select, TextArea } from '../ui';

interface JobAddFormProps {
  onCreated: () => void;
}

function parseSkillList(raw: string): string[] {
  return raw
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

export function JobAddForm({ onCreated }: JobAddFormProps) {
  const { t } = useTranslation();

  const [company, setCompany] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [location, setLocation] = useState('');
  const [workMode, setWorkMode] = useState<'remote' | 'hybrid' | 'onsite'>('hybrid');
  const [salMin, setSalMin] = useState('');
  const [salMax, setSalMax] = useState('');
  const [expMin, setExpMin] = useState('0');
  const [education, setEducation] = useState('');
  const [mandatoryText, setMandatoryText] = useState('');
  const [preferredText, setPreferredText] = useState('');
  const [applyUrl, setApplyUrl] = useState('https://');
  const [source, setSource] = useState('Employer Official Career Page');
  const [extracted, setExtracted] = useState<ExtractedRequirements | null>(null);
  const [formMsg, setFormMsg] = useState('');

  const extractMut = useMutation({
    mutationFn: () => api.extractJob(description),
    onSuccess: (res) => {
      setExtracted(res);
      setMandatoryText(res.mandatory_skills.join(', '));
      setPreferredText(res.preferred_skills.join(', '));
      if (res.experience_years !== null && expMin === '0') setExpMin(String(res.experience_years));
      if (res.education && !education) setEducation(res.education);
      if (res.location && !location) setLocation(res.location);
      if (res.work_mode && (res.work_mode === 'remote' || res.work_mode === 'hybrid' || res.work_mode === 'onsite')) {
        setWorkMode(res.work_mode);
      }
      if (res.salary_min_lpa != null && !salMin) setSalMin(String(res.salary_min_lpa));
      if (res.salary_max_lpa != null && !salMax) setSalMax(String(res.salary_max_lpa));
    },
    onError: (err) => setFormMsg(errorMessage(err, t)),
  });

  const createJobMut = useMutation({
    mutationFn: () =>
      api.createJob({
        company,
        title,
        description,
        mandatory_skills: extracted || mandatoryText ? parseSkillList(mandatoryText) : undefined,
        preferred_skills: extracted || preferredText ? parseSkillList(preferredText) : undefined,
        location,
        work_mode: workMode,
        salary_min_lpa: salMin ? Number(salMin) : null,
        salary_max_lpa: salMax ? Number(salMax) : null,
        experience_min_years: Number(expMin) || 0,
        education,
        posted_date: new Date().toISOString().slice(0, 10),
        apply_url: applyUrl,
        source,
      }),
    onSuccess: () => {
      setFormMsg('Vacancy validated, saved, and matched against your verified skills.');
      onCreated();
    },
    onError: (err) => setFormMsg(errorMessage(err, t)),
  });

  function handleCreate(e: FormEvent) {
    e.preventDefault();
    setFormMsg('');
    createJobMut.mutate();
  }

  return (
    <Card className="space-y-4">
      <div>
        <h2 className="text-base font-semibold">Add &amp; Validate a Company Vacancy</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Paste a complete job description, extract requirements, review or edit them below, and save to match against your verified skills.
        </p>
      </div>
      {formMsg && (
        <p role="status" className="text-sm text-indigo-600 dark:text-indigo-400">
          {formMsg}
        </p>
      )}
      <form onSubmit={handleCreate} className="grid gap-4 sm:grid-cols-2">
        <Input label="Company Name" value={company} onChange={(e) => setCompany(e.target.value)} required />
        <Input label="Job Title" value={title} onChange={(e) => setTitle(e.target.value)} required />
        <div className="sm:col-span-2 space-y-2">
          <TextArea
            label="Job Description (50+ chars — include Mandatory: / Preferred: skills)"
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
          />
          <Button type="button" variant="secondary" size="sm" onClick={() => extractMut.mutate()} disabled={description.length < 10 || extractMut.isPending}>
            {extractMut.isPending ? t('common.loading') : t('jobs.extractPreview')}
          </Button>
        </div>

        <Input
          label="Mandatory Skills (comma-separated, editable)"
          placeholder="Python, SQL, Power BI"
          value={mandatoryText}
          onChange={(e) => setMandatoryText(e.target.value)}
        />
        <Input
          label="Preferred Skills (comma-separated, editable)"
          placeholder="Excel, Docker"
          value={preferredText}
          onChange={(e) => setPreferredText(e.target.value)}
        />
        <Input label="Location" value={location} onChange={(e) => setLocation(e.target.value)} required />
        <Select label="Work Mode" value={workMode} onChange={(e) => setWorkMode(e.target.value as 'remote' | 'hybrid' | 'onsite')}>
          <option value="hybrid">Hybrid</option>
          <option value="onsite">On-site</option>
          <option value="remote">Remote</option>
        </Select>
        <Input label="Min Salary (LPA, optional — leave blank if undisclosed)" type="number" step="0.5" min="0" value={salMin} onChange={(e) => setSalMin(e.target.value)} />
        <Input label="Max Salary (LPA, optional)" type="number" step="0.5" min="0" value={salMax} onChange={(e) => setSalMax(e.target.value)} />
        <Input label="Min Experience (Years)" type="number" step="0.5" min="0" value={expMin} onChange={(e) => setExpMin(e.target.value)} />
        <Input label="Education" value={education} onChange={(e) => setEducation(e.target.value)} />
        <Input label="Official Application URL (https://)" value={applyUrl} onChange={(e) => setApplyUrl(e.target.value)} required />
        <Input label="Source" value={source} onChange={(e) => setSource(e.target.value)} required />

        <div className="sm:col-span-2 flex justify-end">
          <Button type="submit" disabled={createJobMut.isPending}>
            {createJobMut.isPending ? t('common.saving') : 'Save & Match Vacancy'}
          </Button>
        </div>
      </form>
    </Card>
  );
}
