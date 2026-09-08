@echo off
echo ======================================================
echo   TEKNOFEST 2026 - Akilli Fabrika Windows Kurulumu
echo ======================================================

echo.
echo [1/3] Python kontrol ediliyor...
python --version
if errorlevel 1 (
    echo [HATA] Python bulunamadi! Lutfen Python 3 kurun ve PATH'e ekleyin.
    pause
    exit /b 1
)

echo.
echo [2/3] Sanal ortam (venv) olusturuluyor...
if not exist "venv" (
    python -m venv venv
    echo Sanal ortam olusturuldu.
) else (
    echo Mevcut sanal ortam kullaniliyor.
)

call venv\Scripts\activate.bat

echo.
echo [3/3] Paketler yukleniyor (requirements.txt)...
pip install --upgrade pip --quiet
pip install -r requirements.txt

echo.
echo ======================================================
echo   KURULUM BASARIYLA TAMAMLANDI!
echo ======================================================
pause
