@echo off
:: 设置代码页为 UTF-8
chcp 65001 >nul

:: 设置工作目录为当前脚本所在目录
cd /d "%~dp0"

:: Step 1: 生成路径信息文件 path_location.json，生成cmd_app 文件以启动 命令行菜单
echo [ bat ] The path configuration file is being generated...
if exist "env\ltai\python.exe" (
    env\ltai\python.exe path_location.py
) else (
    echo [ bat ] Error: The path of python.exe was not found!
    exit /b 1
)

:: Step 2: 从 cmd_app 文件中读取要执行的命令
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

:: Step 3: 执行命令
echo [ bat ] The command being executed: %cmd line%
%cmd_line%

echo [ bat ] All operations have been completed.

