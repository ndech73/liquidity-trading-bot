export function connectMarketSocket() {
  const url = import.meta.env.VITE_WS_URL
  return new WebSocket(url)
}
