#!/usr/bin/env python3
"""统计需要分析的论文数量"""

import json
from pathlib import Path

PROCESSED_DIR = Path("papers/processed")
ABSTRACT_CACHE = PROCESSED_DIR / "abstracts_cache.json"
ANALYSIS_CACHE = PROCESSED_DIR / "analysis_cache.json"

def load_json(path):
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

abstracts = load_json(ABSTRACT_CACHE)
analyses = load_json(ANALYSIS_CACHE)

# 标准化键名（去掉版本号）
abstracts_std = {}
for k, v in abstracts.items():
    std_k = k.rstrip('v0123456789')
    abstracts_std[std_k] = v

analyzed_ids = set(analyses.keys())
total_abstracts = len(abstracts_std)
analyzed_count = len([aid for aid in abstracts_std.keys() if aid in analyzed_ids])
pending_count = total_abstracts - analyzed_count

print(f"总论文数: {total_abstracts}")
print(f"已分析: {analyzed_count}")
print(f"待分析: {pending_count}")
print()

if pending_count > 0:
    print("待分析的论文 ID:")
    for aid in sorted(abstracts_std.keys()):
        if aid not in analyzed_ids:
            title = abstracts_std[aid].get('title', 'N/A') if isinstance(abstracts_std[aid], dict) else 'N/A'
            print(f"  {aid}: {title[:80]}")
else:
    print("所有论文都已分析完成！")
