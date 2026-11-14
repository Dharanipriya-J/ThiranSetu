import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../hooks/useAuth';
import { errorMessage } from '../lib/errors';
import { Button, Card, Input } from '../components/ui';

export default function RegisterPage() {
  const { t } = useTranslation();
  const { register } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fieldErrs, setFieldErrs] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (fullName.trim().length < 2) errs.fullName = 'Full name must be at least 2 characters.';
    if (!email.includes('@')) errs.email = 'Enter a valid email address.';
    if (password.length < 8 || !/[a-zA-Z]/.test(password) || !/\d/.test(password)) {
      errs.password = 'Password must be 8+ characters with at least one letter and one digit.';
    }
    setFieldErrs(errs);
    setError('');
    if (Object.keys(errs).length > 0) return;

    setBusy(true);
    try {
      await register({ full_name: fullName.trim(), email: email.trim(), password });
      navigate('/profile', { replace: true });
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
          <h1 className="mt-2 text-2xl font-bold">{t('auth.registerTitle')}</h1>
        </div>

        {error && (
          <p role="alert" className="rounded-lg bg-rose-50 dark:bg-rose-950/50 p-3 text-sm text-rose-700 dark:text-rose-200">
            {error}
          </p>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <Input
            label={t('auth.fullName')}
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            error={fieldErrs.fullName}
            required
          />
          <Input
            label={t('auth.email')}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            error={fieldErrs.email}
            required
          />
          <Input
            label={t('auth.password')}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={fieldErrs.password}
            required
          />
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? t('common.loading') : t('common.register')}
          </Button>
        </form>

        <p className="text-sm text-slate-600 dark:text-slate-400">
          {t('auth.hasAccount')}{' '}
          <Link to="/login" className="font-semibold text-indigo-600 dark:text-indigo-400 hover:underline">
            {t('common.login')}
          </Link>
        </p>
      </Card>
    </div>
  );
}
