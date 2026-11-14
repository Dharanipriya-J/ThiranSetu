import type { TFunction } from 'i18next';
import { ApiError } from '../api/client';

/** Turns any thrown value into a user-friendly, translated message. */
export function errorMessage(err: unknown, t: TFunction): string {
  if (err instanceof ApiError) {
    switch (err.kind) {
      case 'network':
        return t('errors.network');
      case 'server':
        return t('errors.server');
      case 'rate_limit':
        return err.retryAfter ? t('errors.rateLimitRetry', { seconds: err.retryAfter }) : t('errors.rateLimit');
      case 'unauthorized':
        return err.detail ?? t('errors.unauthorized');
      case 'validation':
        return err.detail ?? t('errors.validation');
      case 'not_found':
        return err.detail ?? t('errors.notFound');
      default:
        return err.detail ?? t('errors.generic');
    }
  }
  return t('errors.generic');
}

/** Field-level errors from a 422 response, keyed by the last path segment. */
export function fieldErrors(err: unknown): Record<string, string> {
  if (!(err instanceof ApiError) || err.kind !== 'validation') return {};
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(err.fieldErrors)) {
    const last = k.split('.').pop() ?? k;
    out[last] = v;
  }
  return out;
}
