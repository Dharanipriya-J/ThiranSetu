import { useState, type FormEvent } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { api } from '../api/client';
import type { LangCode, MentorReply } from '../api/types';
import { errorMessage } from '../lib/errors';
import { Badge, Button, Card, Input, PageHeader } from '../components/ui';

interface ChatTurn {
  role: 'user' | 'assistant';
  text: string;
  meta?: MentorReply;
}

export default function MentorPage() {
  const { t, i18n } = useTranslation();
  const [input, setInput] = useState('');
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [errMsg, setErrMsg] = useState('');

  const sugQ = useQuery({ queryKey: ['mentor-suggestions'], queryFn: api.mentorSuggestions });

  const chatMut = useMutation({
    mutationFn: (msg: string) => api.mentorChat(msg, (i18n.language as LangCode) || 'en'),
    onSuccess: (reply) => {
      setTurns((prev) => [...prev, { role: 'assistant', text: reply.reply, meta: reply }]);
      setErrMsg('');
    },
    onError: (err) => setErrMsg(errorMessage(err, t)),
  });

  function sendMessage(msg: string) {
    const clean = msg.trim();
    if (!clean || chatMut.isPending) return;
    setTurns((prev) => [...prev, { role: 'user', text: clean }]);
    setInput('');
    chatMut.mutate(clean);
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    sendMessage(input);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('mentor.title')}
        subtitle="Grounded in your verified skills, career rankings, company vacancies, salary fit, and roadmap."
      />

      {(sugQ.data ?? []).length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase text-slate-500">{t('mentor.suggestions')}</p>
          <div className="flex flex-wrap gap-2">
            {sugQ.data!.map((s) => (
              <Button key={s} size="sm" variant="secondary" onClick={() => sendMessage(s)}>
                {s}
              </Button>
            ))}
          </div>
        </div>
      )}

      <Card className="space-y-4">
        <div role="log" aria-live="polite" className="min-h-[260px] max-h-[460px] overflow-y-auto space-y-3 pr-1">
          {turns.length === 0 && (
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Ask a question or pick one of the suggestions above to get personalized career guidance.
            </p>
          )}
          {turns.map((turn, idx) => (
            <div
              key={idx}
              className={`rounded-xl p-3.5 text-sm ${
                turn.role === 'user'
                  ? 'ml-auto max-w-[85%] bg-indigo-600 text-white'
                  : 'mr-auto max-w-[90%] bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100'
              }`}
            >
              <p className="whitespace-pre-wrap">{turn.text}</p>
              {turn.meta && (
                <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px] opacity-80">
                  <Badge tone={turn.meta.mode === 'gemini' ? 'emerald' : 'amber'}>
                    {turn.meta.mode === 'gemini' ? t('common.geminiMode') : t('common.deterministicMode')}
                  </Badge>
                  <span>Sources: {turn.meta.sources.join(', ')}</span>
                </div>
              )}
            </div>
          ))}
          {chatMut.isPending && (
            <p role="status" className="text-xs text-slate-500">
              {t('common.loading')}
            </p>
          )}
        </div>

        {errMsg && (
          <p role="alert" className="text-xs text-rose-600 dark:text-rose-400">
            {errMsg}
          </p>
        )}

        <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-2">
          <div className="flex-1 min-w-[220px]">
            <Input
              label={t('mentor.title')}
              placeholder={t('mentor.placeholder')}
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
          </div>
          <Button type="submit" disabled={chatMut.isPending || !input.trim()}>
            {t('mentor.send')}
          </Button>
        </form>
      </Card>
    </div>
  );
}
