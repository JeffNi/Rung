@echo off
cd /d C:\Users\Jeffn\Documents\Github\Rung
call venv\Scripts\activate
cd backend\voicedraft
uvicorn main:app --reload --host 0.0.0.0 --port 8000





