@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Сборка MIDI Макросы ===
set "PY="
py -3.12 --version >nul 2>nul && set "PY=py -3.12"
if not defined PY py -3.11 --version >nul 2>nul && set "PY=py -3.11"
if not defined PY (
  echo ОШИБКА: нужен Python 3.12 - новые версии пока не поддерживают MIDI-библиотеку.
  echo Скачай Python 3.12 с python.org - Windows installer 64-bit, поставь галочку Add python.exe to PATH.
  start https://www.python.org/downloads/release/python-31210/
  pause
  exit /b 1
)
if not defined PY python --version >nul 2>nul && set "PY=python"
if not defined PY (
  echo ОШИБКА: Python не найден.
  echo 1. Перезагрузи компьютер после установки Python и запусти build.bat снова.
  echo 2. Если не помогло: переустанови Python с python.org, галочка Add python.exe to PATH.
  echo 3. Параметры - Приложения - Псевдонимы выполнения приложений: выключи python.exe и python3.exe.
  pause
  exit /b 1
)
echo Python найден: %PY%
if exist .venv rmdir /s /q .venv
%PY% -m venv .venv || (echo Не удалось создать venv & pause & exit /b 1)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller pytest || (pause & exit /b 1)
python -m pytest -q tests || (echo Тесты упали & pause & exit /b 1)
pyinstaller --noconfirm --onefile --collect-all vosk --hidden-import sounddevice --windowed --name ArturiaMidiMacros --paths app ^
  --hidden-import mido.backends.rtmidi --hidden-import rtmidi --collect-submodules pycaw --collect-submodules comtypes ^
  app\main.py || (pause & exit /b 1)
echo.
echo Готово: dist\ArturiaMidiMacros.exe
pause
