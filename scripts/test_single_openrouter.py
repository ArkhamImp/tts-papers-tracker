#!/usr/bin/env python3
import json, re, requests, fitz
from pathlib import Path
from datetime import datetime, timedelta

# 加载配置（使用 OpenRouter）
def load_config():
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    with open(config_path, 'r', encoding='utf-8-sig') as f:  # 处理 BOM/编码
        cfg = json.load(f)
    openrouter = cfg["models"]["providers"]["openrouter"]
    return {
        "api_key": openrouter["apiKey"],
        "base_url": openrouter["baseUrl"],
        "model": "arcee-ai/trinity-large-preview:free"
    }

config = load_config()
print("模型:", config["model"])
print("Base URL:", config["base_url"])

# 选一篇简单论文测试（不下载PDF）
arxiv_id = "2601.05911"
# 从 README 获取标题和作者
readme = Path("papers/raw/tts-arxiv-daily/README.md").read_text(encoding='utf-8')
for line in readme.splitlines():
    if arxiv_id in line:
        cols = [c.strip() for c in line.split('|')]
        title = cols[2].replace('**','').strip()
        authors = cols[3].replace('**','').strip()
        date = cols[1].replace('**','').strip()
        break
else:
    raise ValueError("Paper not found")

# 从摘要缓存获取摘要
abstracts = json.load(open('papers/processed/abstracts_cache.json'))
abstract = None
for k, v in abstracts.items():
    if k.startswith(arxiv_id.split('.')[0]) or k == arxiv_id:
        abstract = v
        break
if not abstract:
    print("无摘要缓存，跳过")
    exit(0)

paper = {"arxiv_id": arxiv_id, "title": title, "authors": authors, "abstract": abstract}

prompt = f"""Analyze this TTS/audio paper:

Title: {paper['title']}
Authors: {paper['authors']}
arXiv ID: {paper['arxiv_id']}
Abstract: {paper.get('abstract', 'No abstract')}

Provide analysis in pure JSON (no markdown) with these fields:
{{
  "tldr": "one-sentence summary",
  "core_contribution": "main contribution",
  "methodology": "how they did it, technical approach",
  "key_findings": "main results, experiments, metrics",
  "limitations": "limitations or weaknesses",
  "future_work": "future directions mentioned",
  "evaluation": "weak|medium|strong",
  "rating": 1-10
}}

Important: Output only the JSON object. Do not include extra text."""

url = f"{config['base_url']}/chat/completions"
headers = {
    "Authorization": f"Bearer {config['api_key']}",
    "Content-Type": "application/json"
}
payload = {
    "model": config["model"],
    "messages": [{"role": "user", "content": prompt}],
    "temperature": 0.3,
    "max_tokens": 1024
}

print("Calling OpenRouter API...")
resp = requests.post(url, json=payload, headers=headers, timeout=120)
print("Status:", resp.status_code)
if resp.status_code == 200:
    content = resp.json()["choices"][0]["message"]["content"]
    print("Response:", content[:500])
    # Try parse
    m = re.search(r'\{.*\}', content, re.DOTALL)
    if m:
        analysis = json.loads(m.group(0))
        print("Parsed fields:", list(analysis.keys()))
else:
    print("Error response:", resp.text[:500])
