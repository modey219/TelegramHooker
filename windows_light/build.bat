@echo off
echo ================================================
echo  Telegram Hooker - Light Edition Build Script
echo  @ASEQX12
echo ================================================
echo.

echo [1/3] Installing PyInstaller...
pip install pyinstaller --upgrade

echo [2/3] Building EXE...
pyinstaller --onefile --windowed --name "TelegramHooker_Light" --icon=..\icon.ico hooker_light.py

echo [3/3] Done!
echo.
echo EXE located at: dist\TelegramHooker_Light.exe
echo.
pause
