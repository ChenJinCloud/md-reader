@echo off
rem MD Reader launcher
rem Usage: md-reader.cmd "path\to\file.md"
rem Associate this file with .md via "Open With" in Explorer/Everything.
if "%~1"=="" (
  echo Usage: %~nx0 "path\to\file.md"
  pause
  exit /b 1
)
start "" pythonw "%~dp0md-reader.pyw" "%~f1"
exit /b 0
