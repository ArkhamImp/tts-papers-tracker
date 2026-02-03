#!/usr/bin/env python3
"""
TTS 论文月报生成器（中文，带 LLM 分析摘要）
"""

from pathlib import Path
from datetime import datetime, timedelta
import re

PROCESSED_DIR = Path("papers/processed")
BY_DATE_DIR = PROCESSED_DIR / "by-date"
SUMMARIES_DIR = Path("papers/summaries/monthly")
SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)

def load_analysis_cache():
    analysis_path = PROCESSED_DIR / "analysis_cache.json"
    if analysis_path.exists():
        with open(analysis_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def get_last_month_dates():
    """获取上一个月的所有有论文的日期（升序）"""
    today = datetime.now().date()
    first_of_this_month = today.replace(day=1)
    last_month_end = first_of_this_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    dates = []
    for f in BY_DATE_DIR.glob("*.md"):
        try:
            d = datetime.strptime(f.stem, "%Y-%m-%d").date()
            if last_month_start <= d <= last_month_end:
                dates.append(d)
        except:
            continue
    dates.sort()
    return dates

def parse_date_file(filepath: Path):
    """解析日期文件，提取论文信息"""
    papers = []
    content = filepath.read_text(encoding='utf-8')
    blocks = re.split(r'\n(?=## )', content)
    for block in blocks:
        if not block.strip().startswith('##'):
            continue
        lines = block.splitlines()
        if not lines:
            continue
        title = lines[0].lstrip('# ').strip()
        authors = ""
        arxiv_id = ""
        arxiv_url = ""
        tags = ""
        abstract = ""
        for i, line in enumerate(lines):
            line_s = line.strip()
            if line_s.startswith("- **Authors**:"):
                authors = line_s.split(":", 1)[1].strip()
            elif line_s.startswith("- **arXiv**:"):
                m = re.search(r'\[([^\]]+)\]\(([^)]+)\)', line_s)
                if m:
                    arxiv_id = m.group(1)
                    arxiv_url = m.group(2)
            elif line_s.startswith("- **Tags**:"):
                tags = line_s.split(":", 1)[1].strip()
                if i+1 < len(lines):
                    nxt = lines[i+1].strip()
                    if nxt.startswith("- **Abstract**:"):
                        abstract = nxt.split(":", 1)[1].strip()
        if authors and arxiv_id and tags:
            papers.append({
                "title": title,
                "authors": authors,
                "arxiv_id": arxiv_id,
                "arxiv_url": arxiv_url,
                "tags": [t.strip() for t in tags.split(',')],
                "date": filepath.stem,
                "abstract": abstract
            })
    return papers

def generate_monthly_report(papers_by_date, dates, analysis_cache):
    all_papers = []
    for d in dates:
        all_papers.extend(papers_by_date.get(d, []))

    total = len(all_papers)
    # 主题统计（中文化）
    topic_labels = {
        "zero-shot": "零样本",
        "expressive": "表现力",
        "streaming": "流式",
        "long-context": "长文本",
        "multilingual": "多语言",
        "codec": "编解码器",
        "llm-based": "LLM 基础",
        "editing": "编辑",
        "synthesis": "合成",
        "other": "其他"
    }
    topic_counts = {}
    for p in all_papers:
        for tag in p['tags']:
            label = topic_labels.get(tag, tag)
            topic_counts[label] = topic_counts.get(label, 0) + 1
    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)

    month_key = dates[-1].strftime("%Y-%m") if dates else "N/A"
    period_str = f"{dates[0]} 至 {dates[-1]}" if dates else "无数据"

    lines = []
    lines.append(f"# TTS 论文月报")
    lines.append(f"**月份**: {month_key}")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("## 概览")
    lines.append(f"- **论文总数**: {total}")
    lines.append("- **主题分布**:")
    for topic, count in sorted_topics:
        lines.append(f"  - `{topic}`: {count}")
    lines.append("")

    # 重点论文（带分析）
    lines.append("## 重点论文（分析摘要）")
    priority_topics = {"zero-shot", "streaming", "llm-based", "long-context", "expressive", "codec"}
    highlight_papers = [p for p in all_papers if any(t in priority_topics for t in p['tags'])]
    highlight_papers.sort(key=lambda x: x['date'], reverse=True)
    if not highlight_papers:
        lines.append("*本月无重点论文*\n")
    else:
        for p in highlight_papers[:20]:
            lines.append(f"- **{p['title']}** ({p['date']})")
            lines.append(f"  - **作者**: {p['authors']}")
            lines.append(f"  - **arXiv**: [{p['arxiv_id']}]({p['arxiv_url']})")
            lines.append(f"  - **标签**: {', '.join(p['tags'])}")
            if p.get('analysis'):
                a = p['analysis']
                lines.append(f"  - **TLDR**: {a['tldr']}")
                lines.append(f"  - **核心贡献**: {a['core_contribution']}")
                lines.append(f"  - **方法**: {a['methodology']}")
                lines.append(f"  - **关键发现**: {a['key_findings']}")
                lines.append(f"  - **评估**: {a['evaluation']} (评分: {a['rating']}/10)")
            elif p.get('abstract'):
                lines.append(f"  - **摘要**: {p['abstract']}")
            lines.append("")

    # 完整列表（按日期）
    lines.append("## 完整列表（按日期）")
    for d in sorted(dates, reverse=True):
        papers = papers_by_date.get(d, [])
        if not papers:
            continue
        lines.append(f"### {d}")
        papers.sort(key=lambda x: x['title'].lower())
        for p in papers:
            lines.append(f"- **{p['title']}**")
            lines.append(f"  - **作者**: {p['authors']}")
            lines.append(f"  - **arXiv**: [{p['arxiv_id']}]({p['arxiv_url']})")
            if p.get('analysis'):
                a = p['analysis']
                lines.append(f"  - **TLDR**: {a['tldr']}")
                lines.append(f"  - **核心贡献**: {a['core_contribution']}")
                lines.append(f"  - **关键发现**: {a['key_findings']}")
            elif p.get('abstract'):
                lines.append(f"  - **摘要**: {p['abstract']}")
            lines.append("")
        lines.append("")
    return "\n".join(lines)

def main():
    dates = get_last_month_dates()
    if not dates:
        print("No date files found for last month.")
        return

    # 读取各日期文件
    papers_by_date = {}
    for d in dates:
        f = BY_DATE_DIR / f"{d}.md"
        if f.exists():
            papers = parse_date_file(f)
            papers_by_date[d] = papers

    # 加载分析缓存并合并
    analysis_cache = load_analysis_cache()
    for d in dates:
        for p in papers_by_date.get(d, []):
            aid = p.get('arxiv_id')
            if aid and aid in analysis_cache:
                p['analysis'] = analysis_cache[aid]

    # 生成报告
    report = generate_monthly_report(papers_by_date, dates, {})

    # 写入文件
    month_key = dates[-1].strftime("%Y-%m") if dates else "unknown"
    out_file = SUMMARIES_DIR / f"{month_key}.md"
    out_file.write_text(report, encoding='utf-8')
    total = sum(len(p) for p in papers_by_date.values())
    print(f"Monthly report generated: {out_file}")
    print(f"Month: {month_key}, days with papers: {len(dates)}, total papers: {total}")

if __name__ == "__main__":
    import json
    main()
