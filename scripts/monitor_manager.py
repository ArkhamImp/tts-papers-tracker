#!/usr/bin/env python3
"""
TTS Manager 监控和自动重启脚本

功能:
1. 检查 TTS Manager subagent 是否在运行
2. 如果停止,自动重启
3. 记录监控日志

用法:
    python monitor_manager.py [--force-restart]

配置建议: 通过 cron 每 5-10 分钟运行一次
"""
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime, timedelta

# workspace 根目录 (假设脚本在 papers/scripts/ 下)
SCRIPT_DIR = Path(__file__).parent.absolute()
WORKSPACE_ROOT = SCRIPT_DIR.parent.parent

# Manager 状态文件
STATE_FILE = WORKSPACE_ROOT / 'papers' / 'processed' / 'pipeline_state.json'
MONITOR_LOG = WORKSPACE_ROOT / 'papers' / 'processed' / 'manager_monitor.log'

def log(message: str):
    """写入监控日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}\n"
    with open(MONITOR_LOG, 'a', encoding='utf-8') as f:
        f.write(log_entry)
    print(log_entry.strip())

def check_manager_alive():
    """检查 Manager 是否存活"""
    if not STATE_FILE.exists():
        log("状态文件不存在")
        return False, "状态文件不存在"

    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)

        # 检查最后心跳时间
        if 'last_health_check' in state:
            last_check_str = state['last_health_check']
            log(f"最后心跳时间: {last_check_str}")
            # 解析带时区的时间字符串
            try:
                if '+' in last_check_str or last_check_str.endswith('Z'):
                    last_check = datetime.fromisoformat(last_check_str.replace('Z', '+00:00'))
                else:
                    # 如果是无时区的字符串,假设它是本地时间
                    last_check = datetime.fromisoformat(last_check_str)

                now = datetime.now(last_check.tzinfo if last_check.tzinfo else None)
                delta = now - last_check
                log(f"当前时间: {now}, 时间差: {delta}")

                # 如果超过 5 分钟没有心跳,认为 manager 已死
                if delta > timedelta(minutes=5):
                    return False, f"最后心跳: {last_check}, 已超过 5 分钟"
            except Exception as e:
                log(f"时间解析错误: {e}")
                return False, f"时间解析失败: {e}"
        else:
            log("状态文件中没有 last_health_check 字段")
            return False, "状态文件中没有 last_health_check 字段"

        log("Manager 运行正常")
        return True, "Manager 运行正常"
    except Exception as e:
        log(f"读取状态文件失败: {e}")
        return False, f"读取状态文件失败: {e}"

def restart_manager():
    """重启 TTS Manager"""
    log("正在重启 TTS Manager...")

    try:
        # 通过 tasklist 查找并终止旧进程
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/V'],
            capture_output=True, text=True, timeout=5
        )
        old_pid = None
        for line in result.stdout.split('\n'):
            if 'tts_manager.py' in line:
                parts = line.split()
                if len(parts) >= 2:
                    old_pid = parts[1]
                break

        if old_pid:
            log(f"发现旧 manager 进程 PID: {old_pid}, 正在终止...")
            subprocess.run(['taskkill', '/F', '/PID', old_pid], capture_output=True, timeout=5)
            log("旧进程已终止")

        # 启动新进程 (无窗口后台运行)
        log("启动新的 manager 进程...")
        manager_script = WORKSPACE_ROOT / 'papers' / 'scripts' / 'tts_manager.py'

        # 在 Windows 上使用 CREATE_NO_WINDOW 避免弹出控制台窗口
        creationflags = 0
        if sys.platform == 'win32':
            creationflags = subprocess.CREATE_NO_WINDOW

        subprocess.Popen([
            sys.executable, str(manager_script)
        ], creationflags=creationflags, close_fds=True)

        log("TTS Manager 已重启")
        return True
    except Exception as e:
        log(f"重启失败: {e}")
        return False

def main():
    force_restart = '--force-restart' in sys.argv

    if force_restart:
        log("强制重启模式")
        success = restart_manager()
        log(f"强制重启结果: {'成功' if success else '失败'}")
        sys.exit(0 if success else 1)

    # 检查 manager 状态
    alive, reason = check_manager_alive()

    if alive:
        log(f"Manager 状态正常: {reason}")
        sys.exit(0)
    else:
        log(f"Manager 异常: {reason}")
        log("正在自动重启...")
        success = restart_manager()
        log(f"自动重启结果: {'成功' if success else '失败'}")
        sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
