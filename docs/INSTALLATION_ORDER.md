# Installation order

## 0. System prerequisites

Recommended:
- Node.js LTS
- npm
- Python 3.11+
- PostgreSQL
- Git

## 1. Frontend

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install react-router-dom axios
npm install tailwindcss @tailwindcss/vite
```

DXCharts is distributed by Devexperts through a private Nexus npm registry or ZIP. Authenticate to the registry first, then install the licensed packages:

```bash
npm login --registry=https://repo.devexperts.com/repository/dxcharts/
npm install @dx-private/dxchart5-modules
npm install @dx-private/dxstudies
npm install @dx-private/dxchart5-react
```

Then:

```bash
npm run dev
```

## 2. Backend

```bash
cd ../backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create `.env` from `.env.example`.

Start:

```bash
uvicorn app.main:app --reload --port 8000
```

## 3. Database

For development:

```bash
docker compose up -d postgres
```

Then configure `DATABASE_URL` and later run:

```bash
alembic upgrade head
```

## 4. MT5 execution environment

Do not install MT5 into the analysis layer just because the bot uses MT5.

Keep it behind `execution/mt5_executor.py`.

MetaQuotes documents the `MetaTrader5` Python package as an interprocess connection to the MT5 terminal and documents `pip install MetaTrader5`. Their official examples/setup target Windows. If the final execution host is Linux, validate the terminal/Python integration in that environment before production; a Windows execution host is the simpler path. The analysis/backtesting system can remain ordinary Python and does not need MT5.

## 5. Test

```bash
pytest
```
