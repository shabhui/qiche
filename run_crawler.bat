@echo off
chcp 65001 > nul
echo ========================================
echo   太平洋汽车网 数据爬虫
echo ========================================
echo.

REM 进入后端目录
cd /d "%~dp0backend"

REM 检查虚拟环境是否存在（.venv 或 venv）
if exist ".venv\Scripts\activate" (
    call .venv\Scripts\activate
) else if exist "venv\Scripts\activate" (
    call venv\Scripts\activate
) else (
    echo 未找到虚拟环境，将使用系统 Python。
)

REM 检查 scrapy 是否可用
where scrapy >nul 2>nul
if errorlevel 1 (
    echo 错误：未找到 scrapy，请先安装依赖：pip install -r requirements.txt
    pause
    exit /b 1
)

echo 开始运行爬虫轿车榜
scrapy crawl pcauto

echo.
echo 爬取完成！数据已保存到 data/pcauto.db
echo 按任意键退出...
pause > nul