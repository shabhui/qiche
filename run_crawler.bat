@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo   太平洋汽车网 数据爬虫
echo ========================================
echo.

REM 获取当前脚本所在目录（项目根目录）
set "PROJECT_ROOT=%~dp0"
set "BACKEND_DIR=%PROJECT_ROOT%backend"

REM 切换到 backend 目录（爬虫项目所在位置）
cd /d "%BACKEND_DIR%"

echo 正在运行爬虫，请稍候...
echo 抓取轿车榜和SUV榜，每个车型最多5页评论...
echo.

REM 运行 Scrapy 爬虫
scrapy crawl pcauto

REM 检查爬虫是否成功
if errorlevel 1 (
    echo.
    echo [错误] 爬虫运行失败，请检查网络或 Scrapy 安装。
    pause
    exit /b 1
)

echo.
echo 爬虫运行完成，正在整理数据库文件...

REM 将爬虫生成的数据库复制到项目根目录的 data 文件夹
if exist "%BACKEND_DIR%\data\pcauto.db" (
    REM 确保目标目录存在
    if not exist "%PROJECT_ROOT%data" mkdir "%PROJECT_ROOT%data"
    REM 复制并覆盖
    copy /Y "%BACKEND_DIR%\data\pcauto.db" "%PROJECT_ROOT%data\pcauto.db" >nul
    echo [成功] 数据库已更新到：%PROJECT_ROOT%data\pcauto.db
) else (
    echo [警告] 未找到爬虫生成的数据库文件（%BACKEND_DIR%\data\pcauto.db）
    echo 请检查爬虫是否正常抓取到数据。
)

REM 可选：删除 backend 下多余的数据库文件（保留干净）
del /Q "%BACKEND_DIR%\data\pcauto.db" 2>nul

echo.
echo 所有操作完成！按任意键退出...
pause >nul
exit /b 0