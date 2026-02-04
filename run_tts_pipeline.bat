@echo off
REM TTS 论文自动处理 pipeline（跳过 LLM 分析）
REM 使用方法：直接运行此批处理文件，或添加到 Windows Task Scheduler

echo ========================================
echo TTS 论文自动处理 pipeline
echo 开始时间: %DATE% %TIME%
echo ========================================
echo.

REM 切换到脚本目录
cd /d "C:\Users\Administrator\.openclaw\workspace"

REM 运行 pipeline（跳过 LLM 分析以节省时间和配额）
python scripts\run_full_pipeline.py --skip-analysis
if ERRORLEVEL 1 (
    echo.
    echo ❌ Pipeline 执行失败
    echo 错误代码: %ERRORLEVEL%
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ✅ Pipeline 执行完成
echo 结束时间: %DATE% %TIME%
echo.
echo 报告位置:
echo   日报: papers\summaries\daily\
echo   周报: papers\summaries\weekly\
echo   月报: papers\summaries\monthly\
echo.
pause