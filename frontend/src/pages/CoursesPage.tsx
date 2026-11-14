import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { api } from '../api/client';
import type { CourseEquivalents, CourseQuery, LangCode } from '../api/types';
import { LANGUAGES } from '../i18n';
import { errorMessage } from '../lib/errors';
import { safeUrl as safeHttpUrl } from '../lib/format';
import { Badge, Button, Card, EmptyState, ErrorState, Input, PageHeader, Select, Spinner } from '../components/ui';

export default function CoursesPage() {
  const { t, i18n } = useTranslation();
  const [filters, setFilters] = useState<CourseQuery>({ page: 1, page_size: 12 });
  const [equivTargetLang, setEquivTargetLang] = useState<LangCode>((i18n.language as LangCode) || 'ta');
  const [equivResult, setEquivResult] = useState<CourseEquivalents | null>(null);

  const recQ = useQuery({ queryKey: ['recommended-courses'], queryFn: api.recommendedCourses });
  const catQ = useQuery({ queryKey: ['courses', filters], queryFn: () => api.courses(filters) });

  const equivMut = useMutation({
    mutationFn: ({ id, lang }: { id: string | number; lang: LangCode }) => api.courseEquivalents(id, lang),
    onSuccess: (res) => setEquivResult(res),
  });

  if (catQ.isLoading) return <Spinner label={t('common.loading')} />;
  if (catQ.error) return <ErrorState message={errorMessage(catQ.error, t)} />;

  return (
    <div className="space-y-6">
      <PageHeader title={t('courses.title')} subtitle="Curated learning resources matched to your verified skill gaps." />

      {(recQ.data ?? []).length > 0 && (
        <Card className="space-y-4">
          <h2 className="text-base font-semibold">{t('courses.recommended')}</h2>
          <div className="grid gap-4 md:grid-cols-2">
            {recQ.data!.map((grp) => (
              <div key={grp.skill} className="rounded-lg border border-slate-200 dark:border-slate-800 p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-sm">{grp.skill}</span>
                  <span className="text-xs text-slate-500">{grp.reason}</span>
                </div>
                {grp.courses.map((c) => {
                  const url = safeHttpUrl(c.url);
                  return (
                    <div key={c.id} className="flex items-center justify-between gap-2 text-xs">
                      <span>
                        {c.title} ({c.platform} · {c.language.toUpperCase()} · {c.price.label})
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

      <Card className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
        <Input
          label="Search / Skill"
          placeholder="Python, SQL, React..."
          value={filters.q ?? ''}
          onChange={(e) => setFilters({ ...filters, q: e.target.value, page: 1 })}
        />
        <Select label="Platform" value={filters.platform ?? ''} onChange={(e) => setFilters({ ...filters, platform: e.target.value, page: 1 })}>
          <option value="">All Platforms</option>
          <option value="NPTEL">NPTEL</option>
          <option value="Coursera">Coursera</option>
          <option value="edX">edX</option>
          <option value="Udemy">Udemy</option>
          <option value="YouTube">YouTube</option>
        </Select>
        <Select label="Course Language" value={filters.language ?? ''} onChange={(e) => setFilters({ ...filters, language: e.target.value, page: 1 })}>
          <option value="">Any Language</option>
          {LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.native} ({l.english})
            </option>
          ))}
        </Select>
        <Select label="Subtitle Language" value={filters.subtitle_language ?? ''} onChange={(e) => setFilters({ ...filters, subtitle_language: e.target.value, page: 1 })}>
          <option value="">Any Subtitles</option>
          {LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.native}
            </option>
          ))}
        </Select>
        <Select label="Price" value={filters.price ?? ''} onChange={(e) => setFilters({ ...filters, price: e.target.value as 'free' | 'paid' | '', page: 1 })}>
          <option value="">Free & Paid</option>
          <option value="free">{t('courses.freeOnly')}</option>
          <option value="paid">Paid</option>
        </Select>
        <Select
          label="Verification"
          value={filters.verified_only ? 'verified' : 'all'}
          onChange={(e) => setFilters({ ...filters, verified_only: e.target.value === 'verified', page: 1 })}
        >
          <option value="all">All Catalogue Entries</option>
          <option value="verified">Verified Direct URLs Only</option>
        </Select>
        <Select label="Equivalence Target" value={equivTargetLang} onChange={(e) => setEquivTargetLang(e.target.value as LangCode)}>
          {LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.native} ({l.english})
            </option>
          ))}
        </Select>
      </Card>

      {equivResult && (
        <Card className="space-y-3 border-teal-300 dark:border-teal-800">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold">
              Syllabus-Verified Equivalents for "{equivResult.course.title}" ({equivResult.language.toUpperCase()})
            </h2>
            <Button size="sm" variant="ghost" onClick={() => setEquivResult(null)}>
              Close
            </Button>
          </div>
          {equivResult.equivalents.length === 0 ? (
            <p className="text-sm text-slate-600 dark:text-slate-400">
              No syllabus-verified equivalent found in {equivResult.language.toUpperCase()} yet.
            </p>
          ) : (
            <div className="space-y-2">
              {equivResult.equivalents.map((eq) => (
                <div key={eq.course.id} className="rounded-lg bg-teal-50 dark:bg-teal-950/30 p-3 text-xs space-y-1">
                  <div className="flex items-center justify-between font-semibold">
                    <span>
                      {eq.course.title} ({eq.course.platform})
                    </span>
                    <Badge tone={eq.equivalence_status === 'potential_skill_overlap' ? 'amber' : 'teal'}>
                      {eq.overlap_percent}% {eq.equivalence_status === 'potential_skill_overlap' ? 'skill overlap' : 'syllabus overlap'}
                    </Badge>
                  </div>
                  <p>{eq.verdict}</p>
                  <p>Shared outcomes: {eq.shared_outcomes.join(', ') || eq.shared_skills.join(', ')}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {catQ.data?.items.length === 0 && (
        <EmptyState
          title="No verified courses matched"
          description={catQ.data.availability_note || 'No courses matched your current filters. Try clearing a filter.'}
          action={
            <Button variant="secondary" onClick={() => setFilters({ page: 1, page_size: 12 })}>
              {t('common.reset')}
            </Button>
          }
        />
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {(catQ.data?.items ?? []).map((c) => {
          const url = safeHttpUrl(c.url);
          return (
            <Card key={c.id} className="flex flex-col justify-between space-y-3">
              <div className="space-y-2">
                <div className="flex flex-wrap gap-1.5">
                  <Badge tone="indigo">{c.platform}</Badge>
                  <Badge tone={c.price.is_free ? 'emerald' : 'amber'}>{c.price.label}</Badge>
                  <Badge tone="neutral">Teach: {c.language.toUpperCase()}</Badge>
                  <Badge tone={url && c.is_verified !== false ? 'teal' : 'amber'}>
                    {url && c.is_verified !== false ? 'Verified Direct URL' : 'URL Pending Verification'}
                  </Badge>
                </div>
                <h3 className="font-semibold text-sm">{c.title}</h3>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  {c.provider} · {c.difficulty} · {c.duration_hours ?? '—'}h
                </p>
                <p className="text-xs">
                  <strong>Skills:</strong> {c.skills.join(', ')}
                </p>
                <p className="text-xs text-slate-500">
                  Audio: {(c.audio_languages || [c.language]).join(', ').toUpperCase()} · Subtitles:{' '}
                  {c.subtitle_languages.join(', ').toUpperCase()} · Rating:{' '}
                  {c.rating ? `${c.rating.value} (${c.rating.source})` : t('common.notVerified')}
                </p>
              </div>
              <div className="flex flex-wrap gap-2 pt-2 items-center">
                {url ? (
                  <a href={url} target="_blank" rel="noopener noreferrer">
                    <Button size="sm">Open Course</Button>
                  </a>
                ) : (
                  <span className="text-xs text-slate-500 dark:text-slate-400">Direct URL pending verification</span>
                )}
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => equivMut.mutate({ id: c.id, lang: equivTargetLang })}
                >
                  {t('courses.findEquivalent')}
                </Button>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
