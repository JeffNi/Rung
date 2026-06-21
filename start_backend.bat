@echo off
cd /d C:\Users\Jeffn\Documents\Github\Rung
call venv\Scripts\activate
cd backend\coverletter
uvicorn main:app --reload --reload-dir . --reload-dir ..\resume --reload-dir ..\jobsearch --host 0.0.0.0 --port 8000






