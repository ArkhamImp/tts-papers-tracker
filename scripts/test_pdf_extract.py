#!/usr/bin/env python3
import fitz, requests, sys
from pathlib import Path

arxiv_id = "2601.22873"
url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
pdf_path = Path(f"papers/processed/pdf_cache/{arxiv_id}.pdf")
if not pdf_path.exists():
    print(f"Downloading {arxiv_id}...")
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    pdf_path.write_bytes(r.content)
    print("Downloaded.")
else:
    print("PDF already exists.")

doc = fitz.open(pdf_path)
text = []
for page in doc:
    text.append(page.get_text())
full = "\n".join(text)
print(f"Full text length: {len(full)}")
# Show first 500 chars
print(full[:500])

# Simple section extraction heuristic
sections = {"method":"", "experiment":"", "results":"", "conclusion":""}
lines = full.split('\n')
current = None
for line in lines:
    line_lower = line.lower().strip()
    if any(k in line_lower for k in ["method", "approach", "model", "architecture"]):
        current = "method"
    elif any(k in line_lower for k in ["experiment", "evaluation", "setup", "dataset"]):
        current = "experiment"
    elif any(k in line_lower for k in ["result", "findings", "performance"]):
        current = "results"
    elif any(k in line_lower for k in ["conclusion", "discussion", "future work"]):
        current = "conclusion"
    else:
        current = None
    if current and line.strip():
        sections[current] += line + "\n"

combined = ""
for key in ["method", "experiment", "results", "conclusion"]:
    if sections[key]:
        combined += f"\n=== {key.upper()} ===\n{sections[key]}\n"
combined = combined[:8000]  # limit tokens
print("Extracted sections length:", len(combined))
print(combined[:1000])
