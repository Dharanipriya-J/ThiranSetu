import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './locales/en.json';
import type { LangCode } from '../api/types';

export const LANGUAGES: { code: LangCode; native: string; english: string }[] = [
  { code: 'en', native: 'English', english: 'English' },
  { code: 'ta', native: 'தமிழ்', english: 'Tamil' },
  { code: 'hi', native: 'हिन्दी', english: 'Hindi' },
  { code: 'te', native: 'తెలుగు', english: 'Telugu' },
  { code: 'kn', native: 'ಕನ್ನಡ', english: 'Kannada' },
  { code: 'ml', native: 'മലയാളം', english: 'Malayalam' },
  { code: 'bn', native: 'বাংলা', english: 'Bengali' },
  { code: 'mr', native: 'मराठी', english: 'Marathi' },
];

export const LANG_STORAGE_KEY = 'ts_lang';

export function isLangCode(v: unknown): v is LangCode {
  return typeof v === 'string' && LANGUAGES.some((l) => l.code === v);
}

const localeLoaders = import.meta.glob<{ default: Record<string, unknown> }>(['./locales/*.json', '!./locales/en.json']);

/** Loads a locale bundle on demand (English is bundled), then switches to it. */
export async function changeAppLanguage(code: LangCode): Promise<void> {
  if (!i18n.hasResourceBundle(code, 'translation')) {
    const loader = localeLoaders[`./locales/${code}.json`];
    if (loader) {
      const mod = await loader();
      i18n.addResourceBundle(code, 'translation', mod.default, true, true);
    }
  }
  await i18n.changeLanguage(code);
  try {
    localStorage.setItem(LANG_STORAGE_KEY, code);
  } catch {
    /* storage unavailable */
  }
}

function initialLanguage(): LangCode {
  try {
    const stored = localStorage.getItem(LANG_STORAGE_KEY);
    if (isLangCode(stored)) return stored;
  } catch {
    /* ignore */
  }
  const nav = typeof navigator !== 'undefined' ? navigator.language.slice(0, 2) : 'en';
  return isLangCode(nav) ? nav : 'en';
}

i18n.on('languageChanged', (lng) => {
  if (typeof document !== 'undefined') document.documentElement.lang = lng;
});

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en } },
  lng: 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
  returnNull: false,
});

const start = initialLanguage();
if (start !== 'en') void changeAppLanguage(start);

export default i18n;
