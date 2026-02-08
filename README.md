# Bangla News Avatar (Aggregator + Sarvam Bulbul TTS)

A practical CLI for your idea:

- aggregate Bangla headlines from multiple sources,
- keep tone neutral (avoid sensational style),
- auto-fit script length to about **1–1.5 minutes**,
- synthesize speech with **Sarvam Bulbul** using **Bengali (`bn-IN`)** and **Aayan** voice.

## Quick start

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

## When RSS is blocked or unstable

Use local headline input (one headline per line):

```bash
python bangla_news_avatar.py \
  --headlines-file my_headlines.txt \
  --no-feed \
  --generate-audio \
  --output-audio headlines_bn.wav
```

## Duration controls (1–1.5 min target)

The script auto-selects headline count to hit target duration.

- `--target-seconds-min` default: `60`
- `--target-seconds-max` default: `90`
- `--min-headlines` default: `6`
- `--max-headlines` default: `14`

## CLI options

```text
--feeds URL [URL ...]         RSS/Atom sources
--headlines-file PATH         Local UTF-8 headlines file (one per line)
--no-feed                     Skip network feed fetch
--min-headlines N             Minimum headlines in final script
--max-headlines N             Maximum headlines in final script
--target-seconds-min N        Minimum target duration seconds
--target-seconds-max N        Maximum target duration seconds
--output-script PATH          Save generated bulletin text
--generate-audio              Call Sarvam TTS and save audio
--output-audio PATH           Audio output path
--sarvam-api-key KEY          API key (or use SARVAM_API_KEY env var)
--sarvam-endpoint URL         TTS endpoint (default: https://api.sarvam.ai/text-to-speech)
--model NAME                  Model (default: bulbul:v2)
--language-code CODE          Language code (default: bn-IN)
--speaker NAME                Voice (default: Aayan)
--sample-rate HZ              Sample rate (default: 22050)
```

## Notes

- The tool removes common sensational patterns but does not replace human editorial review.
- Keep feed sources curated and trusted before publishing.
