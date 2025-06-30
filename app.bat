@echo off



chcp 65001 >nul



cd /d "%~dp0"



echo [ bat ] The path configuration file is being generated...
if exist "env\ltai\python.exe" (
    env\ltai\python.exe path_location.py
) else (
    echo [ bat ] Error: The path of python.exe was not found!
    exit /b 1
)



set "file=cmd_app"
if not exist "%file%" (
    echo [ bat ] Error: file %file% does not exist!
    exit /b 1
)

set /p cmd_line=<"%file%"
if "%cmd_line%"=="" (
    echo [ bat ] Error: file %file% is empty!
    exit /b 1
)



echo [ bat ] The command being executed: %cmd line%
%cmd_line%


echo [ bat ] All operations have been completed.

