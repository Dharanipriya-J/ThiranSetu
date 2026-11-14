import { useQuery } from '@tanstack/react-query';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useTranslation } from 'react-i18next';
import { api } from '../api/client';
import { errorMessage } from '../lib/errors';
import { Badge, Card, DataNotice, ErrorState, PageHeader, Spinner } from '../components/ui';

export default function MarketPage() {
  const { t } = useTranslation();
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['market'], queryFn: api.market });

  if (isLoading) return <Spinner label={t('common.loading')} />;
  if (error || !data) return <ErrorState message={errorMessage(error, t)} onRetry={() => void refetch()} />;

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('nav.market')}
        subtitle={`${data.data_source.label} · ${data.data_source.vacancies_analyzed} vacancies analysed · As of ${data.data_source.as_of}`}
        actions={<DataNotice isDemo={data.data_source.is_demo} label={t('common.demoData')} />}
      />

      <Card className="space-y-4">
        <h2 className="text-base font-semibold">Most Requested Skills Across Vacancies</h2>
        <div className="h-72 w-full" aria-hidden="true">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.top_skills.slice(0, 8)} margin={{ top: 10, right: 16, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
              <XAxis dataKey="skill" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="mandatory_count" stackId="a" fill="#4f46e5" name="Mandatory" />
              <Bar dataKey="preferred_count" stackId="a" fill="#0d9488" name="Preferred" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <details className="text-xs">
          <summary className="cursor-pointer font-semibold text-indigo-600 dark:text-indigo-400">
            Accessible Table Alternative (Screen-Reader Friendly)
          </summary>
          <table className="mt-2 w-full text-left">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800">
                <th className="py-1">Skill</th>
                <th className="py-1">Vacancies</th>
                <th className="py-1">Share</th>
                <th className="py-1">Mandatory / Preferred</th>
              </tr>
            </thead>
            <tbody>
              {data.top_skills.map((s) => (
                <tr key={s.skill} className="border-b border-slate-100 dark:border-slate-900">
                  <td className="py-1 font-medium">{s.skill}</td>
                  <td className="py-1">{s.demand_count}</td>
                  <td className="py-1">{s.share_percent}%</td>
                  <td className="py-1">
                    {s.mandatory_count} / {s.preferred_count}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="space-y-2">
          <h2 className="font-semibold">Role Demand Breakdown</h2>
          {data.role_demand.map((r) => (
            <div key={r.role_id} className="flex justify-between text-sm">
              <span>{r.title}</span>
              <Badge tone="indigo">{r.vacancies} openings</Badge>
            </div>
          ))}
        </Card>

        <Card className="space-y-2">
          <h2 className="font-semibold">Stable Foundational Skills</h2>
          <div className="flex flex-wrap gap-2">
            {data.stable.map((s) => (
              <Badge key={s} tone="teal">
                {s}
              </Badge>
            ))}
          </div>
          <p className="pt-2 text-xs text-slate-600 dark:text-slate-400">
            Scope: {data.data_source.scope}. {data.notes.join(' ')}
          </p>
        </Card>
      </div>
    </div>
  );
}
