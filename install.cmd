@echo off
rem ============================================================
rem  MD Reader - register .exe as .md handler (current user only)
rem
rem  Why this script exists:
rem  Windows 10/11's "Open With" dialog disables the "Always use
rem  this app" checkbox for .cmd/.bat files — they aren't proper
rem  Win32 apps. Earlier versions registered pythonw.exe + the
rem  .pyw script, but once a stale UserChoice hash gets stuck
rem  Windows refuses to accept that path either. The current
rem  build ships a PyInstaller-made md-reader.exe and registers
rem  a ProgID under HKCU pointing at that real PE executable.
rem  After running, right-click any .md file → Open With → MD
rem  Reader will appear and the "Always" checkbox is enabled.
rem
rem  All writes go under HKEY_CURRENT_USER. No admin required.
rem  Reversible: run `install.cmd /uninstall` to remove.
rem ============================================================

setlocal enabledelayedexpansion
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "EXE=%ROOT%\dist\md-reader.exe"
set "PROGID=MDReader.Markdown"

if /i "%~1"=="/uninstall" goto uninstall

rem ---------- Install ----------
if not exist "%EXE%" (
    echo ERROR: md-reader.exe not found.
    echo Expected: %EXE%
    echo.
    echo If you cloned from source, make sure the repo's dist\ folder
    echo contains md-reader.exe. Rebuild with PyInstaller if needed:
    echo   pyinstaller --onefile --windowed md-reader.pyw
    pause
    exit /b 1
)

echo Registering MD Reader...
echo   ProgID : %PROGID%
echo   exe    : %EXE%
echo.

rem ProgID friendly name + icon
reg add "HKCU\Software\Classes\%PROGID%" /ve /d "Markdown Document" /f >nul
reg add "HKCU\Software\Classes\%PROGID%\DefaultIcon" /ve /d "\"%EXE%\",0" /f >nul

rem Open verb: md-reader.exe "%1"
reg add "HKCU\Software\Classes\%PROGID%\shell\open\command" /ve /d "\"%EXE%\" \"%%1\"" /f >nul

rem Expose to the .md extension's Open-With list
reg add "HKCU\Software\Classes\.md\OpenWithProgids" /v "%PROGID%" /t REG_NONE /f >nul

rem Register under Applications\md-reader.exe so it appears in Open-With
reg add "HKCU\Software\Classes\Applications\md-reader.exe\shell\open\command" /ve /d "\"%EXE%\" \"%%1\"" /f >nul
reg add "HKCU\Software\Classes\Applications\md-reader.exe\SupportedTypes" /v ".md" /t REG_SZ /d "" /f >nul
reg add "HKCU\Software\Classes\Applications\md-reader.exe\FriendlyAppName" /ve /d "MD Reader" /f >nul

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
reg delete "HKCU\Software\Classes\Applications\md-reader.exe" /f >nul 2>&1
echo.
echo Removed. Note: Windows may still remember "MD Reader" as a past
echo choice in the Open-With dialog's history list — that's a separate
echo cache cleared via Settings -^> Apps -^> Default apps -^> .md.
echo.
pause
exit /b 0
