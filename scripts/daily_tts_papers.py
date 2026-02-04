#!/usr/bin/env python3
"""
每日 TTS 论文处理（解析 + 抓取摘要 + 分析摘要 + 生成日报）
"""

import re
import time
import json
import requests
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
RAW_DIR = SCRIPT_DIR.parent / "raw" / "tts-arxiv-daily"
PROCESSED_DIR = SCRIPT_DIR.parent / "processed"
ABSTRACT_CACHE = PROCESSED_DIR / "abstracts_cache.json"
BY_DATE_DIR = PROCESSED_DIR / "by-date"
DAILY_SUMMARIES_DIR = SCRIPT_DIR.parent / "summaries" / "daily"
DAILY_SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)

KEYWORDS = {
    "zero-shot": ["zero-shot", "zero shot", "few-shot", "voice cloning", "speaker adaptation"],
    "expressive": ["expressive", "emotional", "emotion", "prosody", "intonation", "style", "affect"],
    "streaming": ["real-time", "streaming", "low-latency", "online", "incremental", "fast"],
    "long-context": ["long-context", "long-form", "long audio", "hour", "60-minute", "extended"],
    "multilingual": ["multilingual", "cross-lingual", "language", "dialect"],
    "codec": ["neural codec", "speech codec", "vocoder", "discrete token", "semantic token", "acoustic token"],
    "llm-based": ["LLM", "large language model", "speech language model", "transformer"],
    "editing": ["editing", "modification", "manipulation"],
    "synthesis": ["text-to-speech", "TTS", "speech synthesis", "voice synthesis"],
}

EXCLUDED = [
    "diarization", "speaker diarization", "multi-speaker", "speaker separation",
    "speaker embedding", "speaker verification", "voice spoofing", "anti-spoofing",
    "ASR", "speech recognition", "voice activity detection"
]

def load_cache():
    if ABSTRACT_CACHE.exists():
        with open(ABSTRACT_CACHE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(ABSTRACT_CACHE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def load_analysis_cache():
    analysis_path = PROCESSED_DIR / "analysis_cache.json"
    if analysis_path.exists():
        with open(analysis_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def fetch_abstracts_batch(arxiv_ids):
    if not arxiv_ids:
        return {}
    params = {"id_list": ",".join(arxiv_ids), "max_results": len(arxiv_ids)}
    try:
        resp = requests.get("https://export.arxiv.org/api/query", params=params, timeout=30)
        resp.raise_for_status()
        results = {}
        entries = re.findall(r'<entry>(.*?)</entry>', resp.text, re.DOTALL)
        for entry in entries:
            id_match = re.search(r'<id[^>]*>([^<]+)</id>', entry)
            summary_match = re.search(r'<summary[^>]*>(.*?)</summary>', entry, re.DOTALL)
            if id_match and summary_match:
                raw_id = id_match.group(1).rstrip('/').split('/')[-1]
                arxiv_id = re.sub(r'v\d+$', '', raw_id)
                abstract = re.sub(r'\s+', ' ', summary_match.group(1).strip())
                results[arxiv_id] = abstract
        return results
    except Exception as e:
        print(f"批量获取失败: {e}")
        return {}

def parse_markdown_table(file_path: Path):
    try:
        lines = file_path.read_text(encoding='utf-8').splitlines()
    except UnicodeDecodeError:
        lines = file_path.read_text(encoding='gbk', errors='replace').splitlines()
    papers = []
    for line in lines:
        line = line.strip()
        if not line.startswith('|') or 'Publish Date' in line or '---' in line:
            continue
        if not re.search(r'\d{4}-\d{2}-\d{2}', line):
            continue
        cols = [c.strip() for c in line.split('|')]
        if len(cols) < 6:
            continue
        date_str = cols[1].replace('**', '').strip()
        title = cols[2].replace('**', '').strip()
        authors = cols[3].replace('**', '').strip()
        pdf_col = cols[4]
        arxiv_id = None
        arxiv_url = None
        arxiv_match = re.search(r'https?://arxiv\.org/abs/([^\s)\]]+)', pdf_col)
        if arxiv_match:
            arxiv_id = arxiv_match.group(1)
            arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
        paper = {
            "date": date_str,
            "title": title,
            "authors": authors,
            "arxiv_id": arxiv_id,
            "arxiv_url": arxiv_url,
            "raw": f"{title} {authors}"
        }
        papers.append(paper)
    return papers

def get_tags(paper):
    text = paper['title'] + ' ' + paper['authors'] + ' ' + paper['raw']
    text_lower = text.lower()
    tags = []
    for tag, keywords in KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                tags.append(tag)
                break
    # 排除
    for ex in EXCLUDED:
        if ex in text_lower:
            return None
    return tags if tags else None

def generate_date_file(date_str, date_papers):
    date_file = BY_DATE_DIR / f"{date_str}.md"
    with date_file.open('w', encoding='utf-8') as f:
        f.write(f"# TTS Papers - {date_str}\n\n")
        f.write(f"Total: {len(date_papers)}\n\n")
        for p in date_papers:
            f.write(f"## {p['title']}\n")
            f.write(f"- **Authors**: {p['authors']}\n")
            if p['arxiv_id']:
                f.write(f"- **arXiv**: [{p['arxiv_id']}]({p['arxiv_url']})\n")
            f.write(f"- **Tags**: {', '.join(p['tags'])}\n\n")
    print(f"生成 {date_file.name}: {len(date_papers)} 篇")

def insert_abstracts_to_file(date_file: Path, cache: dict):
    content = date_file.read_text(encoding='utf-8')
    if "**Abstract**:" in content:
        return 0
    lines = content.splitlines(keepends=True)
    new_lines = []
    inserted = set()
    for i, line in enumerate(lines):
        new_lines.append(line)
        if line.strip().startswith("- **Tags**:"):
            arxiv_id = None
            for j in range(i-1, max(0, i-20), -1):
                m = re.search(r'\[([^\]]+)\]\(https?://arxiv\.org/abs/([^)\]]+)\)', lines[j])
                if m:
                    arxiv_id = re.sub(r'v\d+$', '', m.group(2))
                    break
            if arxiv_id and arxiv_id in cache and arxiv_id not in inserted:
                abstract = cache[arxiv_id]
                new_lines.append(f"- **Abstract**: {abstract}\n")
                inserted.add(arxiv_id)
    date_file.write_text(''.join(new_lines), encoding='utf-8')
    return len(inserted)

def generate_daily_report(date_str, papers):
    """生成中文日报（带分析摘要）"""
    if not papers:
        return
    total = len(papers)
    topic_counts = {}
    for p in papers:
        for tag in p['tags']:
            topic_counts[tag] = topic_counts.get(tag, 0) + 1
    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)

    priority_topics = {"zero-shot", "streaming", "llm-based", "long-context", "expressive"}
    highlights = [p for p in papers if any(t in priority_topics for t in p['tags'])]
    highlights.sort(key=lambda x: x['title'])

    lines = []
    lines.append(f"# TTS 论文日报")
    lines.append(f"**日期**: {date_str}")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("## 概览")
    lines.append(f"- **论文数**: {total}")
    lines.append("- **主题分布**:")
    for topic, count in sorted_topics:
        lines.append(f"  - `{topic}`: {count}")
    lines.append("")

    lines.append("## 重点论文（分析摘要）")
    for p in highlights:
        lines.append(f"- **{p['title']}**")
        lines.append(f"  - 作者: {p['authors']}")
        lines.append(f"  - arXiv: [{p['arxiv_id']}]({p['arxiv_url']})")
        lines.append(f"  - 标签: {', '.join(p['tags'])}")
        analysis = p.get('analysis')
        if analysis:
            lines.append(f"  - TLDR: {analysis['tldr']}")
            lines.append(f"  - 核心贡献: {analysis['core_contribution']}")
            lines.append(f"  - 方法: {analysis['methodology']}")
            lines.append(f"  - 关键发现: {analysis['key_findings']}")
            lines.append(f"  - 局限性: {analysis['limitations']}")
            lines.append(f"  - 评估: {analysis['evaluation']} (评分: {analysis['rating']}/10)")
        else:
            if p.get('abstract'):
                lines.append(f"  - 摘要: {p['abstract']}")
        lines.append("")

    lines.append("## 完整列表（带分析摘要）")
    for p in sorted(papers, key=lambda x: x['title'].lower()):
        lines.append(f"- **{p['title']}**")
        lines.append(f"  - 作者: {p['authors']}")
        lines.append(f"  - arXiv: [{p['arxiv_id']}]({p['arxiv_url']})")
        analysis = p.get('analysis')
        if analysis:
            lines.append(f"  - TLDR: {analysis['tldr']}")
            lines.append(f"  - 核心贡献: {analysis['core_contribution']}")
            lines.append(f"  - 关键发现: {analysis['key_findings']}")
        else:
            if p.get('abstract'):
                lines.append(f"  - 摘要: {p['abstract']}")
        lines.append("")
    report = "\n".join(lines)
    out_file = DAILY_SUMMARIES_DIR / f"{date_str}.md"
    out_file.write_text(report, encoding='utf-8')
    print(f"日报已生成: {out_file}")

def main():
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        # 默认处理昨天的论文
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"=== 处理 {target_date} 的 TTS 论文 ===")

    raw_readme = RAW_DIR / "README.md"
    if not raw_readme.exists():
        print(f"错误: {raw_readme} 不存在")
        sys.exit(1)

    # 解析 README
    papers = parse_markdown_table(raw_readme)
    print(f"解析到 {len(papers)} 篇论文")
    tagged_papers = []
    for paper in papers:
        tags = get_tags(paper)
        if tags:
            paper['tags'] = tags
            tagged_papers.append(paper)
    print(f"TTS 相关: {len(tagged_papers)} 篇")

    # 按日期分组
    papers_by_date = {}
    for p in tagged_papers:
        d = p['date']
        papers_by_date.setdefault(d, []).append(p)

    if target_date not in papers_by_date:
        print(f"目标日期 {target_date} 没有论文")
        return
    date_papers = papers_by_date[target_date]

    # 生成日期文件
    generate_date_file(target_date, date_papers)

    # 加载缓存并处理摘要
    cache = load_cache()
    date_file = BY_DATE_DIR / f"{target_date}.md"
    content = date_file.read_text(encoding='utf-8')
    arxiv_ids = set()
    for m in re.finditer(r'\[([^\]]+)\]\(https?://arxiv\.org/abs/([^)\]]+)\)', content):
        arxiv_id = re.sub(r'v\d+$', '', m.group(2))
        arxiv_ids.add(arxiv_id)
    need_fetch = [i for i in arxiv_ids if i not in cache]
    if need_fetch:
        print(f"需要抓取 {len(need_fetch)} 条新摘要")
        for i in range(0, len(need_fetch), 200):
            batch = need_fetch[i:i+200]
            results = fetch_abstracts_batch(batch)
            cache.update(results)
            save_cache(cache)
            print(f"  批次 {i//200 + 1}: {len(results)} 篇")
            if i + 200 < len(need_fetch):
                time.sleep(3)
    else:
        print("所有摘要已缓存")

    # 插入摘要到文件
    inserted = insert_abstracts_to_file(date_file, cache)
    print(f"插入 {inserted} 条摘要")

    # 为 date_papers 添加 abstract 字段
    for p in date_papers:
        aid = p.get('arxiv_id')
        p['abstract'] = cache.get(aid, "") if aid else ""

    # 加载分析缓存并合并
    analysis_cache = load_analysis_cache()
    for p in date_papers:
        aid = p.get('arxiv_id')
        if aid and aid in analysis_cache:
            p['analysis'] = analysis_cache[aid]
        else:
            p['analysis'] = None

    # 生成日报
    generate_daily_report(target_date, date_papers)
    print(f"=== {target_date} 处理完成 ===")

if __name__ == "__main__":
    import sys
    from datetime import datetime
    main()
