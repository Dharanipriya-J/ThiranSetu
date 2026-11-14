import '@testing-library/jest-dom/vitest';

const store = new Map<string, string>();
const memoryStorage: Storage = {
  get length() {
    return store.size;
  },
  clear: () => store.clear(),
  getItem: (k: string) => store.get(k) ?? null,
  key: (i: number) => Array.from(store.keys())[i] ?? null,
  removeItem: (k: string) => {
    store.delete(k);
  },
  setItem: (k: string, v: string) => {
    store.set(k, String(v));
  },
};
Object.defineProperty(globalThis, 'localStorage', { value: memoryStorage, configurable: true });
Object.defineProperty(window, 'localStorage', { value: memoryStorage, configurable: true });

if (typeof window !== 'undefined' && !('ResizeObserver' in window)) {
  (window as unknown as { ResizeObserver: unknown }).ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
