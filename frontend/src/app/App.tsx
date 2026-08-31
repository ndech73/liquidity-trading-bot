import { BrowserRouter } from 'react-router-dom'

export function App() {
  return (
    <BrowserRouter>
      <main className="min-h-screen bg-slate-950 text-slate-100 p-6">
        <h1 className="text-2xl font-semibold">Liquidity Trading System</h1>
        <p className="mt-2 text-slate-400">
          Analysis engine scaffold — connect routes and DXCharts next.
        </p>
      </main>
    </BrowserRouter>
  )
}
