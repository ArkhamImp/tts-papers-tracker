#!/usr/bin/env python3
"""
抓取最近30天论文的摘要（带ID标准化）
"""

import json
import time
import re
import requests
from pathlib import Path
from datetime import datetime, timedelta

PROCESSED_DIR = Path("papers/processed")
ABSTRACT_CACHE = PROCESSED_DIR / "abstracts_cache.json"
BY_DATE_DIR = PROCESSED_DIR / "by-date"

ARXIV_API = "https://export.arxiv.org/api/query"

def load_cache():
    if ABSTRACT_CACHE.exists():
        with open(ABSTRACT_CACHE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 标准化：去掉版本号（v1, v2...）
        std = {}
        for k, v in data.items():
            std_k = re.sub(r'v\d+$', '', k)
            std[std_k] = v
        print(f"加载缓存：原始 {len(data)} 条，标准化后 {len(std)} 条")
        return std
    return {}

def save_cache(cache):
    # 保存时不做额外处理
    with open(ABSTRACT_CACHE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def fetch_abstracts_batch(arxiv_ids):
    if not arxiv_ids:
        return {}
    params = {"id_list": ",".join(arxiv_ids), "max_results": len(arxiv_ids)}
    try:
        resp = requests.get(ARXIV_API, params=params, timeout=30)
        resp.raise_for_status()
        content = resp.text
        results = {}
        entries = re.findall(r'<entry>(.*?)</entry>', content, re.DOTALL)
        for entry in entries:
            id_match = re.search(r'<id[^>]*>([^<]+)</id>', entry)
            summary_match = re.search(r'<summary[^>]*>(.*?)</summary>', entry, re.DOTALL)
            if id_match and summary_match:
                raw_id = id_match.group(1).rstrip('/').split('/')[-1]
                arxiv_id = re.sub(r'v\d+$', '', raw_id)  # 标准化
                abstract = re.sub(r'\s+', ' ', summary_match.group(1).strip())
                results[arxiv_id] = abstract
        return results
    except Exception as e:
        print(f"批量获取失败: {e}")
        return {}

def collect_recent_ids(days=30):
    cutoff = datetime.now().date() - timedelta(days=days)
    ids = set()
    for f in BY_DATE_DIR.glob("*.md"):
        try:
            d = datetime.strptime(f.stem, "%Y-%m-%d").date()
            if d >= cutoff:
                content = f.read_text(encoding='utf-8')
                matches = re.findall(r'https?://arxiv\.org/abs/([^\s)\]]+)', content)
                for mid in matches:
                    std_id = re.sub(r'v\d+$', '', mid)
                    ids.add(std_id)
        except:
            continue
    return sorted(ids)

def update_files_with_abstracts(cache):
    count = 0
    for f in BY_DATE_DIR.glob("*.md"):
        content = f.read_text(encoding='utf-8')
        if "**Abstract**:" in content:
            continue
        # 定位所有论文块
        title_matches = list(re.finditer(r'^## .+?$', content, re.MULTILINE))
        if not title_matches:
            continue
        insertions = []
        for i, m in enumerate(title_matches):
            title_end = m.end()
            block_end = title_matches[i+1].start() if i+1 < len(title_matches) else len(content)
            block = content[title_end:block_end]
            tags_match = re.search(r'(-\s*\*\*Tags\*\*: .+?\n)', block)
            arxiv_match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', block)
            if not (tags_match and arxiv_match):
                continue
            arxiv_id = arxiv_match.group(1).strip()
            arxiv_id = re.sub(r'v\d+$', '', arxiv_id)
            if arxiv_id in cache:
                abstract = cache[arxiv_id]
                abstract_line = f"- **Abstract**: {abstract}\n"
                insert_pos = title_end + tags_match.end()
                insertions.append((insert_pos, abstract_line))
        if insertions:
            for pos, line in sorted(insertions, key=lambda x: x[0], reverse=True):
                content = content[:pos] + line + content[pos:]
            f.write_text(content, encoding='utf-8')
            count += 1
            print(f"[OK] {f.name}")
    print(f"共更新 {count} 个文件")

def main():
    print("=== 开始抓取最近30天论文摘要 ===")
    cache = load_cache()
    ids = collect_recent_ids(30)
    to_fetch = [i for i in ids if i not in cache]
    print(f"最近30天论文数: {len(ids)}")
    print(f"已有缓存: {len(ids) - len(to_fetch)}")
    print(f"待抓取: {len(to_fetch)}")

    if not to_fetch:
        print("无需抓取新摘要。")
    else:
        BATCH = 200
        total_batches = (len(to_fetch) + BATCH - 1) // BATCH
        for i in range(0, len(to_fetch), BATCH):
            batch = to_fetch[i:i+BATCH]
            print(f"[{datetime.now().strftime('%H:%M')}] 批次 {i//BATCH + 1}/{total_batches} ({len(batch)} 篇)")
            results = fetch_abstracts_batch(batch)
            cache.update(results)
            save_cache(cache)
            print(f"  获取到 {len(results)} 篇摘要")
            if i + BATCH < len(to_fetch):
                time.sleep(3)
        print("摘要抓取完成。")

    print("\n正在更新日期文件...")
    update_files_with_abstracts(cache)
    print("全部完成！")

if __name__ == "__main__":
    main()
