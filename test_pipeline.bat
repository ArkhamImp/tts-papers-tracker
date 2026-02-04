@echo off
echo 开始测试 pipeline...
echo.

echo === 步骤 1: 更新论文列表 ===
cd papers\raw\tts-arxiv-daily
python daily_arxiv.py --config_path config.yaml
if errorlevel 1 (
    echo 失败: 更新论文列表
    pause
    exit /b 1
)
echo 成功: 论文列表更新完成
echo.

cd ..\..\..
echo === 步骤 2: 解析并分类论文 ===
python papers\scripts\parse_tts_papers.py
if errorlevel 1 (
    echo 失败: 解析分类
    pause
    exit /b 1
)
echo 成功: 论文解析分类完成
echo.

echo === 步骤 3: 抓取论文摘要 ===
python papers\scripts\fetch_abstracts.py
if errorlevel 1 (
    echo 失败: 抓取摘要
    pause
    exit /b 1
)
echo 成功: 摘要抓取完成
echo.

echo === 步骤 4: 生成日报 ===
python papers\scripts\daily_tts_papers.py 2026-02-02
if errorlevel 1 (
    echo 失败: 生成日报
    pause
    exit /b 1
)
echo 成功: 日报生成完成
echo.

echo === 所有步骤完成 ===
pause