// 05-api.md, "Polling": 3 s por padrão.
export const POLL_INTERVAL_MS =
  Number(import.meta.env.VITE_POLL_INTERVAL_MS) || 3000
