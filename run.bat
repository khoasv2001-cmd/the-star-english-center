@echo off
cd /d "%~dp0"
if not exist venv (
    echo Tao moi truong ao...
    python -m venv venv
)
call venv\Scripts\activate
echo Cai dat thu vien...
pip install -r requirements.txt
echo.
echo ============================================
echo  THE STAR ENGLISH CENTER - dang chay
echo  Mo trinh duyet: http://127.0.0.1:5000
echo  Dang nhap: admin / admin123
echo ============================================
python app.py
pause
