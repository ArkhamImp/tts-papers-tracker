#!/usr/bin/env python3
"""
为 TTS 论文生成 LLM 分析（基于摘要 + PDF 全文关键部分）
"""

import json
import re
import time
import requests
import fitz  # PyMuPDF
from pathlib import Path
from datetime import datetime, timedelta

# 路径定义
RAW_DIR = Path("papers/raw/tts-arxiv-daily")
PROCESSED_DIR = Path("papers/processed")
ABSTRACT_CACHE = PROCESSED_DIR / "abstracts_cache.json"
ANALYSIS_CACHE = PROCESSED_DIR / "analysis_cache.json"
PDF_CACHE = PROCESSED_DIR / "pdf_cache"  # 存放下载的 PDF
PDF_CACHE.mkdir(parents=True, exist_ok=True)
PDF_TEXT_CACHE = PROCESSED_DIR / "pdf_text_cache.json"  # 缓存提取的全文文本

# 获取 DeepSeek API Key 和 URL
def load_config():
    home = Path.home()
    config_path = home / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    openrouter = cfg["models"]["providers"]["openrouter"]
    return {
        "api_key": openrouter["apiKey"],
        "base_url": openrouter["baseUrl"],
        "model": "arcee-ai/trinity-large-preview:free"
    }

def load_json(path):
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def download_pdf(arxiv_id):
    """下载 PDF 到本地缓存，返回文件路径"""
    pdf_path = PDF_CACHE / f"{arxiv_id}.pdf"
    if pdf_path.exists():
        return pdf_path
    url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    print(f"    下载 PDF: {arxiv_id}")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    pdf_path.write_bytes(resp.content)
    return pdf_path

def extract_key_sections(pdf_path, max_tokens=3000):
    """从 PDF 中提取方法、实验、结果等关键部分"""
    doc = fitz.open(pdf_path)
    text = []
    for page in doc:
        page_text = page.get_text()
        text.append(page_text)
    full_text = "\n".join(text)

    # 简单启发式：查找章节标题
    sections = {
        "method": "",
        "experiment": "",
        "results": "",
        "conclusion": ""
    }
    lines = full_text.split('\n')
    current_section = None
    for line in lines:
        line_lower = line.lower().strip()
        # 检测方法章节
        if any(k in line_lower for k in ["method", "approach", "model", "architecture"]):
            current_section = "method"
        elif any(k in line_lower for k in ["experiment", "evaluation", "setup", "dataset"]):
            current_section = "experiment"
        elif any(k in line_lower for k in ["result", "findings", "performance"]):
            current_section = "results"
        elif any(k in line_lower for k in ["conclusion", "discussion", "future work"]):
            current_section = "conclusion"
        else:
            current_section = None

        if current_section and line.strip():
            sections[current_section] += line + "\n"

    # 合并 sections，截断到 token 限制（粗略按字符算，1 token ~= 4 chars）
    combined = ""
    for key in ["method", "experiment", "results", "conclusion"]:
        if sections[key]:
            combined += f"\n=== {key.upper()} ===\n{sections[key]}\n"
    if len(combined) > max_tokens * 4:
        combined = combined[:max_tokens * 4]
    return combined.strip()

def load_pdf_text_cache():
    if PDF_TEXT_CACHE.exists():
        with open(PDF_TEXT_CACHE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def call_llm(prompt, model, api_key, base_url):
    url = f"{base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1024
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

def build_paper_dict():
    """从 README 构建 arxiv_id -> {title, authors} 映射"""
    raw_readme = RAW_DIR / "README.md"
    if not raw_readme.exists():
        raise FileNotFoundError(f"Missing: {raw_readme}")
    lines = raw_readme.read_text(encoding='utf-8').splitlines()
    papers = {}
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
        m = re.search(r'https?://arxiv\.org/abs/([^\s)\]]+)', pdf_col)
        if m:
            arxiv_id = re.sub(r'v\d+$', '', m.group(1))
            papers[arxiv_id] = {
                "title": title,
                "authors": authors,
                "date": date_str
            }
    return papers

def analyze_paper(paper, config, pdf_text_cache=None):
    """调用 DeepSeek 分析单篇论文（可选包含 PDF 全文）"""
    if pdf_text_cache is None:
        pdf_text_cache = {}

    arxiv_id = paper['arxiv_id']
    pdf_text = pdf_text_cache.get(arxiv_id, "")

    prompt = f"""Analyze this TTS/audio paper:

Title: {paper['title']}
Authors: {paper['authors']}
arXiv ID: {arxiv_id}
Abstract: {paper.get('abstract', 'No abstract')}
"""
    if pdf_text:
        prompt += f"\nFull text excerpts (key sections):\n{pdf_text}\n"
    prompt += """
Provide analysis in pure JSON (no markdown) with these fields:
{
  "tldr": "one-sentence summary",
  "core_contribution": "main contribution",
  "methodology": "how they did it, technical approach",
  "key_findings": "main results, experiments, metrics",
  "limitations": "limitations or weaknesses",
  "future_work": "future directions mentioned",
  "evaluation": "weak|medium|strong (based on experimental rigor)",
  "rating": integer 1-10
}

Important: Output only the JSON object. Do not include extra text."""
    try:
        output = call_llm(prompt, config["model"], config["api_key"], config["base_url"])
        # 提取 JSON 块
        json_match = re.search(r'\{[\s\S]*\}', output)
        if json_match:
            analysis = json.loads(json_match.group(0))
            # 验证必要字段
            require_fields = ["tldr", "core_contribution", "methodology", "key_findings", "limitations", "future_work", "evaluation", "rating"]
            for k in require_fields:
                if k not in analysis:
                    print(f"  警告: {arxiv_id} 缺失字段 {k}")
                    return None
            return analysis
        else:
            print(f"  解析失败: {arxiv_id} 无 JSON")
            return None
    except Exception as e:
        print(f"  分析异常 {arxiv_id}: {e}")
        return None

def main():
    raw_abstracts = load_json(ABSTRACT_CACHE)
    # 标准化 abstracts 的 key（去掉版本号）
    abstracts = {}
    for k, v in raw_abstracts.items():
        std_k = re.sub(r'v\d+$', '', k)
        abstracts[std_k] = v
    analysis_cache = load_json(ANALYSIS_CACHE)
    papers_by_id = build_paper_dict()
    pdf_text_cache = load_pdf_text_cache()

    # 需要分析的论文 ID（有摘要且未分析）
    to_analyze = [aid for aid in abstracts.keys() if aid not in analysis_cache]
    print(f"[{datetime.now()}] 总论文: {len(abstracts)}，待分析: {len(to_analyze)}")
    if not to_analyze:
        print("无需新分析")
        return

    # 只分析最近 30 天的论文，避免过多请求
    cutoff_date = (datetime.now() - timedelta(days=30)).date()
    recent_ids = []
    for aid in to_analyze:
        p = papers_by_id.get(aid)
        if p and 'date' in p:
            try:
                pdate = datetime.strptime(p['date'], "%Y-%m-%d").date()
                if pdate >= cutoff_date:
                    recent_ids.append(aid)
            except:
                pass
    print(f"最近30天内论文: {len(recent_ids)}")

    config = load_config()
    count = 0
    batch_size = 3  # 减小批次，因为下载 PDF 会增加耗时

    for i in range(0, len(recent_ids), batch_size):
        batch = recent_ids[i:i+batch_size]
        for aid in batch:
            if aid not in papers_by_id:
                print(f"  跳过 {aid}: 未在 README 中找到元数据")
                continue
            paper = papers_by_id[aid]
            paper['arxiv_id'] = aid
            paper['abstract'] = abstracts[aid]

            # 获取或提取 PDF 关键文本
            pdf_text = pdf_text_cache.get(aid)
            if not pdf_text:
                try:
                    pdf_path = download_pdf(aid)
                    pdf_text = extract_key_sections(pdf_path, max_tokens=2000)
                    pdf_text_cache[aid] = pdf_text
                    save_json(pdf_text_cache, PDF_TEXT_CACHE)
                except Exception as e:
                    print(f"  PDF处理失败 {aid}: {e}")
                    pdf_text = None

            print(f"  分析中: {aid} - {paper['title'][:60]}...")
            analysis = analyze_paper(paper, config, pdf_text_cache if pdf_text else None)
            if analysis:
                analysis_cache[aid] = analysis
                count += 1
            time.sleep(2)  # 礼貌延迟
        # 中途保存
        save_json(analysis_cache, ANALYSIS_CACHE)
        print(f"  批次 {i//batch_size + 1}: 完成 {count} (累计)")
    save_json(analysis_cache, ANALYSIS_CACHE)
    print(f"[{datetime.now()}] 分析完成，总计新增 {count} 篇")

if __name__ == "__main__":
    main()
