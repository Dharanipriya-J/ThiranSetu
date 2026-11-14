import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../api/client';
import type { AssessmentResult, AssessmentSession, Level } from '../api/types';
import { errorMessage } from '../lib/errors';
import { Badge, Button, Card, ErrorState, Input, PageHeader, Select, Spinner } from '../components/ui';

export default function AssessmentsPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [params] = useSearchParams();
  const initialSkill = params.get('skill') ?? '';

  const availQ = useQuery({ queryKey: ['assessments-available'], queryFn: api.availableAssessments });
  const verifiedQ = useQuery({ queryKey: ['verified-skills'], queryFn: api.verifiedSkills });
  const historyQ = useQuery({ queryKey: ['assessment-history'], queryFn: api.assessmentHistory });

  const [selectedSkill, setSelectedSkill] = useState(initialSkill);
  const [level, setLevel] = useState<Level>('intermediate');
  const [session, setSession] = useState<AssessmentSession | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<AssessmentResult | null>(null);
  const [errMsg, setErrMsg] = useState('');

  const startMut = useMutation({
    mutationFn: ({ skill, lvl }: { skill: string; lvl: Level }) => api.startAssessment(skill, lvl),
    onSuccess: (s) => {
      setSession(s);
      setAnswers({});
      setResult(null);
      setErrMsg('');
    },
    onError: (err) => setErrMsg(errorMessage(err, t)),
  });

  const submitMut = useMutation({
    mutationFn: () => api.submitAssessment(session!.attempt_id, answers),
    onSuccess: (res) => {
      setResult(res);
      setSession(null);
      void qc.invalidateQueries({ queryKey: ['verified-skills'] });
      void qc.invalidateQueries({ queryKey: ['assessment-history'] });
      void qc.invalidateQueries({ queryKey: ['dashboard'] });
      setErrMsg('');
    },
    onError: (err) => setErrMsg(errorMessage(err, t)),
  });

  if (availQ.isLoading) return <Spinner label={t('common.loading')} />;
  if (availQ.error) return <ErrorState message={errorMessage(availQ.error, t)} />;

  const available = availQ.data ?? [];
  const activeSkill = selectedSkill || (available[0]?.skill ?? 'Python');

  function handleStart(e: FormEvent) {
    e.preventDefault();
    startMut.mutate({ skill: activeSkill, lvl: level });
  }

  return (
    <div className="space-y-6">
      <PageHeader title={t('assessments.title')} subtitle={t('assessments.subtitle')} />

      {errMsg && (
        <p role="alert" className="rounded-lg bg-rose-50 dark:bg-rose-950/50 p-3 text-sm text-rose-700 dark:text-rose-200">
          {errMsg}
        </p>
      )}

      {!session && (
        <Card>
          <form onSubmit={handleStart} className="flex flex-wrap items-end gap-4">
            <div className="min-w-[200px] flex-1">
              <Select label="Skill" value={activeSkill} onChange={(e) => setSelectedSkill(e.target.value)}>
                {available.map((a) => (
                  <option key={a.skill} value={a.skill}>
                    {a.skill} ({a.question_count} questions)
                  </option>
                ))}
              </Select>
            </div>
            <div className="min-w-[180px]">
              <Select label="Difficulty Level" value={level} onChange={(e) => setLevel(e.target.value as Level)}>
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </Select>
            </div>
            <Button type="submit" disabled={startMut.isPending}>
              {startMut.isPending ? t('common.loading') : t('assessments.start')}
            </Button>
          </form>
        </Card>
      )}

      {session && (
        <Card className="space-y-6">
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
            <h2 className="text-lg font-semibold">
              {session.skill} — <span className="capitalize">{session.level}</span> Assessment
            </h2>
            <Badge tone="indigo">{session.questions.length} Questions</Badge>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              submitMut.mutate();
            }}
            className="space-y-6"
          >
            {session.questions.map((q, idx) => (
              <fieldset key={q.id} className="space-y-2 rounded-lg border border-slate-200 dark:border-slate-800 p-4">
                <legend className="px-1 text-sm font-semibold">
                  Q{idx + 1}. [{q.topic} · {q.type}] {q.prompt}
                </legend>
                {q.code && (
                  <pre className="overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">{q.code}</pre>
                )}
                {q.options ? (
                  <div className="space-y-2 pt-1">
                    {q.options.map((opt) => (
                      <label key={opt} className="flex items-center gap-2.5 text-sm cursor-pointer">
                        <input
                          type="radio"
                          name={q.id}
                          value={opt}
                          checked={answers[q.id] === opt}
                          onChange={() => setAnswers({ ...answers, [q.id]: opt })}
                        />
                        <span>{opt}</span>
                      </label>
                    ))}
                  </div>
                ) : (
                  <Input
                    label="Your Output Answer"
                    placeholder="Type exact output..."
                    value={answers[q.id] ?? ''}
                    onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
                  />
                )}
              </fieldset>
            ))}

            <div className="flex gap-3">
              <Button type="submit" disabled={submitMut.isPending}>
                {submitMut.isPending ? t('common.loading') : t('assessments.submit')}
              </Button>
              <Button type="button" variant="secondary" onClick={() => setSession(null)}>
                {t('common.cancel')}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {result && (
        <Card className="space-y-4 border-indigo-300 dark:border-indigo-800">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-bold">
              {result.skill} Result: {result.score}% ({result.correct}/{result.total} correct)
            </h2>
            <Badge tone="teal">
              Verified Proficiency: {result.verified_score}% ({result.proficiency})
            </Badge>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 text-sm">
            <div>
              <strong>{t('assessments.strongTopics')}:</strong>{' '}
              {result.strong_topics.length ? result.strong_topics.join(', ') : 'None yet'}
            </div>
            <div>
              <strong>{t('assessments.weakTopics')}:</strong>{' '}
              {result.weak_topics.length ? result.weak_topics.join(', ') : 'None'}
            </div>
          </div>
          <ul className="list-disc pl-5 text-sm text-slate-700 dark:text-slate-300">
            {result.recommendations.map((rec, i) => (
              <li key={i}>{rec}</li>
            ))}
          </ul>
          <div className="space-y-2 pt-2">
            <h3 className="text-sm font-semibold">Answer Review & Explanations</h3>
            {result.review.map((rv) => (
              <div
                key={rv.question_id}
                className={`rounded-lg p-3 text-xs ${
                  rv.correct
                    ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-900 dark:text-emerald-100'
                    : 'bg-rose-50 dark:bg-rose-950/40 text-rose-900 dark:text-rose-100'
                }`}
              >
                <p className="font-semibold">{rv.prompt}</p>
                <p className="mt-1">
                  Your answer: <strong>{rv.your_answer || '(blank)'}</strong> · Correct: <strong>{rv.correct_answer}</strong>
                </p>
                <p className="mt-1 opacity-90">{rv.explanation}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card className="space-y-3">
        <h2 className="text-base font-semibold">{t('assessments.verifiedTable')}</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 dark:border-slate-800 text-xs uppercase text-slate-500">
              <tr>
                <th className="py-2 pr-4">Skill</th>
                <th className="py-2 pr-4">{t('assessments.selfReported')}</th>
                <th className="py-2 pr-4">{t('assessments.verifiedScore')}</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4">Weak Topics</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              {(verifiedQ.data ?? []).map((v) => (
                <tr key={v.skill}>
                  <td className="py-2.5 pr-4 font-medium">{v.skill}</td>
                  <td className="py-2.5 pr-4 capitalize">{v.self_reported_level ?? '—'}</td>
                  <td className="py-2.5 pr-4">{v.verified_score !== null ? `${v.verified_score}% (${v.proficiency})` : 'Not Assessed'}</td>
                  <td className="py-2.5 pr-4">
                    <Badge tone={v.verified_score !== null ? 'emerald' : 'amber'}>{v.status}</Badge>
                  </td>
                  <td className="py-2.5 pr-4 text-xs text-slate-600 dark:text-slate-400">
                    {v.weak_topics.length ? v.weak_topics.join(', ') : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card className="space-y-3">
        <h2 className="text-base font-semibold">{t('assessments.history')}</h2>
        {(historyQ.data ?? []).length === 0 ? (
          <p className="text-sm text-slate-600 dark:text-slate-400">No assessments completed yet.</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {(historyQ.data ?? []).map((h) => (
              <li key={h.attempt_id} className="flex items-center justify-between rounded-lg bg-slate-50 dark:bg-slate-800/50 px-3 py-2">
                <span>
                  <strong>{h.skill}</strong> ({h.level})
                </span>
                <span>
                  <strong>{h.score}%</strong> · {new Date(h.completed_at).toLocaleDateString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
