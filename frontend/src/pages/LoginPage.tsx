import { useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../hooks/useAuth';
import { errorMessage } from '../lib/errors';
import { Button, Card, Input } from '../components/ui';

export default function LoginPage() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const expired = Boolean((location.state as { expired?: boolean } | null)?.expired);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    if (!email.includes('@') || !password) {
      setError('Please enter a valid email and password.');
      return;
    }
    setBusy(true);
    try {
      await login({ email: email.trim(), password });
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(errorMessage(err, t));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 p-4">
      <Card className="w-full max-w-md space-y-5">
        <div>
          <Link to="/" className="text-sm font-semibold text-indigo-600 dark:text-indigo-400">
            {t('brand')}
          </Link>
          <h1 className="mt-2 text-2xl font-bold">{t('auth.loginTitle')}</h1>
        </div>

        {expired && (
          <p role="status" className="rounded-lg bg-amber-50 dark:bg-amber-950/50 p-3 text-sm text-amber-800 dark:text-amber-200">
            {t('auth.sessionExpired')}
          </p>
        )}
        {error && (
          <p role="alert" className="rounded-lg bg-rose-50 dark:bg-rose-950/50 p-3 text-sm text-rose-700 dark:text-rose-200">
            {error}
          </p>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <Input label={t('auth.email')} type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <Input label={t('auth.password')} type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? t('common.loading') : t('common.login')}
          </Button>
        </form>

        <p className="text-sm text-slate-600 dark:text-slate-400">
          {t('auth.noAccount')}{' '}
          <Link to="/register" className="font-semibold text-indigo-600 dark:text-indigo-400 hover:underline">
            {t('common.register')}
          </Link>
        </p>
      </Card>
    </div>
  );
}
