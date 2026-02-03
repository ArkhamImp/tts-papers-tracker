#!/usr/bin/env python3
import json, requests, re, sys
from pathlib import Path

abstracts = json.load(open('papers/processed/abstracts_cache.json'))
raw = Path('papers/raw/tts-arxiv-daily/README.md').read_text()
lines = raw.splitlines()
papers_by_id = {}
for line in lines:
    if not line.strip().startswith('|'): continue
    if 'Publish Date' in line or '---' in line: continue
    cols = [c.strip() for c in line.split('|')]
    if len(cols) < 6: continue
    title = cols[2].replace('**','').strip()
    authors = cols[3].replace('**','').strip()
    pdf_col = cols[4]
    m = re.search(r'https?://arxiv\.org/abs/([^\s)\]]+)', pdf_col)
    if m:
        arxiv_id = re.sub(r'v\d+$','',m.group(1))
        papers_by_id[arxiv_id] = {'title':title,'authors':authors}

paper_id = '2601.22873'
paper = papers_by_id.get(paper_id)
if not paper:
    print('Paper not found')
    sys.exit(1)
paper['arxiv_id'] = paper_id
paper['abstract'] = abstracts.get(paper_id, '')

config = {
    'api_key': 'sk-196e86674e13423890041a9f6e936ea0',
    'base_url': 'https://api.deepseek.com',
    'model': 'deepseek-chat'
}

prompt = f"""Analyze this TTS/audio paper:

Title: {paper['title']}
Authors: {paper['authors']}
arXiv ID: {paper['arxiv_id']}
Abstract: {paper['abstract']}

Provide analysis in pure JSON (no markdown) with these fields:
{{
  "tldr": "one-sentence summary",
  "core_contribution": "main contribution",
  "methodology": "how they did it",
  "key_findings": "main results",
  "limitations": "limitations",
  "future_work": "future directions",
  "evaluation": "weak|medium|strong",
  "rating": 1-10
}}

Output only the JSON object."""

resp = requests.post(
    config['base_url'] + '/chat/completions',
    json={
        'model': config['model'],
        'messages': [{'role':'user','content':prompt}],
        'temperature': 0.3,
        'max_tokens': 1024
    },
    headers={'Authorization': f'Bearer {config["api_key"]}', 'Content-Type': 'application/json'},
    timeout=60
)
print('Status:', resp.status_code)
if resp.status_code != 200:
    print('Error', resp.text)
    sys.exit(1)
out = resp.json()
content = out['choices'][0]['message']['content']
print('Response snippet:', content[:200])
m = re.search(r'\{.*\}', content, re.DOTALL)
if m:
    analysis = json.loads(m.group(0))
    print('Parsed analysis:')
    print(json.dumps(analysis, ensure_ascii=False, indent=2))
    # Save to a temp file
    cache = {}
    if Path('papers/processed/analysis_cache.json').exists():
        with open('papers/processed/analysis_cache.json','r') as f: cache = json.load(f)
    cache[paper_id] = analysis
    with open('papers/processed/analysis_cache.json','w') as f: json.dump(cache, f, ensure_ascii=False, indent=2)
    print('Saved analysis to cache.')
else:
    print('No JSON found')
