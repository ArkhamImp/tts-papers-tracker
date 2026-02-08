#!/usr/bin/env python3
"""
TTS Pipeline Manager - 持续运行的子代理

负责监控、协调和管理整个 TTS 论文跟踪管道系统。

启动方式:
    守护进程模式:
        python papers/scripts/tts_manager.py --daemon

    健康检查:
        python papers/scripts/tts_manager.py --health

    状态查询:
        python papers/scripts/tts_manager.py --status

    任务状态更新:
        python papers/scripts/tts_manager.py --update-task <task_name> <status> [duration_ms] [error]

作者: ArkhamImp
日期: 2026-02-06
"""

import json
import logging
import os
import sys
import time
import signal
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess
from dataclasses import dataclass, asdict
from enum import Enum

# 确保路径正确
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# 添加项目路径到 sys.path
sys.path.insert(0, str(PROJECT_ROOT))

# ============= 配置和常量 =============

STATE_FILE = PROJECT_ROOT / "papers" / "processed" / "pipeline_state.json"
LOG_FILE = PROJECT_ROOT / "papers" / "processed" / "tts_manager.log"
CHECK_INTERVAL = 60  # 检查间隔(秒)
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2

class TaskStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    RUNNING = "running"
    SKIPPED = "skipped"
    UNKNOWN = "unknown"

@dataclass
class TaskRecord:
    """单个任务的执行记录"""
    name: str
    last_run: Optional[str]  # ISO 8601 时间戳
    last_status: str  # TaskStatus 值
    last_duration: Optional[int]  # 毫秒
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    retry_count: int = 0

@dataclass
class PipelineState:
    """管道整体状态"""
    manager_start_time: str
    tasks: Dict[str, TaskRecord]
    total_runs: int = 0
    total_successes: int = 0
    total_failures: int = 0
    last_health_check: Optional[str] = None
    alerts_suppressed_until: Optional[str] = None

# ============= 日志设置 =============

def setup_logging():
    """配置日志系统"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ============= 状态管理 =============

class StateManager:
    """状态文件管理器"""

    def __init__(self, state_path: Path):
        self.state_path = state_path
        self.state = self._load_or_init()

    def _load_or_init(self) -> PipelineState:
        """加载或初始化状态"""
        if self.state_path.exists():
            try:
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # 重建 TaskRecord 对象
                tasks = {
                    name: TaskRecord(**record)
                    for name, record in data.get('tasks', {}).items()
                }
                return PipelineState(**{**data, 'tasks': tasks})
            except Exception as e:
                logger.error(f"加载状态文件失败: {e}, 将创建新状态")

        # 初始化新状态
        now = datetime.now().astimezone().isoformat()
        return PipelineState(
            manager_start_time=now,
            tasks={},
            last_health_check=now
        )

    def save(self):
        """保存状态到文件"""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self.state)
        with open(self.state_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def update_task(self, task_name: str, status: TaskStatus,
                   duration: Optional[int] = None, error: Optional[str] = None):
        """更新任务记录"""
        now_iso = datetime.now().astimezone().isoformat()

        if task_name in self.state.tasks:
            task = self.state.tasks[task_name]
        else:
            # 创建新任务记录,使用默认值
            task = TaskRecord(
                name=task_name,
                last_run=now_iso,
                last_status=TaskStatus.UNKNOWN.value,
                last_duration=None,
                consecutive_failures=0,
                last_error=None,
                retry_count=0
            )

        # 更新计数
        if status == TaskStatus.SUCCESS:
            self.state.total_successes += 1
        elif status == TaskStatus.FAILED:
            self.state.total_failures += 1
            task.consecutive_failures += 1
            task.last_error = error
        else:
            task.consecutive_failures = 0
            task.last_error = None

        task.last_run = now_iso
        task.last_status = status.value
        task.last_duration = duration

        self.state.tasks[task_name] = task
        self.state.total_runs += 1
        self.save()

    def get_task(self, task_name: str) -> Optional[TaskRecord]:
        return self.state.tasks.get(task_name)

# ============= 任务监控 =============

class TaskMonitor:
    """任务监控器"""

    def __init__(self, state_manager: StateManager):
        self.state = state_manager

    def check_cron_jobs(self) -> List[Dict[str, Any]]:
        """通过查询 OpenClaw cron 作业状态来检查任务"""
        # 这里需要调用 OpenClaw API 或读取 cron 状态
        # 简化实现: 假设任务执行会留下标记文件
        results = []

        expected_tasks = [
            "TTS-Daily-Crawl",
            "TTS-Papers-Crawl",
            "TTS-Papers-Analysis",
            "TTS-Daily-Summary",
            "Git-Push-Daily"
        ]

        for task_name in expected_tasks:
            record = self.state.get_task(task_name)
            if record:
                results.append({
                    "task": task_name,
                    "last_run": record.last_run,
                    "status": record.last_status,
                    "consecutive_failures": record.consecutive_failures
                })
            else:
                results.append({
                    "task": task_name,
                    "status": "never_run"
                })

        return results

    def check_data_freshness(self) -> Dict[str, Any]:
        """检查数据新鲜度"""
        data_dir = PROJECT_ROOT / "papers" / "processed"
        freshness = {}

        # 检查最近的数据文件
        daily_md = data_dir / "daily" / "latest.md"
        if daily_md.exists():
            mtime = datetime.fromtimestamp(daily_md.stat().st_mtime).astimezone()
            now = datetime.now().astimezone()
            age_hours = (now - mtime).total_seconds() / 3600
            freshness["daily_report"] = {
                "file": str(daily_md),
                "age_hours": round(age_hours, 2),
                "fresh": age_hours < 24
            }

        return freshness

# ============= 主管理器 =============

class TTSManager:
    """TTS 管道管理器"""

    def __init__(self):
        self.state_manager = StateManager(STATE_FILE)
        self.monitor = TaskMonitor(self.state_manager)
        self.running = True
        self.last_check = datetime.now().astimezone()
        self.last_heartbeat = datetime.now().astimezone()

        # 设置信号处理
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        logger.info("TTS Manager 初始化完成")
        logger.info(f"状态文件: {STATE_FILE}")
        logger.info(f"检查间隔: {CHECK_INTERVAL} 秒")

        # 保存初始状态到磁盘
        self.state_manager.save()
        logger.info("初始状态已保存")

    def _handle_shutdown(self, signum, frame):
        """优雅关闭"""
        logger.info(f"收到信号 {signum}, 正在关闭...")
        self.running = False

    def run_health_check(self) -> Dict[str, Any]:
        """执行健康检查,返回详细报告"""
        logger.info("执行健康检查...")

        cron_status = self.monitor.check_cron_jobs()
        data_freshness = self.monitor.check_data_freshness()

        # 计算统计信息
        total_runs = self.state_manager.state.total_runs
        total_successes = self.state_manager.state.total_successes
        success_rate = (total_successes / total_runs * 100) if total_runs > 0 else 0

        # 识别失败任务
        failed_tasks = [t for t in cron_status if t["status"] == TaskStatus.FAILED.value]

        now = datetime.now().astimezone()  # local timezone-aware
        start_time = datetime.fromisoformat(
            self.state_manager.state.manager_start_time.replace('Z', '+00:00')
        ).astimezone()
        report = {
            "timestamp": now.isoformat(),
            "manager_uptime": str(now - start_time),
            "statistics": {
                "total_runs": total_runs,
                "total_successes": total_successes,
                "total_failures": self.state_manager.state.total_failures,
                "success_rate_percent": round(success_rate, 2)
            },
            "cron_tasks": cron_status,
            "data_freshness": data_freshness,
            "alerts": {
                "failed_tasks_count": len(failed_tasks),
                "stale_data": [k for k, v in data_freshness.items() if not v.get("fresh", True)],
                "needs_attention": len(failed_tasks) > 0 or any(not v.get("fresh", True) for v in data_freshness.values())
            }
        }

        self.state_manager.state.last_health_check = report["timestamp"]
        self.state_manager.save()

        return report

    def format_health_report(self, report: Dict[str, Any]) -> str:
        """将健康报告格式化为可读文本 (GBK安全,无emoji)"""
        lines = [
            "[TTS Pipeline Health Report]",
            "=" * 40,
            f"[Time] {report['timestamp']}",
            f"[Manager Uptime] {report['manager_uptime']}",
            "",
            "[Statistics]",
            f"   Total runs: {report['statistics']['total_runs']}",
            f"   Successes: {report['statistics']['total_successes']}",
            f"   Failures: {report['statistics']['total_failures']}",
            f"   Success rate: {report['statistics']['success_rate_percent']}%",
            "",
            "[Task Status]"
        ]

        for task in report["cron_tasks"]:
            status_marker = "[OK]" if task["status"] == TaskStatus.SUCCESS.value else \
                           "[FAIL]" if task["status"] == TaskStatus.FAILED.value else \
                           "[RUN]" if task["status"] == TaskStatus.RUNNING.value else "[??]"
            lines.append(f"   {status_marker} {task['task']}: {task['status']}")
            if task.get("last_run"):
                lines.append(f"      Last run: {task['last_run']}")
            if task.get("consecutive_failures", 0) > 0:
                lines.append(f"      [!] Consecutive failures: {task['consecutive_failures']} times")

        if report["data_freshness"]:
            lines.append("")
            lines.append("[Data Freshness]")
            for key, info in report["data_freshness"].items():
                freshness_marker = "[FRESH]" if info["fresh"] else "[STALE]"
                lines.append(f"   {freshness_marker} {key}: {info['age_hours']} hours ago")

        alerts = report["alerts"]
        lines.append("")
        lines.append("[Alerts]")
        if alerts["needs_attention"]:
            lines.append(f"   [!] Failed tasks needing attention: {alerts['failed_tasks_count']}")
            lines.append(f"   [!] Stale data items: {len(alerts['stale_data'])}")
            lines.append("   [CRITICAL] System status: Needs attention")
        else:
            lines.append("   [OK] All systems operational")

        lines.append("=" * 40)
        return "\n".join(lines)

        return "\n".join(lines)

    def handle_system_event(self, event_text: str) -> str:
        """处理系统事件(健康检查请求等)"""
        logger.info(f"收到系统事件: {event_text[:100]}")

        event_lower = event_text.lower()

        if "health" in event_lower or "status" in event_lower or "check" in event_lower:
            report = self.run_health_check()
            return self.format_health_report(report)
        elif "retry" in event_lower:
            # TODO: 实现重试逻辑
            return "[WAIT] 重试功能尚未实现"
        elif "trigger" in event_lower:
            # TODO: 实现手动触发逻辑
            return "[WAIT] 手动触发功能尚未实现"
        else:
            return "[TTS Manager] 在线。状态: 运行中。\n输入 'health' 或 'status' 获取详细信息。"

    def run(self):
        """主事件循环"""
        logger.info("TTS Manager 已启动,进入主循环...")
        logger.info("等待系统事件和定期检查...")

        # 立即更新一次心跳,表明自己活着
        self._update_heartbeat()

        while self.running:
            try:
                current_time = datetime.now().astimezone()

                # 每分钟执行一次被动检查
                if (current_time - self.last_check).total_seconds() >= CHECK_INTERVAL:
                    logger.debug("执行定期检查...")
                    # 这里可以添加被动检查逻辑,如验证文件存在性等
                    self.last_check = current_time

                # 每 60 秒主动更新一次心跳,表明自己还活着
                if (current_time - self.last_heartbeat).total_seconds() >= 60:
                    self._update_heartbeat()

                # 短暂休眠,减少 CPU 占用
                time.sleep(1)

            except Exception as e:
                logger.error(f"主循环异常: {e}", exc_info=True)
                time.sleep(5)  # 异常后等待更长时间

        logger.info("TTS Manager 已关闭")

    def _update_heartbeat(self):
        """主动更新心跳时间戳"""
        self.last_heartbeat = datetime.now().astimezone()
        self.state_manager.state.last_health_check = self.last_heartbeat.isoformat()
        try:
            self.state_manager.save()
            logger.debug(f"心跳已更新: {self.state_manager.state.last_health_check}")
        except Exception as e:
            logger.error(f"更新心跳失败: {e}")

# ============= 入口点 =============

def main():
    """主函数 - 支持守护进程模式和 CLI 命令"""
    import argparse

    parser = argparse.ArgumentParser(description="TTS Pipeline Manager")
    parser.add_argument("--daemon", action="store_true", help="启动守护进程模式 (默认)")
    parser.add_argument("--health", action="store_true", help="执行健康检查并输出报告")
    parser.add_argument("--status", action="store_true", help="输出状态 JSON")
    parser.add_argument("--update-task", nargs="+", metavar="ARGS", help="更新任务状态: <task_name> <status> [duration_ms] [error]")
    parser.add_argument("--test", action="store_true", help="测试运行: 初始化并立即退出")
    parser.add_argument("--model", type=str, default=None, help="指定使用的模型 (用于子进程调用)")

    args = parser.parse_args()

    # 如果没有参数,默认启动 daemon
    if not any([args.daemon, args.health, args.status, args.update_task, args.test, args.model]):
        args.daemon = True

    try:
        manager = TTSManager()

        if args.test:
            print("[INFO] Manager 初始化成功 (测试模式)", flush=True)
            manager.state_manager.save()
            print("[INFO] 状态文件已保存", flush=True)
            return

        if args.update_task:
            # 更新任务状态: --update-task <task_name> <status> [duration] [error]
            task_name = args.update_task[0]
            status = args.update_task[1]
            duration = int(args.update_task[2]) if len(args.update_task) > 2 else None
            error = args.update_task[3] if len(args.update_task) > 3 else None
            manager.state_manager.update_task(task_name, TaskStatus(status), duration, error)
            print(f"[OK] 已更新任务 {task_name} 状态为 {status}", flush=True)
            return

        if args.health:
            report = manager.run_health_check()
            print(manager.format_health_report(report), flush=True)
            return

        if args.status:
            # 输出 JSON 状态
            data = asdict(manager.state_manager.state)
            print(json.dumps(data, indent=2, ensure_ascii=False), flush=True)
            return

        if args.model:
            # 子进程调用模式: 接收模型参数(但不使用)
            print(f"[INFO] Manager received model: {args.model}", flush=True)
            #  fall through to daemon

        # Daemon 模式 (默认)
        print("[START] TTS Pipeline Manager 启动中...", flush=True)
        print("[OK] Manager 初始化成功", flush=True)
        manager.run()

    except KeyboardInterrupt:
        logger.info("收到 KeyboardInterrupt, 退出")
        print("\n[STOP] Manager 已停止", flush=True)
    except Exception as e:
        logger.error(f"Manager 运行失败: {e}", exc_info=True)
        print(f"[ERROR] Manager 错误: {e}", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()