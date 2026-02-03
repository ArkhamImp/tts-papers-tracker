#!/usr/bin/env python3
"""
TTS 论文周报生成器（中文，带 LLM 分析摘要）
"""

from pathlib import Path
from datetime import datetime, timedelta, date
import re
import json

PROCESSED_DIR = Path("papers/processed")
BY_DATE_DIR = PROCESSED_DIR / "by-date"
SUMMARIES_DIR = Path("papers/summaries/weekly")
SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)

def load_analysis_cache():
    analysis_path = PROCESSED_DIR / "analysis_cache.json"
    if analysis_path.exists():
        with open(analysis_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def get_last_7_dates():
    all_dates = []
    for f in BY_DATE_DIR.glob("*.md"):
        try:
            d = datetime.strptime(f.stem, "%Y-%m-%d").date()
            all_dates.append(d)
        except:
            continue
    all_dates.sort(reverse=True)
    seen = set()
    dates = []
    for d in all_dates:
        if d not in seen:
            seen.add(d)
            dates.append(d)
        if len(dates) >= 7:
            break
    return sorted(dates)

def parse_date_file(filepath: Path):
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

def generate_weekly_report(papers_by_date, dates):
    all_papers = []
    for d in dates:
        all_papers.extend(papers_by_date.get(d, []))

    total = len(all_papers)
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

    week_num = dates[-1].strftime("%Y-W%V")
    year = dates[-1].isocalendar()[0]
    period_str = f"{dates[0]} 至 {dates[-1]}" if dates else "无数据"

    lines = []
    lines.append(f"# TTS 论文周报")
    lines.append(f"**周期**: {period_str} (第 {dates[-1].isocalendar()[1]} 周, {year} 年)")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("## 概览")
    lines.append(f"- **论文总数**: {total}")
    lines.append("- **主题分布**:")
    for topic, count in sorted_topics:
        lines.append(f"  - `{topic}`: {count}")
    lines.append("")

    priority_topics = {"zero-shot", "streaming", "llm-based", "long-context", "expressive"}
    highlight_papers = [p for p in all_papers if any(t in priority_topics for t in p['tags'])]
    highlight_papers.sort(key=lambda x: x['date'], reverse=True)

    lines.append("## 重点论文（分析摘要）")
    if not highlight_papers:
        lines.append("*本周无重点论文*\n")
    else:
        for p in highlight_papers[:10]:
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
                abstract = p['abstract'][:250] + "..." if len(p['abstract']) > 250 else p['abstract']
                lines.append(f"  - **摘要**: {abstract}")
            lines.append("")

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
                abstract = p['abstract'][:150] + "..." if len(p['abstract']) > 150 else p['abstract']
                lines.append(f"  - **摘要**: {abstract}")
            lines.append("")
        lines.append("")
    return "\n".join(lines), week_num

def update_main_document_highlights(highlight_papers, week_num):
    main_doc = Path("LLM_TTS_Technologies_2024-2025.md")
    if not main_doc.exists():
        print("Main document not found, skipping highlights update.")
        return

    highlight_lines = []
    if highlight_papers:
        for p in highlight_papers[:10]:
            highlight_lines.append(f"- **{p['title']}** ({p['date']})")
            highlight_lines.append(f"  - Authors: {p['authors']}")
            highlight_lines.append(f"  - arXiv: [{p['arxiv_id']}]({p['arxiv_url']})")
            highlight_lines.append(f"  - Tags: {', '.join(p['tags'])}")
            if p.get('analysis'):
                a = p['analysis']
                highlight_lines.append(f"  - TLDR: {a['tldr']}")
                highlight_lines.append(f"  - Core Contribution: {a['core_contribution']}")
                highlight_lines.append(f"  - Key Findings: {a['key_findings']}")
                highlight_lines.append(f"  - Evaluation: {a['evaluation']} (Rating: {a['rating']}/10)")
            elif p.get('abstract'):
                abstract = p['abstract'][:250] + "..." if len(p['abstract']) > 250 else p['abstract']
                highlight_lines.append(f"  - Abstract: {abstract}")
            highlight_lines.append("")
    else:
        highlight_lines.append("*No highlight papers this week.*\n")

    new_highlights = "\n".join(highlight_lines)
    content = main_doc.read_text(encoding='utf-8')
    start_marker = "<!-- LATEST_HIGHLIGHTS_START -->"
    end_marker = "<!-- LATEST_HIGHLIGHTS_END -->"
    if start_marker in content and end_marker in content:
        parts = content.split(start_marker)
        before = parts[0]
        after = parts[1].split(end_marker, 1)[1]
        new_content = f"{before}{start_marker}\n{new_highlights}{end_marker}{after}"
        new_content = re.sub(
            r'\*Last updated: .+\*',
            f"*Last updated: {datetime.now().strftime('%Y-%m-%d')} (Week {week_num.split('-W')[1]})*",
            new_content
        )
        main_doc.write_text(new_content, encoding='utf-8')
        print("Main document highlights updated.")
    else:
        print("Markers not found in main document, skipping update.")

def main():
    dates = get_last_7_dates()
    if not dates:
        print("No date files found.")
        return
    papers_by_date = {}
    for d in dates:
        f = BY_DATE_DIR / f"{d}.md"
        if f.exists():
            papers = parse_date_file(f)
            papers_by_date[d] = papers

    analysis_cache = load_analysis_cache()
    for d in dates:
        for p in papers_by_date.get(d, []):
            aid = p.get('arxiv_id')
            if aid and aid in analysis_cache:
                p['analysis'] = analysis_cache[aid]

    report, week_num = generate_weekly_report(papers_by_date, dates)
    out_file = SUMMARIES_DIR / f"{week_num}.md"
    out_file.write_text(report, encoding='utf-8')
    total = sum(len(p) for p in papers_by_date.values())
    print(f"Weekly report generated: {out_file}")
    print(f"Covering {len(dates)} days, total {total} papers.")

    # Update main doc highlights
    all_papers = []
    for d in dates:
        all_papers.extend(papers_by_date.get(d, []))
    priority_topics = {"zero-shot", "streaming", "llm-based", "long-context", "expressive"}
    highlight_papers = [p for p in all_papers if any(t in priority_topics for t in p['tags'])]
    highlight_papers.sort(key=lambda x: x['date'], reverse=True)
    update_main_document_highlights(highlight_papers, week_num)

if __name__ == "__main__":
    main()
