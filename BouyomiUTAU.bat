@echo off
cd /d "%~dp0"
pythonw -m bouyomi_utau
if errorlevel 1 python -m bouyomi_utau
