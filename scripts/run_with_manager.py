#!/usr/bin/env python3
"""
Cron 任务包装器 - 与 TTS Manager 集成

用法:
    python run_with_manager.py <task_name> <command> [args...]

示例:
    python run_with_manager.py TTS-Daily-Crawl python papers/raw/tts-arxiv-daily/daily_arxiv.py --config_path papers/raw/tts-arxiv-daily/config.yaml
"""
import sys
import subprocess
import time
import os
from pathlib import Path

# 脚本位置: papers/scripts/run_with_manager.py
# 工作空间根目录: 向上两级

def run_command_with_tracking(task_name: str, command: str, args: list):
    """运行命令并跟踪状态到 TTS Manager"""

    # 获取 workspace 根目录 (假设脚本在 papers/scripts/ 下)
    script_dir = Path(__file__).parent.absolute()
    workspace_root = script_dir.parent.parent

    # 构建 manager 脚本路径
    manager_script = workspace_root / 'papers' / 'scripts' / 'tts_manager.py'

    start_time = time.time()

    # 1. 通知 manager 任务开始
    try:
        subprocess.run([
            sys.executable,
            str(manager_script),
            '--update-task', task_name, 'running'
        ], check=False, timeout=5)
    except Exception as e:
        print(f"[WARN] 无法通知 Manager 任务开始: {e}", file=sys.stderr)

    # 2. 执行实际命令
    try:
        # 在 workspace 根目录执行
        result = subprocess.run(
            [command] + args,
            cwd=workspace_root,
            capture_output=False,
            env={**os.environ, 'PYTHONPATH': str(workspace_root)}
        )
        duration_ms = int((time.time() - start_time) * 1000)
        exit_code = result.returncode

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        print(f"[ERROR] 任务执行异常: {e}", file=sys.stderr)
        exit_code = 1
        error_msg = str(e)

    # 3. 根据结果更新 manager
    try:
        if exit_code == 0:
            # 成功
            subprocess.run([
                sys.executable,
                str(manager_script),
                '--update-task', task_name, 'success', str(duration_ms)
            ], check=False, timeout=5)
        else:
            # 失败 - 需要获取错误信息
            # 如果是 subprocess.CalledProcessError, stderr 可能在 result.stderr
            error_msg = getattr(result, 'stderr', None)
            if error_msg:
                error_text = error_msg.decode('utf-8', errors='replace') if isinstance(error_msg, bytes) else str(error_msg)
            else:
                error_text = f"Exit code {exit_code}"

            subprocess.run([
                sys.executable,
                str(manager_script),
                '--update-task', task_name, 'failed', str(duration_ms), error_text[:200]
            ], check=False, timeout=5)
    except Exception as e:
        print(f"[WARN] 无法通知 Manager 任务结果: {e}", file=sys.stderr)

    # 4. 返回原命令的退出码
    sys.exit(exit_code)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: run_with_manager.py <task_name> <command> [args...]", file=sys.stderr)
        sys.exit(2)

    task_name = sys.argv[1]
    command = sys.argv[2]
    args = sys.argv[3:]

    run_command_with_tracking(task_name, command, args)
