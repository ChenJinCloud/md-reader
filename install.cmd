@echo off
rem ============================================================
rem  MD Reader - register as .md handler (current user only)
rem
rem  Why this script exists:
rem  Windows 10/11's "Open With" dialog disables the "Always use
rem  this app" checkbox when you point at a .cmd batch file — they
rem  aren't proper Win32 apps. This script registers a ProgID
rem  (MDReader.Markdown) under HKCU that points directly at
rem  pythonw.exe + md-reader.pyw, which Windows recognizes as a
rem  real app. After running, right-click any .md file → Open With
rem  → Choose another app → MD Reader will appear, and the
rem  "Always" checkbox will be enabled.
rem
rem  All writes go under HKEY_CURRENT_USER. No admin required.
rem  Reversible: run `install.cmd /uninstall` to remove.
rem ============================================================

setlocal enabledelayedexpansion
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "PYW=%ROOT%\md-reader.pyw"
set "PROGID=MDReader.Markdown"

if /i "%~1"=="/uninstall" goto uninstall

rem ---------- Install ----------
if not exist "%PYW%" (
    echo ERROR: md-reader.pyw not found next to this script.
    echo Expected: %PYW%
    pause
    exit /b 1
)

rem Find pythonw.exe
set "PYTHONW="
for /f "delims=" %%i in ('where pythonw.exe 2^>nul') do (
    set "PYTHONW=%%i"
    goto pyfound
)
:pyfound
if "%PYTHONW%"=="" (
    echo ERROR: pythonw.exe not found in PATH.
    echo Install Python 3 from https://www.python.org/ and make sure
    echo pythonw.exe is on PATH ^(the installer's "Add Python to PATH"
    echo option does this^).
    pause
    exit /b 1
)

echo Registering MD Reader...
echo   ProgID  : %PROGID%
echo   pythonw : %PYTHONW%
echo   script  : %PYW%
echo.

rem ProgID friendly name
reg add "HKCU\Software\Classes\%PROGID%" /ve /d "Markdown Document" /f >nul
reg add "HKCU\Software\Classes\%PROGID%\DefaultIcon" /ve /d "\"%PYTHONW%\",0" /f >nul

rem Open verb: pythonw.exe "<script>" "%1"
reg add "HKCU\Software\Classes\%PROGID%\shell\open\command" /ve /d "\"%PYTHONW%\" \"%PYW%\" \"%%1\"" /f >nul

rem Expose to the .md extension's Open-With list
reg add "HKCU\Software\Classes\.md\OpenWithProgids" /v "%PROGID%" /t REG_NONE /f >nul

rem Also register under Applications\pythonw.exe so it shows up nicely
reg add "HKCU\Software\Classes\Applications\pythonw.exe\SupportedTypes" /v ".md" /t REG_SZ /d "" /f >nul

rem Notify shell to refresh icon/association cache
powershell -NoProfile -Command ^
  "$sig = '[DllImport(\"shell32.dll\")] public static extern void SHChangeNotify(int eventId, int flags, IntPtr item1, IntPtr item2);'; ^
   Add-Type -MemberDefinition $sig -Name Shell -Namespace Win32 -ErrorAction SilentlyContinue; ^
   [Win32.Shell]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)" >nul 2>&1

echo Done.
echo.
echo Next steps:
echo   1. Right-click any .md file
echo   2. "Open With" -^> "Choose another app"
echo   3. Scroll, pick "MD Reader" ^(or "Markdown Document"^)
echo   4. The "Always use this app" checkbox is now enabled — check it
echo.
pause
exit /b 0

rem ---------- Uninstall ----------
:uninstall
echo Unregistering MD Reader...
reg delete "HKCU\Software\Classes\%PROGID%" /f >nul 2>&1
reg delete "HKCU\Software\Classes\.md\OpenWithProgids" /v "%PROGID%" /f >nul 2>&1
reg delete "HKCU\Software\Classes\Applications\pythonw.exe\SupportedTypes" /v ".md" /f >nul 2>&1
echo.
echo Removed. Note: Windows may still remember "MD Reader" as a past
echo choice in the Open-With dialog's history list — that's a separate
echo cache cleared via Settings -^> Apps -^> Default apps -^> .md.
echo.
pause
exit /b 0
