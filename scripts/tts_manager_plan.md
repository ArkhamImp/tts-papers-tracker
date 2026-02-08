# TTS Manager 子代理实现计划

## 目标
创建一个持续运行的 subagent (tts-manager),作为 TTS 管道的中枢控制系统

## 职责

### 1. 系统监控
- 实时监控所有 cron 作业的执行状态
- 检查数据完整性(论文列表、缓存、摘要文件)
- 监控磁盘空间和文件系统健康

### 2. 任务协调
- 管理任务依赖关系 (daily_arxiv → parse_tts_papers → fetch_abstracts → analyze_papers → daily_tts_papers)
- 在检测到前置任务失败时阻止后续任务执行
- 提供手动触发任意任务的能力

### 3. 异常处理
- 捕获和分析任务失败原因
- 自动重试机制(最多3次,指数退避)
- 失败告警和通知(待集成 Feishu)

### 4. 状态管理
- 维护管道状态文件: `papers/processed/pipeline_state.json`
- 记录最近执行历史、错误统计
- 提供状态查询接口(供其他 agent 或用户)

### 5. 健康检查
- 响应系统事件 "Check TTS pipeline health and status"
- 生成健康报告: 任务完成情况、数据新鲜度、错误率

## 技术实现

### 运行模式
- 使用 `sessionTarget: "isolated"` 创建持久化会话
- 进入主事件循环,定期(每分钟)检查状态
- 响应系统事件进行健康检查
- 使用 `time.sleep()` 避免 CPU 占用

### 状态存储
- JSON 文件: `papers/processed/pipeline_state.json`
- 包含: 最后运行时间、成功/失败计数、错误日志、数据摘要

### 通信机制
- 监听系统事件: `payload.kind: "systemEvent"`
- 支持命令: 
  - "status" - 返回完整状态报告
  - "health" - 健康检查
  - "retry <task_name>" - 手动重试失败任务
  - "trigger <task_name>" - 立即执行指定任务

### 日志记录
- 专用日志文件: `papers/processed/tts_manager.log`
- 轮转策略: 每天一个文件,保留7天

## 与现有 cron 的集成

### 双向通信
- Manager 记录每个 cron 任务的执行结果
- Cron 任务执行前后通知 manager (通过临时状态文件或共享状态)
- Manager 可以临时禁用 cron 任务(通过标记状态文件)

### 健康检查集成
- TTS-Pipeline-Health-Check cron 任务发送系统事件给 main 会话
- Main 会话转发给 tts-manager subagent
- Manager 返回详细健康报告

## 启动方式

### 1. 手动启动(首次)
```bash
openclaw sessions_spawn --agent main --task "Start TTS Manager subagent: python papers/scripts/tts_manager.py"
```

### 2. 自动重启(需配置)
添加 cron 作业,在 manager 意外退出时重启:
- 检查 manager 会话是否活跃
- 如不活跃,重新 spawn

### 3. Gateway 重启恢复
- 在 Gateway 配置中添加自动恢复逻辑
- 检查上次运行时间,超过阈值则重启

## 阶段实施

### Phase 1: 基础框架 (现在)
- [ ] 创建 `tts_manager.py` 脚本
- [ ] 实现状态存储和加载
- [ ] 实现主事件循环
- [ ] 实现基本日志记录

### Phase 2: 监控功能
- [ ] 实现 cron 状态查询(通过 sessions_list 或文件标记)
- [ ] 实现数据完整性检查
- [ ] 实现状态报告生成

### Phase 3: 协调控制
- [ ] 实现任务依赖检查
- [ ] 实现手动触发功能
- [ ] 实现失败重试逻辑

### Phase 4: 告警集成
- [ ] 集成 Feishu 通知(插件安装后)
- [ ] 配置告警规则(连续失败、数据过期等)

### Phase 5: 稳定性和恢复
- [ ] 添加心跳机制(防止僵尸进程)
- [ ] 实现优雅关闭(Ctrl+C 处理)
- [ ] 添加启动自愈机制

## 验收标准

1. **持续运行**: Manager 会话一旦启动,持续运行直到主动停止
2. **状态持久化**: 重启后恢复之前的计数和状态
3. **准确监控**: 实时反映所有 cron 任务的执行情况
4. **快速响应**: 健康检查请求在 5 秒内返回
5. **错误恢复**: 在单个任务失败时能自动重试或隔离
6. **低资源占用**: CPU < 1%, 内存 < 50MB

---

*创建时间: 2026-02-06*
*状态: 计划阶段*