#!/usr/bin/env python3
"""
完整的 TTS 论文处理 pipeline
整合：更新论文列表 -> 解析分类 -> 抓取摘要 -> 分析论文 -> 生成日报/周报/月报

用法:
  python run_full_pipeline.py [--skip-analysis] [--date YYYY-MM-DD]

选项:
  --skip-analysis   跳过 LLM 分析步骤（加快速度）
  --date DATE       指定生成日报的日期（默认：最新日期）
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import argparse

# 基于脚本位置的路径配置
SCRIPT_DIR = Path(__file__).parent
RAW_DIR = SCRIPT_DIR.parent / "raw" / "tts-arxiv-daily"
PROCESSED_DIR = SCRIPT_DIR.parent / "processed"
BY_DATE_DIR = PROCESSED_DIR / "by-date"
DAILY_SUMMARIES_DIR = SCRIPT_DIR.parent / "summaries" / "daily"
WEEKLY_SUMMARIES_DIR = SCRIPT_DIR.parent / "summaries" / "weekly"
MONTHLY_SUMMARIES_DIR = SCRIPT_DIR.parent / "summaries" / "monthly"

# 确保目录存在
for dir_path in [PROCESSED_DIR, BY_DATE_DIR, DAILY_SUMMARIES_DIR, WEEKLY_SUMMARIES_DIR, MONTHLY_SUMMARIES_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

def run_command(cmd, description):
    """运行子命令并返回成功/失败状态"""
    print(f"\n执行: {description}")
    print(f"命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"失败: {description}")
        print(f"错误输出: {result.stderr}")
        return False
    print(f"成功: {description}")
    return True

def step1_update_paper_list():
    """步骤1: 从 arxiv 更新论文列表"""
    daily_arxiv_script = RAW_DIR / "daily_arxiv.py"
    config_file = RAW_DIR / "config.yaml"
    # 设置工作目录为 RAW_DIR，确保相对路径正确
    result = subprocess.run([sys.executable, str(daily_arxiv_script), "--config_path", str(config_file)],
                          capture_output=True, text=True, cwd=str(RAW_DIR))
    if result.returncode != 0:
        print(f"失败: 更新论文列表")
        print(f"STDERR: {result.stderr}")
        return False
    print(f"成功: 论文列表更新完成")
    return True

def step2_parse_and_classify():
    """步骤2: 解析并分类论文"""
    parse_script = SCRIPT_DIR / "parse_tts_papers.py"
    return run_command([sys.executable, str(parse_script)], "解析并分类论文")

def step3_fetch_abstracts():
    """步骤3: 抓取论文摘要"""
    fetch_script = SCRIPT_DIR / "fetch_abstracts.py"
    return run_command([sys.executable, str(fetch_script)], "抓取论文摘要")

def step4_analyze_papers():
    """步骤4: LLM 分析论文 (可选)"""
    # 检查配置
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        print("警告: 未找到配置文件，跳过论文分析")
        return True

    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    if "deepseek" not in cfg.get("models", {}).get("providers", {}):
        print("警告: 未配置 DeepSeek provider，跳过论文分析")
        return True

    print("开始分析论文 (可能需要较长时间，且消耗 API 配额)...")
    analyze_script = SCRIPT_DIR / "analyze_papers.py"
    return run_command([sys.executable, str(analyze_script)], "LLM 论文分析")

def step5_generate_summaries(target_date=None):
    """步骤5: 生成日报、周报、月报"""
    print("\n生成日报、周报、月报...")

    # 获取可用的日期列表
    all_dates = []
    for f in BY_DATE_DIR.glob("*.md"):
        try:
            d = datetime.strptime(f.stem, "%Y-%m-%d").date()
            all_dates.append(d)
        except:
            continue
    all_dates.sort(reverse=True)

    if not all_dates:
        print("错误: 未找到按日期分类的论文文件")
        return False

    # 确定日报日期
    if target_date:
        try:
            report_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            if report_date not in all_dates:
                print(f"警告: 指定日期 {target_date} 没有论文数据，将使用最新日期 {all_dates[0]}")
                report_date = all_dates[0]
        except ValueError:
            print(f"错误: 日期格式不正确，应为 YYYY-MM-DD")
            return False
    else:
        report_date = all_dates[0]

    # 生成日报
    print(f"\n生成日报: {report_date}")
    daily_script = SCRIPT_DIR / "daily_tts_papers.py"
    success = run_command([sys.executable, str(daily_script), str(report_date)], f"日报生成 ({report_date})")

    # 生成周报
    recent_dates = all_dates[:7] if len(all_dates) >= 7 else all_dates
    if recent_dates:
        print(f"\n生成周报: {recent_dates[-1]} 至 {recent_dates[0]}")
        weekly_script = SCRIPT_DIR / "generate_weekly_summary.py"
        success &= run_command([sys.executable, str(weekly_script)], "周报生成")

    # 生成月报
    current_month = datetime.now().strftime("%Y-%m")
    print(f"\n生成月报: {current_month}")
    monthly_script = SCRIPT_DIR / "generate_monthly_summary.py"
    success &= run_command([sys.executable, str(monthly_script), current_month], "月报生成")

    return success

def check_prerequisites():
    """检查前置条件"""
    print("检查前置条件...")

    # 检查原始数据目录
    if not RAW_DIR.exists():
        print(f"错误: 原始数据目录不存在: {RAW_DIR}")
        return False

    # 检查 README.md
    readme = RAW_DIR / "README.md"
    if not readme.exists():
        print(f"错误: README.md 不存在: {readme}")
        print("请先运行 daily_arxiv.py 生成论文列表")
        return False

    print("前置条件检查通过")
    return True

def main():
    parser = argparse.ArgumentParser(description="TTS 论文完整处理 pipeline")
    parser.add_argument("--skip-analysis", action="store_true", help="跳过 LLM 分析步骤")
    parser.add_argument("--date", help="指定日报日期 (格式: YYYY-MM-DD)")
    args = parser.parse_args()

    print("="*60)
    print("TTS 论文完整 pipeline")
    print("="*60)
    start_time = datetime.now()
    print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # 检查前置条件
    if not check_prerequisites():
        return 1

    # 定义执行步骤
    steps = [
        step1_update_paper_list,
        step2_parse_and_classify,
        step3_fetch_abstracts,
    ]

    if not args.skip_analysis:
        steps.append(step4_analyze_papers)
    else:
        print("提示: 使用 --skip-analysis 跳过 LLM 分析")

    steps.append(lambda: step5_generate_summaries(args.date))

    # 执行步骤
    results = []
    for step in steps:
        try:
            success = step()
            results.append(success)
            if not success:
                print("步骤失败，停止执行")
                break
        except KeyboardInterrupt:
            print("\n用户中断执行")
            break
        except Exception as e:
            print(f"异常: {e}")
            results.append(False)

    # 总结
    end_time = datetime.now()
    duration = end_time - start_time

    print("\n" + "="*60)
    print("Pipeline 执行总结")
    print("="*60)
    print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总耗时: {duration}")
    print(f"完成步骤: {sum(results)}/{len(results)}")

    if all(results):
        print("\n所有步骤成功完成！")
        print(f"报告位置:")
        print(f"  日报: {DAILY_SUMMARIES_DIR}")
        print(f"  周报: {WEEKLY_SUMMARIES_DIR}")
        print(f"  月报: {MONTHLY_SUMMARIES_DIR}")
        return 0
    else:
        print("\n部分步骤失败，请检查上述错误信息")
        return 1

if __name__ == "__main__":
    sys.exit(main())