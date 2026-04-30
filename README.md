# Prescription Verifier

## Run the project

From the project root, start both the backend API and Streamlit frontend:

```powershell
cd "e:\Projects\gen ai\prescription-verifier"
.\run-project.ps1
```

The app will be available at:

- Backend API: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:8501`

## Run services separately

Start the backend API:

```powershell
cd "e:\Projects\gen ai\prescription-verifier"
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in another terminal:

```powershell
cd "e:\Projects\gen ai\prescription-verifier"
.\.venv\Scripts\python.exe -m streamlit run frontend\app.py --server.port 8501
```
