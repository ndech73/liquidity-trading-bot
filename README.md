# Automated Liquidity Trading System

## Current architecture

Frontend:
- React
- TypeScript
- Vite
- Tailwind CSS
- DXCharts
- REST + WebSocket clients

Backend:
- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- Alembic
- Pydantic Settings
- Loguru
- PostgreSQL
- NumPy/Pandas

Trading:
- Analysis Engine
- Strategy Engine
- Risk Engine
- Execution Service -> MT5

Research:
- Backtesting
- Trade Forensics
- Chart Replay

## Development order

1. Install Node.js and Python.
2. Create the frontend with Vite/React/TypeScript.
3. Authenticate to the DXCharts private registry and install the licensed DXCharts packages.
4. Create the Python virtual environment.
5. Install backend dependencies.
6. Start PostgreSQL.
7. Configure `.env`.
8. Build the Analysis Engine first.
9. Build Strategy + Exit Engine.
10. Add Risk Engine.
11. Build backtesting and forensics.
12. Connect MT5 execution.
13. Build the full dashboard.
14. Demo-test before any live account.

## Important

The compression/expansion thresholds in this scaffold are research defaults, not validated trading rules.
Do not use the scaffold for live trading until the strategy has been tested and the execution/risk layers have been completed.
