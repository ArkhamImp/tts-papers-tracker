# 📚 TTS & Audio Papers Tracking System

## Daily Sources (Auto-Updating)

### 1. TTS-arxiv-daily (Primary)
- **URL**: https://github.com/liutaocode/TTS-arxiv-daily
- **Update Frequency**: Every 12 hours via GitHub Actions
- **Content**: Text-to-Speech, speech synthesis, voice cloning, expressive TTS, LLM-based audio generation
- **Format**: Markdown with date folders, each containing:
  - Paper title
  - Authors
  - arXiv ID and link
  - Optional GitHub links
- **Status**: ✅ **Added to tracking system** (2026-02-03)

### 2. ASR-TTS-paper-daily (Secondary)
- **URL**: https://github.com/halsay/ASR-TTS-paper-daily
- **Content**: Broader ASR/TTS coverage, chronological
- **Use Case**: Cross-validation and catching missed papers

### 3. VibeVoice & Industry Models (Manual)
- Microsoft VibeVoice: https://github.com/microsoft/VibeVoice
- NVIDIA NeMo: https://github.com/NVIDIA/NeMo
- FunAudioLLM: https://github.com/FunAudioLLM/Fun-ASR
- Parakeet (NIM): https://huggingface.co/nvidia/multitalker-parakeet-streaming-0.6b-v1

## Storage & Organization

```
workspace/papers/
├── raw/
│   └── tts-arxiv-daily/       # Cloned repo (auto-updated)
├── processed/
│   ├── by-date/
│   │   └── 2026-02-03.md      # Today's parsed papers (TTS only)
│   ├── by-topic/
│   │   ├── zero-shot.md
│   │   ├── expressive.md
│   │   ├── streaming.md
│   │   ├── long-context.md
│   │   ├── multilingual.md
│   │   └── codec.md
│   └── index.md               # Master index with tags, priorities
├── summaries/
│   ├── weekly/
│   │   └── 2026-W05.md        # Week 5 (Feb 3-9)
│   └── monthly/
└── README.md                   # This file
```

## Parsing Strategy

### Keywords to Flag (Priority Papers)
**High Priority (TTS Core):**
- `text-to-speech` / `TTS`
- `speech synthesis` / `voice synthesis`
- `neural codec` / `speech codec`
- `vocoder` / `neural vocoder`
- `flow matching` / `diffusion` (for TTS)
- `zero-shot TTS` / `voice cloning`
- `expressive TTS` / `emotional TTS`
- `prosody` / `intonation`
- `real-time TTS` / `streaming TTS` / `low-latency TTS`
- `long-context TTS` / `long-form synthesis`
- `multilingual TTS`
- `voice conversion`

**Medium Priority (Related):**
- `audio generation` / `speech generation`
- `LLM-based TTS` / `speech language model`
- `discrete tokens` / `semantic tokens`
- `acoustic tokens`
- `speech editing`
- `style control`
- `phonemizer` / `g2p`

**Low Priority (Skip unless breakthrough):**
- `ASR` / `speech recognition`
- `diarization` / `speaker separation`
- `voice activity detection`
- `speaker verification`
- `audio deepfake` / `synthetic speech detection`

### Excluded Keywords (Filter Out)
- `speaker diarization`
- `multi-speaker ASR`
- `speaker embedding` (unless in TTS context)
- `voice spoofing` / `anti-spoofing`
- `speech enhancement` (unless directly tied to TTS)

## Automation Plan

### Daily (via Heartbeat or Cron)
1. Pull latest from TTS-arxiv-daily
2. Parse today's markdown entries
3. Tag based on keywords
4. Append to `processed/by-date/YYYY-MM-DD.md`
5. Update `processed/index.md` with metadata

### Weekly Summary (Sunday)
- Generate report of new papers by topic
- Highlight top 5 most relevant to user's needs
- Identify trending techniques (e.g., flow matching, LLM integration)

### Monthly Digest
- Compare SOTA performance metrics if available
- Track open-source releases vs academic papers
- Note which projects become production-ready

## Integration with Current Workflow

### Link to Existing LLM TTS Doc
- Reference `LLM_TTS_Technologies_2024-2025.md` for comprehensive tech review
- New papers from daily tracking will feed into periodic updates of that document

### TTS Focus Areas
Track papers by these core TTS categories:

| Topic File | Focus | Key Papers |
|-----------|-------|------------|
| `zero-shot.md` | Voice cloning without fine-tuning | VALL-E, YourTTS, VoiceCraft |
| `expressive.md` | Emotion, prosody, style control | VibeVoice-TTS, Emotional TTS |
| `streaming.md` | Real-time, low-latency synthesis | VibeVoice-Realtime, Parakeet |
| `long-context.md` | >30s coherent generation | VibeVoice-ASR (TTS part), long-form TTS |
| `multilingual.md` | Cross-lingual voice synthesis | GLM-TTS, Qwen3-TTS, Omni-speech |
| `codec.md` | Neural codecs, tokenization | Mimi, EnCodec, DAC, SpeechTokenizer |

Each topic file contains:
- Paper citation (title, authors, arXiv)
- Key innovations
- Open-source status (code/model links)
- Performance metrics (if available)
- Production readiness assessment

## ✅ Implementation Complete

### Completed Tasks
- [x] Clone `TTS-arxiv-daily` into `workspace/papers/raw/`
- [x] Write parser (`parse_tts_papers.py`) extracting 1518 TTS-relevant papers
- [x] Apply keyword tagging (9 categories: zero-shot, expressive, streaming, long-context, multilingual, codec, llm-based, editing, synthesis, other)
- [x] Create by-date and by-topic organized files
- [x] Generate weekly summaries with highlights
- [x] Integrate highlights into `LLM_TTS_Technologies_2024-2025.md`
- [x] Set up automation (Windows Scheduled Tasks)

### Automation Configuration

| Task | Frequency | Script | Windows Task Name |
|------|-----------|--------|-------------------|
| Daily Parse | Every 12 hours | `parse_tts_papers.py` | `TTS-Papers-Parser` |
| Weekly Summary | Weekly (Sun 04:00) | `generate_weekly_summary.py` | `TTS-Weekly-Summary` |
| Monthly Summary | Monthly (1st 05:00) | `generate_monthly_summary.py` | `TTS-Monthly-Summary` |

### Output Structure
```
workspace/papers/
├── raw/tts-arxiv-daily/          # Source git clone (auto-updates)
├── processed/
│   ├── by-date/YYYY-MM-DD.md    # 1612 total dates (2017-2026)
│   ├── by-topic/*.md            # 9 category files
│   └── index.md                 # Master index with stats
├── summaries/
│   ├── weekly/YYYY-WWW.md      # Weekly reports (auto)
│   └── monthly/YYYY-MM.md      # Monthly reports (auto)
└── scripts/
    ├── parse_tts_papers.py
    ├── generate_weekly_summary.py
    └── generate_monthly_summary.py
```

### Integration Points
- **Main Document**: `LLM_TTS_Technologies_2024-2025.md` includes `<!-- LATEST_HIGHLIGHTS_START -->` section updated weekly with top papers.

### Future Enhancements
- [ ] Add email digest of weekly highlights
- [ ] Create RSS feed from highlights
- [ ] Implement incremental parsing (only new papers)
- [ ] Add search/indexing (ripgrep or whoosh)
- [ ] Track open-source releases vs academic papers

---
**Created**: 2026-02-03
**Status**: Planning phase, automation pending
