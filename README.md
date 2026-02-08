# Bangla News Avatar (Aggregator + Sarvam Bulbul TTS)

A practical toolset for your idea:

- aggregate Bangla headlines,
- keep tone neutral (avoid sensational style),
- auto-fit script length to about **1–1.5 minutes**,
- synthesize speech with **Sarvam Bulbul** using **Bengali (`bn-IN`)** and **Aayan** voice,
- and now a **slick web UI** for fast newsroom workflow.

## Option A: Use the new Web UI (recommended)

### Start server

```bash
cd /workspace/News
python web_ui.py
```

Open: `http://localhost:8000`

### Web UI features

- Paste/edit headlines directly (one per line)
- Tune min/max headlines and duration range
- Generate clean Bangla script instantly
- Optional one-click Sarvam audio generation with API key input
- Download generated WAV from the interface

---

## Option B: CLI usage

### 1) Generate a Bangla bulletin script

```bash
python bangla_news_avatar.py --output-script headlines_bn.txt
```

### 2) Generate audio with Sarvam Bulbul

```bash
export SARVAM_API_KEY="<your_sarvam_api_key>"
python bangla_news_avatar.py \
  --generate-audio \
  --model bulbul:v2 \
  --language-code bn-IN \
  --speaker Aayan \
  --output-audio headlines_bn.wav
```

### 3) When RSS is blocked or unstable

Use local headline input (one headline per line):

```bash
python bangla_news_avatar.py \
  --headlines-file my_headlines.txt \
  --no-feed \
  --generate-audio \
  --output-audio headlines_bn.wav
```

## Duration controls (1–1.5 min target)

- `--target-seconds-min` default: `60`
- `--target-seconds-max` default: `90`
- `--min-headlines` default: `6`
- `--max-headlines` default: `14`

## Notes

- The tool removes common sensational patterns but does not replace human editorial review.
- Keep feed sources curated and trusted before publishing.
