#!/usr/bin/env python3
"""
TTS-arxiv-daily 解析器
从 README.md 的 Markdown 表格中提取论文，按TTS相关关键词分类，生成索引。
"""

import re
import time
import requests
from pathlib import Path

# 配置
RAW_DIR = Path("papers/raw/tts-arxiv-daily")
PROCESSED_DIR = Path("papers/processed")

# 关键词规则
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

def parse_markdown_table(file_path: Path):
    """从 Markdown 表格解析论文"""
    lines = file_path.read_text(encoding='utf-8').splitlines()
    papers = []

    for line in lines:
        line = line.strip()
        # 识别表格数据行：以 | 开头且包含日期 YYYY-MM-DD
        if not line.startswith('|') or 'Publish Date' in line or '---' in line:
            continue
        if not re.search(r'\d{4}-\d{2}-\d{2}', line):
            continue

        # 按 | 分割列（去除首尾空列）
        cols = [c.strip() for c in line.split('|')]
        if len(cols) < 6:  # 至少需要：空、日期、标题、作者、PDF、Code、空
            continue

        # col[1] = 日期 (可能带 **)
        date_str = cols[1].replace('**', '').strip()
        # col[2] = 标题 (可能带 **)
        title = cols[2].replace('**', '').strip()
        # col[3] = 作者 (可能带 **)
        authors = cols[3].replace('**', '').strip()
        # col[4] = PDF 链接列，格式如 [2601.23255](http://arxiv.org/abs/2601.23255)
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
    """根据关键词给论文打标签"""
    text = paper['title'] + ' ' + paper['authors'] + ' ' + paper['raw']
    text_lower = text.lower()

    # 排除非TTS内容
    if any(ex in text_lower for ex in EXCLUDED):
        return None

    tags = []
    for tag, kws in KEYWORDS.items():
        if any(kw.lower() in text_lower for kw in kws):
            tags.append(tag)
    return tags if tags else ["other"]

def main():
    # 读取原始文件
    raw_file = RAW_DIR / "README.md"
    if not raw_file.exists():
        print(f"Error: {raw_file} not found")
        return

    papers = parse_markdown_table(raw_file)

    # 过滤和标记
    filtered_papers = []
    for p in papers:
        text = f"{p['title']} {p['authors']}".lower()
        # 检查排除关键词
        if any(ex in text for ex in EXCLUDED):
            continue
        tags = get_tags(p)
        if tags:
            p['tags'] = tags
            filtered_papers.append(p)

    print(f"Parsed {len(papers)} papers, {len(filtered_papers)} TTS-relevant")

    # 创建输出目录
    date_dir = PROCESSED_DIR / "by-date"
    date_dir.mkdir(parents=True, exist_ok=True)
    topic_dir = PROCESSED_DIR / "by-topic"
    topic_dir.mkdir(parents=True, exist_ok=True)

    # 按日期分组
    papers_by_date = {}
    for p in filtered_papers:
        d = p['date']
        if d not in papers_by_date:
            papers_by_date[d] = []
        papers_by_date[d].append(p)

    # 写入 by-date 和 by-topic
    topic_files = {topic: [] for topic in KEYWORDS.keys()}
    topic_files["other"] = []

    for date_str, date_papers in sorted(papers_by_date.items()):
        # 写入日期文件
        date_out = date_dir / f"{date_str}.md"
        with date_out.open('w', encoding='utf-8') as f:
            f.write(f"# TTS Papers - {date_str}\n\n")
            f.write(f"Total: {len(date_papers)}\n\n")
            for p in date_papers:
                f.write(f"## {p['title']}\n")
                f.write(f"- **Authors**: {p['authors']}\n")
                if p['arxiv_id']:
                    f.write(f"- **arXiv**: [{p['arxiv_id']}]({p['arxiv_url']})\n")
                f.write(f"- **Tags**: {', '.join(p['tags'])}\n\n")

        # 收集到主题分类
        for p in date_papers:
            for tag in p['tags']:
                if tag in topic_files:
                    topic_files[tag].append(p)

    # 写入 by-topic
    for topic, papers_list in topic_files.items():
        if not papers_list:
            continue
        topic_file = topic_dir / f"{topic}.md"
        mode = 'w'  # 每次重写，避免重复
        with topic_file.open(mode, encoding='utf-8') as f:
            f.write(f"# {topic.replace('-', ' ').title()} Papers\n\n")
            # 按日期倒序
            papers_by_date_in_topic = {}
            for p in papers_list:
                d = p['date']
                if d not in papers_by_date_in_topic:
                    papers_by_date_in_topic[d] = []
                papers_by_date_in_topic[d].append(p)
            for date_str in sorted(papers_by_date_in_topic.keys(), reverse=True):
                f.write(f"## {date_str}\n\n")
                for p in papers_by_date_in_topic[date_str]:
                    f.write(f"- **{p['title']}**\n")
                    f.write(f"  - Authors: {p['authors']}\n")
                    if p['arxiv_id']:
                        f.write(f"  - arXiv: [{p['arxiv_id']}]({p['arxiv_url']})\n")
                f.write("\n")

    # 更新主索引（追加）
    index_file = PROCESSED_DIR / "index.md"
    mode = 'a' if index_file.exists() else 'w'
    with index_file.open(mode, encoding='utf-8') as f:
        if mode == 'w':
            f.write("# TTS Papers Index\n\n")
        f.write(f"## Updated {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"- **Total TTS-relevant papers**: {len(filtered_papers)}\n")
        for topic in sorted(topic_files.keys()):
            count = len(topic_files[topic])
            if count > 0:
                f.write(f"- `{topic}`: {count} papers\n")
        f.write("\n")

    print(f"\nProcessed {len(filtered_papers)} TTS-relevant papers")
    print("By topic: " + ", ".join(f"{k}:{len(v)}" for k,v in topic_files.items() if v))

# ========== 摘要抓取模块 ==========
def fetch_abstracts_for_date(date_str):
    """为指定日期的论文抓取摘要并插入到文件中"""
    date_file = PROCESSED_DIR / "by-date" / f"{date_str}.md"
    if not date_file.exists():
        print(f"日期文件 {date_file} 不存在")
        return

    # 读取文件，提取 arxiv_id
    content = date_file.read_text(encoding='utf-8')
    arxiv_ids = set()
    for m in re.finditer(r'\[([^\]]+)\]\(https?://arxiv\.org/abs/([^)\]]+)\)', content):
        arxiv_id = m.group(2)
        arxiv_id = re.sub(r'v\d+$', '', arxiv_id)
        arxiv_ids.add(arxiv_id)

    if not arxiv_ids:
        print("没有找到 arXiv ID")
        return

    print(f"需要抓取 {len(arxiv_ids)} 篇摘要")

    # 批量获取摘要
    cache = {}
    BATCH_SIZE = 200
    arxiv_ids_list = list(arxiv_ids)
    for i in range(0, len(arxiv_ids_list), BATCH_SIZE):
        batch = arxiv_ids_list[i:i+BATCH_SIZE]
        params = {"id_list": ",".join(batch), "max_results": len(batch)}
        try:
            resp = requests.get("https://export.arxiv.org/api/query", params=params, timeout=30)
            resp.raise_for_status()
            entries = re.findall(r'<entry>(.*?)</entry>', resp.text, re.DOTALL)
            for entry in entries:
                id_match = re.search(r'<id[^>]*>([^<]+)</id>', entry)
                summary_match = re.search(r'<summary[^>]*>(.*?)</summary>', entry, re.DOTALL)
                if id_match and summary_match:
                    raw_id = id_match.group(1).rstrip('/').split('/')[-1]
                    arxiv_id_std = re.sub(r'v\d+$', '', raw_id)
                    abstract = re.sub(r'\s+', ' ', summary_match.group(1).strip())
                    cache[arxiv_id_std] = abstract
            print(f"  批次 {i//BATCH_SIZE + 1}: 获取 {len(entries)} 篇")
            if i + BATCH_SIZE < len(arxiv_ids_list):
                time.sleep(3)
        except Exception as e:
            print(f"  批次失败: {e}")

    # 插入摘要
    lines = content.splitlines(keepends=True)
    new_lines = []
    inserted = set()  # 防止重复插入
    for i, line in enumerate(lines):
        new_lines.append(line)
        if line.strip().startswith("- **Tags**:"):
            # 找本区的 arxiv_id（往前找）
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
    print(f"{date_file.name} 已更新，添加 {len(inserted)} 条摘要")

if __name__ == "__main__":
    from datetime import datetime
    main()
