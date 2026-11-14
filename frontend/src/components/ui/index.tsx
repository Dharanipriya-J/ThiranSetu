import { forwardRef, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Tone = 'neutral' | 'indigo' | 'teal' | 'amber' | 'rose' | 'emerald';

const BTN_STYLES: Record<Variant, string> = {
  primary: 'bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-indigo-400',
  secondary:
    'bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700',
  ghost: 'text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800',
  danger: 'bg-rose-600 text-white hover:bg-rose-700 disabled:bg-rose-400',
};

export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: 'sm' | 'md' }
>(({ variant = 'primary', size = 'md', className = '', children, ...rest }, ref) => (
  <button
    ref={ref}
    className={`inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors min-h-[44px] sm:min-h-[38px] ${
      size === 'sm' ? 'px-3 py-1.5 text-xs' : 'px-4 py-2 text-sm'
    } disabled:cursor-not-allowed disabled:opacity-60 ${BTN_STYLES[variant]} ${className}`}
    {...rest}
  >
    {children}
  </button>
));
Button.displayName = 'Button';

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <section
      className={`rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm ${className}`}
    >
      {children}
    </section>
  );
}

const BADGE_TONES: Record<Tone, string> = {
  neutral: 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200',
  indigo: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-200',
  teal: 'bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-200',
  amber: 'bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200',
  rose: 'bg-rose-100 text-rose-900 dark:bg-rose-950 dark:text-rose-200',
  emerald: 'bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200',
};

export function Badge({ children, tone = 'neutral', className = '' }: { children: ReactNode; tone?: Tone; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${BADGE_TONES[tone]} ${className}`}>
      {children}
    </span>
  );
}

export function Input({
  label,
  error,
  id,
  className = '',
  ...rest
}: InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string }) {
  const inputId = id ?? `in-${label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`;
  const errId = error ? `${inputId}-err` : undefined;
  return (
    <div className="space-y-1">
      <label htmlFor={inputId} className="block text-sm font-medium text-slate-700 dark:text-slate-200">
        {label}
      </label>
      <input
        id={inputId}
        aria-invalid={Boolean(error)}
        aria-describedby={errId}
        className={`w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 min-h-[42px] ${
          error ? 'border-rose-500' : ''
        } ${className}`}
        {...rest}
      />
      {error && (
        <p id={errId} role="alert" className="text-xs text-rose-600 dark:text-rose-400">
          {error}
        </p>
      )}
    </div>
  );
}

export function Select({
  label,
  error,
  id,
  children,
  className = '',
  ...rest
}: SelectHTMLAttributes<HTMLSelectElement> & { label: string; error?: string }) {
  const selectId = id ?? `sel-${label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`;
  const errId = error ? `${selectId}-err` : undefined;
  return (
    <div className="space-y-1">
      <label htmlFor={selectId} className="block text-sm font-medium text-slate-700 dark:text-slate-200">
        {label}
      </label>
      <select
        id={selectId}
        aria-invalid={Boolean(error)}
        aria-describedby={errId}
        className={`w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 min-h-[42px] ${className}`}
        {...rest}
      >
        {children}
      </select>
      {error && (
        <p id={errId} role="alert" className="text-xs text-rose-600 dark:text-rose-400">
          {error}
        </p>
      )}
    </div>
  );
}

export function TextArea({
  label,
  error,
  id,
  className = '',
  ...rest
}: TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string; error?: string }) {
  const areaId = id ?? `ta-${label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`;
  const errId = error ? `${areaId}-err` : undefined;
  return (
    <div className="space-y-1">
      <label htmlFor={areaId} className="block text-sm font-medium text-slate-700 dark:text-slate-200">
        {label}
      </label>
      <textarea
        id={areaId}
        aria-invalid={Boolean(error)}
        aria-describedby={errId}
        className={`w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 ${className}`}
        {...rest}
      />
      {error && (
        <p id={errId} role="alert" className="text-xs text-rose-600 dark:text-rose-400">
          {error}
        </p>
      )}
    </div>
  );
}

export function ProgressBar({ value, label }: { value: number; label?: string }) {
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div className="space-y-1">
      {label && (
        <div className="flex justify-between text-xs text-slate-600 dark:text-slate-400">
          <span>{label}</span>
          <span className="font-semibold text-slate-900 dark:text-slate-100">{pct}%</span>
        </div>
      )}
      <div
        className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"
        role="progressbar"
        aria-label={label ?? 'Progress'}
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="h-full rounded-full bg-indigo-600 dark:bg-indigo-500 transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Spinner({ label = 'Loading...' }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex items-center justify-center gap-3 py-12 text-sm text-slate-600 dark:text-slate-400">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-xl border border-rose-200 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/40 p-5 text-sm text-rose-800 dark:text-rose-200">
      <p className="font-medium">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry} className="mt-3">
          Retry
        </Button>
      )}
    </div>
  );
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-700 p-8 text-center">
      <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function DataNotice({ isDemo, label }: { isDemo?: boolean; label: string }) {
  if (!isDemo) return null;
  return (
    <Badge tone="amber" className="font-semibold">
      {label}
    </Badge>
  );
}
