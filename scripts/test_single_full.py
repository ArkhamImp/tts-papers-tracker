#!/usr/bin/env python3
import json, re, requests, fitz
from pathlib import Path
from datetime import datetime, timedelta
from papers.scripts.analyze_papers import load_config, load_json, save_json, download_pdf, extract_key_sections, call_llm, build_paper_dict

# 准备环境
RAW_DIR = Path("papers/raw/tts-arxiv-daily")
PROCESSED_DIR = Path("papers/processed")
ABSTRACT_CACHE = PROCESSED_DIR / "abstracts_cache.json"
ANALYSIS_CACHE = PROCESSED_DIR / "analysis_cache.json"
PDF_TEXT_CACHE = load_json(PROCESSED_DIR / "pdf_text_cache.json")

# 标准化 abstracts
raw_abstracts = load_json(ABSTRACT_CACHE)
abstracts = {}
for k, v in raw_abstracts.items():
    std_k = re.sub(r'v\d+$', '', k)
    abstracts[std_k] = v

analysis_cache = load_json(ANALYSIS_CACHE)
papers_by_id = build_paper_dict()

# 找一个最近30天内且未分析的
cutoff = (datetime.now() - timedelta(days=30)).date()
candidates = []
for aid in abstracts:
    if aid in analysis_cache:
        continue
    p = papers_by_id.get(aid)
    if not p or 'date' not in p:
        continue
    try:
        d = datetime.strptime(p['date'], "%Y-%m-%d").date()
        if d >= cutoff:
            candidates.append(aid)
    except:
        pass
if not candidates:
    print("无候选论文")
    exit(0)
test_id = candidates[0]
paper = papers_by_id[test_id].copy()
paper['arxiv_id'] = test_id
paper['abstract'] = abstracts[test_id]
print(f"测试论文: {test_id} - {paper['title'][:60]}")

config = load_config()
print(f"使用模型: {config['model']}")

# 处理 PDF
pdf_text = PDF_TEXT_CACHE.get(test_id)
if not pdf_text:
    print("无 PDF 缓存，下载并提取...")
    try:
        pdf_path = download_pdf(test_id)
        pdf_text = extract_key_sections(pdf_path, max_tokens=2000)
        PDF_TEXT_CACHE[test_id] = pdf_text
        save_json(PDF_TEXT_CACHE, PROCESSED_DIR / "pdf_text_cache.json")
        print(f"PDF 文本长度: {len(pdf_text)}")
    except Exception as e:
        print(f"PDF 失败: {e}")
        pdf_text = ""
else:
    print("使用 PDF 缓存")

# 分析
print("开始分析...")
result = call_llm(
    f"""Analyze this TTS/audio paper:

Title: {paper['title']}
Authors: {paper['authors']}
arXiv ID: {paper['arxiv_id']}
Abstract: {paper.get('abstract', 'No abstract')}
{f'Full text excerpts:\n{pdf_text}' if pdf_text else ''}

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

Important: Output only the JSON object.""",
    config["model"],
    config["api_key"],
    config["base_url"]
)
print("LLM 输出:", result[:500])

# 解析并保存
m = re.search(r'\{.*\}', result, re.DOTALL)
if m:
    analysis = json.loads(m.group(0))
    print("解析成功，字段:", list(analysis.keys()))
    analysis_cache[test_id] = analysis
    save_json(analysis_cache, ANALYSIS_CACHE)
    print("已保存到分析缓存")
else:
    print("无有效 JSON")
