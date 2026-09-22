@echo off
title Processos Tracker - Loop Continuo
cd /d "%~dp0"
echo Iniciando verificacao automatica a cada 6 horas...
python processos_tracker.py --loop 6h
pause