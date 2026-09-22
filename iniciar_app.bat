@echo off
title Processos Tracker
echo Iniciando a interface do Processos Tracker...
cd /d "%~dp0"
streamlit run app.py
pause