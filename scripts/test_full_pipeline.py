#!/usr/bin/env python3
import json, re, requests, fitz, time
from pathlib import Path
from datetime import datetime, timedelta

# config
home = Path.home()
config_path = home / ".openclaw" / "openclaw.json"
with open(config_path) as f:
    cfg = json.load(f)
deepseek = cfg["models"]["providers"]["deepseek"]
config = {
    "api_key": deepseek["apiKey"],
    "base_url": deepseek["baseUrl"],
    "model": deepseek["models"][0]["id"]
}

# caches
abstracts = json.load(open('papers/processed/abstracts_cache.json'))
# normalize abstracts keys
abstracts_std = {}
for k,v in abstracts.items():
    std = re.sub(r'v\d+$', '', k)
    abstracts_std[std] = v
analysis_cache = {}
pdf_cache = Path('papers/processed/pdf_cache')
pdf_cache.mkdir(exist_ok=True)
pdf_text_cache_path = Path('papers/processed/pdf_text_cache.json')
if pdf_text_cache_path.exists():
    pdf_text_cache = json.load(open(pdf_text_cache_path))
else:
    pdf_text_cache = {}

# Build paper dict from README
raw = Path('papers/raw/tts-arxiv-daily/README.md').read_text()
papers_by_id = {}
for line in raw.splitlines():
    if not line.strip().startswith('|') or 'Publish Date' in line or '---' in line: continue
    cols = [c.strip() for c in line.split('|')]
    if len(cols) < 6: continue
    date_str = cols[1].replace('**','').strip()
    title = cols[2].replace('**','').strip()
    authors = cols[3].replace('**','').strip()
    pdf_col = cols[4]
    m = re.search(r'https?://arxiv\.org/abs/([^\s)\]]+)', pdf_col)
    if m:
        arxiv_id = re.sub(r'v\d+$','', m.group(1))
        papers_by_id[arxiv_id] = {'title':title,'authors':authors,'date':date_str}

# pick recent paper within 30 days
cutoff = (datetime.now() - timedelta(days=30)).date()
candidates = []
for aid, p in papers_by_id.items():
    try:
        d = datetime.strptime(p['date'], '%Y-%m-%d').date()
        if d >= cutoff and aid in abstracts_std and aid not in analysis_cache:
            candidates.append(aid)
    except: pass
print(f"Candidates: {len(candidates)}")
if not candidates:
    print("No candidate, exit")
    exit(0)
test_id = candidates[0]
paper = papers_by_id[test_id]
paper['arxiv_id'] = test_id
paper['abstract'] = abstracts_std[test_id]
print(f"Testing paper: {test_id} - {paper['title'][:60]}")

# Get PDF text
if test_id in pdf_text_cache:
    pdf_text = pdf_text_cache[test_id]
    print("Loaded PDF text from cache.")
else:
    pdf_path = pdf_cache / f"{test_id}.pdf"
    if not pdf_path.exists():
        print("Downloading PDF...")
        url = f"https://arxiv.org/pdf/{test_id}.pdf"
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        pdf_path.write_bytes(r.content)
    # extract sections
    doc = fitz.open(pdf_path)
    txt = "\n".join(page.get_text() for page in doc)
    sections = {"method":"","experiment":"","results":"","conclusion":""}
    lines = txt.split('\n')
    cur = None
    for line in lines:
        low = line.lower().strip()
        if any(k in low for k in ["method","approach","model","architecture"]):
            cur = "method"
        elif any(k in low for k in ["experiment","evaluation","setup","dataset"]):
            cur = "experiment"
        elif any(k in low for k in ["result","findings","performance"]):
            cur = "result"
        elif any(k in low for k in ["conclusion","discussion","future work"]):
            cur = "conclusion"
        else:
            cur = None
        if cur and line.strip():
            sections[cur] += line + "\n"
    combined = ""
    for sec in ["method","experiment","result","conclusion"]:
        if sections[sec]:
            combined += f"\n=== {sec.upper()} ===\n{sections[sec]}\n"
    combined = combined[:8000]
    pdf_text = combined
    pdf_text_cache[test_id] = pdf_text
    with open(pdf_text_cache_path, 'w', encoding='utf-8') as f:
        json.dump(pdf_text_cache, f, ensure_ascii=False, indent=2)
    print(f"Extracted PDF text length: {len(pdf_text)}")

# Analyze via DeepSeek
prompt = f"""Analyze this TTS/audio paper:

Title: {paper['title']}
Authors: {paper['authors']}
arXiv ID: {paper['arxiv_id']}
Abstract: {paper.get('abstract', 'No abstract')}

Full text excerpts (key sections):
{pdf_text}

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

Output only the JSON object."""
headers = {"Authorization": f"Bearer {config['api_key']}", "Content-Type": "application/json"}
resp = requests.post(config['base_url']+'/chat/completions', json={"model":config["model"],"messages":[{"role":"user","content":prompt}],"temperature":0.3,"max_tokens":1024}, headers=headers, timeout=120)
print("API status:", resp.status_code)
if resp.status_code != 200:
    print("Error:", resp.text)
    exit(1)
content = resp.json()['choices'][0]['message']['content']
print("Response snippet:", content[:300])
m = re.search(r'\{.*\}', content, re.DOTALL)
if m:
    analysis = json.loads(m.group(0))
    print("Parsed analysis fields:", list(analysis.keys()))
    # Save to cache
    analysis_cache[test_id] = analysis
    with open('papers/processed/analysis_cache.json', 'w', encoding='utf-8') as f:
        json.dump(analysis_cache, f, ensure_ascii=False, indent=2)
    print("Analysis saved.")
else:
    print("No JSON found.")
