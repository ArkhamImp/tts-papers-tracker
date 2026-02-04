# TTS 论文追踪与处理系统

自动追踪、处理、分析和 summarise 最新的 TTS 相关论文（基于 arxiv 每日更新）。

## 目录结构

```
papers/
├── raw/tts-arxiv-daily/      # 原始数据源
│   ├── README.md             # 论文列表 Markdown 表格
│   ├── config.yaml           # 爬虫配置
│   └── daily_arxiv.py        # arxiv 爬虫脚本
│
├── scripts/                  # 核心处理脚本
│   ├── parse_tts_papers.py   # 解析分类论文
│   ├── fetch_abstracts.py    # 抓取摘要
│   ├── analyze_papers.py     # LLM 分析（可选）
│   ├── daily_tts_papers.py   # 生成日报
│   ├── generate_weekly_summary.py
│   ├── generate_monthly_summary.py
│   └── run_full_pipeline.py  # 完整 pipeline
│
├── processed/                # 处理后数据
│   ├── by-date/              # 按日期分类的论文
│   ├── by-topic/             # 按主题分类的论文
│   ├── abstracts_cache.json
│   ├── analysis_cache.json
│   └── index.md
│
├── summaries/                # 生成的报告
│   ├── daily/YYYY-MM-DD.md
│   ├── weekly/YYYY-Www.md
│   └── monthly/YYYY-MM.md
│
└── run_tts_pipeline.bat      # Windows 批处理一键运行

```

## 快速开始

### 完整流程（推荐）

直接运行完整 pipeline（自动执行所有步骤）：

```bash
python papers/scripts/run_full_pipeline.py --skip-analysis
```

或使用批处理文件（Windows）：

```cmd
papers\run_tts_pipeline.bat
```

### 单独步骤

如果只想执行特定步骤：

1. **更新论文列表**（从 arxiv 抓取）：
```bash
cd papers/raw/tts-arxiv-daily
python daily_arxiv.py --config_path config.yaml
```

2. **解析并分类**：
```bash
python papers/scripts/parse_tts_papers.py
```

3. **抓取摘要**：
```bash
python papers/scripts/fetch_abstracts.py
```

4. **LLM 分析**（需配置 DeepSeek API）：
```bash
python papers/scripts/analyze_papers.py
```

5. **生成日报/周报/月报**：
```bash
python papers/scripts/daily_tts_papers.py 2026-02-02  # 指定日期
python papers/scripts/generate_weekly_summary.py
python papers/scripts/generate_monthly_summary.py 2026-02
```

## 配置

### LLM 分析（可选）

如需启用 LLM 论文分析，需在 OpenClaw 配置文件中添加 DeepSeek provider：

配置路径：`~\.openclaw\openclaw.json`

```json
{
  "models": {
    "providers": {
      "deepseek": {
        "apiKey": "your-api-key",
        "baseUrl": "https://api.deepseek.com"
      }
    }
  }
}
```

使用 `--skip-analysis` 参数可跳过 LLM 分析以节省时间和配额。

### 自动调度（Cron Jobs）

已在 OpenClaw 中配置自动化任务：

- **TTS-Daily-Crawl**：每天 00:20，更新论文列表
- **TTS-Papers-Crawl**：每天 00:30，解析分类 + 抓取摘要
- **TTS-Daily-Summary**：每天 01:00，生成日报
- **TTS-Papers-Analysis**：每天 01:30，LLM 分析（可选）
- **TTS-Weekly-Summary**：每周日 04:00，生成周报
- **TTS-Monthly-Summary**：每月 1 号 05:00，生成月报
- **Git-Push-Daily**：每天 06:30，git 推送

## 输出

- **日报**：`papers/summaries/daily/YYYY-MM-DD.md`
- **周报**：`papers/summaries/weekly/YYYY-Www.md`
- **月报**：`papers/summaries/monthly/YYYY-MM.md`

## 编码处理

系统已针对 Windows (GBK) 兼容性进行优化：
- 文件读取时自动 fallback 到 UTF-8/GBK 编码
- 移除了所有 emoji 符号
- 所有路径使用绝对路径防止拼接错误

## 报告示例

日报包含：
- 当日新论文概览
- 按主题分类统计
- 重点论文摘要
- LLM 分析结果（如启用）

周报/月报包含周期趋势、热点主题和重要发现。

## 故障排除

**问题：`UnicodeDecodeError`**
- 确保脚本使用 UTF-8/GBK fallback 编码读取文件
- 检查原始数据文件编码

**问题：路径错误**
- 所有脚本使用基于 `__file__` 的绝对路径
- 确保目录结构完整

**问题：LLM 分析失败**
- 检查 openclaw.json 配置
- 确认 DeepSeek API 配额充足
- 使用 `--skip-analysis` 跳过分析

## 维护

- 定期清理 `processed/` 缓存释放磁盘空间
- 调整 `parse_tts_papers.py` 中的关键词规则以优化分类
- 修改 `papers/raw/tts-arxiv-daily/config.yaml` 定制爬虫行为

## 许可证

本项目基于 [tqsar/daily-arxiv](https://github.com/tqsar/daily-arxiv) 改造，原始来源：[Vincentqyw/cv-arxiv-daily](https://github.com/Vincentqyw/cv-arxiv-daily)。

---

**最后更新**：2026-02-04