# AquaHealthOS Demo (Option A stack)

## Stack
- Frontend: Next.js (Vercel)
- Backend: FastAPI (Render)
- DB: Supabase Postgres
- Alerts: dashboard-only

## Local run (fast)
### 1) Backend
cd backend
cp .env.example .env
# set DATABASE_URL to your Supabase Postgres URI
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

### 2) Frontend
cd ../frontend
cp .env.example .env.local
npm install
npm run dev
# open http://localhost:3000

### 3) Simulator (generates live data)
cd ../simulator
cp .env.example .env
pip install -r requirements.txt
python simulate.py
