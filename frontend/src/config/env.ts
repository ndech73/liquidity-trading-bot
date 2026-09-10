const getApiUrl = (): string => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  if (typeof window !== 'undefined') {
    const host = window.location.hostname || '127.0.0.1';
    return `${window.location.protocol}//${host}:8000/api`;
  }
  return 'http://127.0.0.1:8000/api';
};

const getWsUrl = (): string => {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname || '127.0.0.1';
    return `${protocol}//${host}:8000/ws`;
  }
  return 'ws://127.0.0.1:8000/ws';
};

export const ENV = {
  API_URL: getApiUrl(),
  WS_URL: getWsUrl(),
  IS_DEV: import.meta.env.DEV,
  IS_PROD: import.meta.env.PROD,
} as const;

