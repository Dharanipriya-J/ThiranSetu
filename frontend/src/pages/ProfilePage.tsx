import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { api } from '../api/client';
import type { LangCode, Level, Profile, ProfileUpdate, TechnicalSkill, WorkMode } from '../api/types';
import { LANGUAGES } from '../i18n';
import { errorMessage } from '../lib/errors';
import { Badge, Button, Card, ErrorState, Input, PageHeader, ProgressBar, Select, Spinner, TextArea } from '../components/ui';

function profileToForm(p: Profile): ProfileUpdate {
  return {
    full_name: p.full_name,
    education: p.education,
    college: p.college,
    graduation_year: p.graduation_year,
    technical_skills: p.technical_skills,
    soft_skills: p.soft_skills,
    projects: p.projects,
    certifications: p.certifications,
    experience_years: p.experience_years,
    experience_summary: p.experience_summary,
    career_interests: p.career_interests,
    target_role: p.target_role ?? '',
    current_location: p.current_location,
    preferred_locations: p.preferred_locations,
    willing_to_relocate: p.willing_to_relocate,
    work_mode: p.work_mode,
    expected_salary_lpa: p.expected_salary_lpa,
    min_salary_lpa: p.min_salary_lpa,
    learning_language: p.learning_language,
    app_language: p.app_language,
  };
}

export default function ProfilePage() {
  const { t } = useTranslation();
  const qc = useQueryClient();

  const profileQ = useQuery({ queryKey: ['profile'], queryFn: api.getProfile });
  const rolesQ = useQuery({ queryKey: ['roles'], queryFn: api.roles });
  const skillsQ = useQuery({ queryKey: ['skills'], queryFn: api.skills });

  const [draft, setDraft] = useState<ProfileUpdate | null>(null);
  const [newSkill, setNewSkill] = useState('');
  const [newSkillLevel, setNewSkillLevel] = useState<Level>('intermediate');
  const [draftSoftSkills, setDraftSoftSkills] = useState<string | null>(null);
  const [draftPrefLocs, setDraftPrefLocs] = useState<string | null>(null);
  const [projTitle, setProjTitle] = useState('');
  const [projDesc, setProjDesc] = useState('');
  const [certName, setCertName] = useState('');
  const [certIssuer, setCertIssuer] = useState('');
  const [statusMsg, setStatusMsg] = useState('');
  const [errMsg, setErrMsg] = useState('');

  const form: ProfileUpdate = draft ?? (profileQ.data ? profileToForm(profileQ.data) : {});
  const setForm = (next: ProfileUpdate) => setDraft(next);
  const softSkillInput = draftSoftSkills ?? (profileQ.data?.soft_skills ?? []).join(', ');
  const setSoftSkillInput = (val: string) => setDraftSoftSkills(val);
  const prefLocInput = draftPrefLocs ?? (profileQ.data?.preferred_locations ?? []).join(', ');
  const setPrefLocInput = (val: string) => setDraftPrefLocs(val);

  const saveMut = useMutation({
    mutationFn: (payload: ProfileUpdate) => api.updateProfile(payload),
    onSuccess: (updated) => {
      qc.setQueryData(['profile'], updated);
      setDraft(null);
      setDraftSoftSkills(null);
      setDraftPrefLocs(null);
      void qc.invalidateQueries({ queryKey: ['dashboard'] });
      setErrMsg('');
      setStatusMsg('Profile saved and all 7 AI agents updated.');
    },
    onError: (err) => {
      setStatusMsg('');
      setErrMsg(errorMessage(err, t));
    },
  });

  if (profileQ.isLoading) return <Spinner label={t('common.loading')} />;
  if (profileQ.error || !profileQ.data) return <ErrorState message={errorMessage(profileQ.error, t)} />;

  function addTechSkill() {
    const name = newSkill.trim();
    if (!name) return;
    const current = (form.technical_skills ?? []) as TechnicalSkill[];
    const filtered = current.filter((s) => s.name.toLowerCase() !== name.toLowerCase());
    setForm({ ...form, technical_skills: [...filtered, { name, self_level: newSkillLevel }] });
    setNewSkill('');
  }

  function removeTechSkill(name: string) {
    setForm({
      ...form,
      technical_skills: (form.technical_skills ?? []).filter((s) => s.name !== name),
    });
  }

  function addProject() {
    if (!projTitle.trim()) return;
    setForm({
      ...form,
      projects: [...(form.projects ?? []), { title: projTitle.trim(), description: projDesc.trim(), skills: [] }],
    });
    setProjTitle('');
    setProjDesc('');
  }

  function addCert() {
    if (!certName.trim()) return;
    setForm({
      ...form,
      certifications: [...(form.certifications ?? []), { name: certName.trim(), issuer: certIssuer.trim(), year: null }],
    });
    setCertName('');
    setCertIssuer('');
  }

  function useBrowserLocation() {
    if (!('geolocation' in navigator)) {
      setErrMsg('Browser geolocation is unavailable. Enter your city manually.');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setForm({
          ...form,
          current_location: `${pos.coords.latitude.toFixed(3)}, ${pos.coords.longitude.toFixed(3)}`,
        });
      },
      () => setErrMsg('Location permission declined. You can type your city manually.'),
    );
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const soft = softSkillInput.split(',').map((s) => s.trim()).filter(Boolean);
    const locs = prefLocInput.split(',').map((s) => s.trim()).filter(Boolean);
    saveMut.mutate({
      ...form,
      target_role: form.target_role || null,
      soft_skills: soft,
      preferred_locations: locs,
    });
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Student Profile"
        subtitle="Self-reported skills, projects, salary expectations, and location preferences."
        actions={<Badge tone="indigo">Completeness: {profileQ.data.completeness}%</Badge>}
      />

      <ProgressBar value={profileQ.data.completeness} label="Profile Completeness" />

      {statusMsg && (
        <p role="status" className="rounded-lg bg-emerald-50 dark:bg-emerald-950/50 p-3 text-sm text-emerald-800 dark:text-emerald-200">
          {statusMsg}
        </p>
      )}
      {errMsg && (
        <p role="alert" className="rounded-lg bg-rose-50 dark:bg-rose-950/50 p-3 text-sm text-rose-700 dark:text-rose-200">
          {errMsg}
        </p>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card className="grid gap-4 sm:grid-cols-2">
          <Input label="Full Name" value={form.full_name ?? ''} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
          <Input label="Education / Qualification" placeholder="e.g. B.Tech CSE" value={form.education ?? ''} onChange={(e) => setForm({ ...form, education: e.target.value })} />
          <Input label="College / University" value={form.college ?? ''} onChange={(e) => setForm({ ...form, college: e.target.value })} />
          <Input
            label="Graduation Year"
            type="number"
            value={form.graduation_year ?? ''}
            onChange={(e) => setForm({ ...form, graduation_year: e.target.value ? Number(e.target.value) : null })}
          />
          <Input
            label="Experience (Years)"
            type="number"
            step="0.5"
            min="0"
            value={form.experience_years ?? 0}
            onChange={(e) => setForm({ ...form, experience_years: Number(e.target.value) || 0 })}
          />
          <Select
            label="Target Career"
            value={form.target_role ?? ''}
            onChange={(e) => setForm({ ...form, target_role: e.target.value })}
          >
            <option value="">Auto-rank from profile</option>
            {(rolesQ.data ?? []).map((r) => (
              <option key={r.id} value={r.id}>
                {r.title}
              </option>
            ))}
          </Select>
          <div className="sm:col-span-2">
            <TextArea
              label="Experience Summary"
              rows={2}
              value={form.experience_summary ?? ''}
              onChange={(e) => setForm({ ...form, experience_summary: e.target.value })}
            />
          </div>
        </Card>

        <Card className="space-y-4">
          <h2 className="text-base font-semibold">Technical Skills (Self-Reported — Verify via Assessments)</h2>
          <div className="flex flex-wrap items-end gap-2">
            <div className="flex-1 min-w-[180px]">
              <Input
                label="Add Technical Skill"
                list="canonical-skills"
                placeholder="Python, SQL, Excel, Power BI..."
                value={newSkill}
                onChange={(e) => setNewSkill(e.target.value)}
              />
              <datalist id="canonical-skills">
                {(skillsQ.data ?? []).map((s) => (
                  <option key={s.name} value={s.name} />
                ))}
              </datalist>
            </div>
            <Select label="Self Level" value={newSkillLevel} onChange={(e) => setNewSkillLevel(e.target.value as Level)}>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </Select>
            <Button type="button" variant="secondary" onClick={addTechSkill}>
              Add Skill
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {(form.technical_skills ?? []).map((sk) => (
              <Badge key={sk.name} tone="indigo" className="py-1 px-3">
                {sk.name} ({sk.self_level})
                <button type="button" onClick={() => removeTechSkill(sk.name)} aria-label={`Remove ${sk.name}`} className="ml-1 font-bold">
                  ×
                </button>
              </Badge>
            ))}
          </div>
          <Input label="Soft Skills (comma separated)" value={softSkillInput} onChange={(e) => setSoftSkillInput(e.target.value)} />
        </Card>

        <Card className="space-y-4">
          <h2 className="text-base font-semibold">Career Interests</h2>
          <div className="grid gap-2 sm:grid-cols-3">
            {(rolesQ.data ?? []).map((r) => {
              const checked = (form.career_interests ?? []).includes(r.id);
              return (
                <label key={r.id} className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => {
                      const curr = form.career_interests ?? [];
                      setForm({
                        ...form,
                        career_interests: checked ? curr.filter((x) => x !== r.id) : [...curr, r.id],
                      });
                    }}
                  />
                  <span>{r.title}</span>
                </label>
              );
            })}
          </div>
        </Card>

        <Card className="grid gap-4 sm:grid-cols-2">
          <div>
            <Input
              label="Current Location (Optional)"
              placeholder="e.g. Coimbatore"
              value={form.current_location ?? ''}
              onChange={(e) => setForm({ ...form, current_location: e.target.value })}
            />
            <Button type="button" variant="ghost" size="sm" onClick={useBrowserLocation} className="mt-1">
              Use browser location (optional)
            </Button>
          </div>
          <Input
            label="Preferred Job Locations (comma separated)"
            placeholder="Chennai, Bengaluru, Remote"
            value={prefLocInput}
            onChange={(e) => setPrefLocInput(e.target.value)}
          />
          <Select
            label="Preferred Work Mode"
            value={form.work_mode ?? 'any'}
            onChange={(e) => setForm({ ...form, work_mode: e.target.value as WorkMode })}
          >
            <option value="any">Any</option>
            <option value="remote">Remote</option>
            <option value="hybrid">Hybrid</option>
            <option value="onsite">On-site</option>
          </Select>
          <div className="flex items-center gap-2 pt-6">
            <input
              id="reloc"
              type="checkbox"
              checked={Boolean(form.willing_to_relocate)}
              onChange={(e) => setForm({ ...form, willing_to_relocate: e.target.checked })}
            />
            <label htmlFor="reloc" className="text-sm font-medium">
              Willing to relocate
            </label>
          </div>
          <Input
            label="Expected Salary (LPA in ₹)"
            type="number"
            step="0.5"
            min="0"
            value={form.expected_salary_lpa ?? ''}
            onChange={(e) => setForm({ ...form, expected_salary_lpa: e.target.value ? Number(e.target.value) : null })}
          />
          <Input
            label="Minimum Acceptable Salary (LPA in ₹)"
            type="number"
            step="0.5"
            min="0"
            value={form.min_salary_lpa ?? ''}
            onChange={(e) => setForm({ ...form, min_salary_lpa: e.target.value ? Number(e.target.value) : null })}
          />
          <Select
            label="Preferred Course Learning Language"
            value={form.learning_language ?? 'en'}
            onChange={(e) => setForm({ ...form, learning_language: e.target.value as LangCode })}
          >
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.native} ({l.english})
              </option>
            ))}
          </Select>
        </Card>

        <Card className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-3">
            <h2 className="text-base font-semibold">Projects ({(form.projects ?? []).length})</h2>
            <Input label="Project Title" value={projTitle} onChange={(e) => setProjTitle(e.target.value)} />
            <Input label="Short Description" value={projDesc} onChange={(e) => setProjDesc(e.target.value)} />
            <Button type="button" variant="secondary" size="sm" onClick={addProject}>
              Add Project
            </Button>
            <ul className="space-y-1 text-xs text-slate-600 dark:text-slate-400">
              {(form.projects ?? []).map((p, idx) => (
                <li key={idx}>• {p.title}</li>
              ))}
            </ul>
          </div>

          <div className="space-y-3">
            <h2 className="text-base font-semibold">Certifications ({(form.certifications ?? []).length})</h2>
            <Input label="Certification Name" value={certName} onChange={(e) => setCertName(e.target.value)} />
            <Input label="Issuer" value={certIssuer} onChange={(e) => setCertIssuer(e.target.value)} />
            <Button type="button" variant="secondary" size="sm" onClick={addCert}>
              Add Certification
            </Button>
            <ul className="space-y-1 text-xs text-slate-600 dark:text-slate-400">
              {(form.certifications ?? []).map((c, idx) => (
                <li key={idx}>
                  • {c.name} {c.issuer ? `(${c.issuer})` : ''}
                </li>
              ))}
            </ul>
          </div>
        </Card>

        <div className="flex justify-end">
          <Button type="submit" disabled={saveMut.isPending}>
            {saveMut.isPending ? t('common.saving') : t('common.save')}
          </Button>
        </div>
      </form>
    </div>
  );
}
