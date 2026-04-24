# Compressor Lifetime v4

## Backend

```powershell
cd backend
python -m pip install -r requirements.txt
python run.py
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend environment variables:

```powershell
# frontend/.env.development
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_WS_BASE_URL=ws://127.0.0.1:8000
```

Frontend build and test:

```powershell
npm run build
npm run test
```

## Backend Test

```powershell
cd backend
python -m pip install -r requirements.txt
python -m pytest -q
```

Backend: `http://127.0.0.1:8000`  
Frontend: `http://127.0.0.1:5173`
