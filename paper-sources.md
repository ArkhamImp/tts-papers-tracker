# Paper Tracking Resources

## TTS/ASR/Audio Daily Papers

### Primary Sources
- **TTS-arxiv-daily**: https://github.com/liutaocode/TTS-arxiv-daily
  - Auto-updates every 12 hours via GitHub Actions
  - Covers: Text-to-Speech, speech synthesis, voice cloning, expressive TTS, audio generation
  - Format: Daily markdown with paper titles, authors, arXiv links
  - Integration: Can be cloned and parsed for automated tracking

### Complementary Repositories
- **ASR-TTS-paper-daily**: https://github.com/halsay/ASR-TTS-paper-daily
  - Chronological list of recent ASR/TTS papers
  - Good for cross-reference and broader coverage

### Official Model Hubs
- Hugging Face TTS models: https://huggingface.co/models?pipeline_tag=text-to-speech
- NVIDIA NeMo: https://github.com/NVIDIA/NeMo
- Microsoft VibeVoice: https://github.com/microsoft/VibeVoice
- FunAudioLLM (FunASR): https://github.com/FunAudioLLM/Fun-ASR

## Tracking Strategy

### 1. Daily Digest
```bash
# Clone and update daily
git clone https://github.com/liutaocode/TTS-arxiv-daily.git
cd TTS-arxiv-daily
git pull
# Parse today's entries from markdown files
```

### 2. Keyword Filters (for relevant papers)
- Streaming / Real-time
- Multi-speaker
- Diarization
- Zero-shot
- Low-latency
- Conversational
- Voice cloning
- LLM-based

### 3. Storage Structure
```
workspace/
├── papers/
│   ├── tt-track/
│   │   ├── 2026-02/
│   │   │   ├── 2026-02-03.md  # Papers from this date
│   │   │   └── summaries/
│   │   └── index.md           # Master index with tags
│   └── asr-track/
└── MEMORY.md
```

### 4. Automation Plan
- Add cron job to pull TTS-arxiv-daily every 12h
- Parse new entries matching keywords
- Append to daily markdown files
- Generate weekly summary reports

---
**Last Updated**: 2026-02-03
**Status**: Repository recorded, integration pending
