# Backend (FastAPI)

Run in development:

```powershell
python -m pip install -r requirements.txt
python run.py
```

Optional host/port overrides:

```powershell
$env:COMPRESSOR_API_HOST="0.0.0.0"
$env:COMPRESSOR_API_PORT="8000"
python run.py
```

Run tests:

```powershell
python -m pytest -q
```
