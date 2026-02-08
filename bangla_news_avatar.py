#!/usr/bin/env python3
"""Generate a neutral Bangla top-news bulletin and synthesize it with Sarvam Bulbul TTS."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Iterable

DEFAULT_FEEDS = [
    "https://www.prothomalo.com/feed/",
    "https://www.thedailystar.net/frontpage/rss.xml",
    "https://bangla.bdnews24.com/?widgetName=rssfeed&widgetId=1151&getXmlFeed=true",
    "https://www.kalerkantho.com/rss.xml",
]

# Terms to reduce hype-heavy writing in final spoken script.
SENSATIONAL_PATTERNS = [
    r"\bexclusive\b",
    r"\bshocking\b",
    r"\bviral\b",
    r"অবিশ্বাস্য",
    r"চাঞ্চল্য(?:কর)?",
    r"তোলপাড়",
    r"বিস্ফোরক",
    r"এক্সক্লুসিভ",
    r"চমকে\s*দেবে",
    r"দেখলে\s*অবাক\s*হবেন",
]


@dataclass
class NewsItem:
    title: str
    source: str
    link: str
    published: dt.datetime | None


@dataclass
class TTSConfig:
    api_key: str
    endpoint: str = "https://api.sarvam.ai/text-to-speech"
    model: str = "bulbul:v2"
    language_code: str = "bn-IN"
    speaker: str = "Aayan"
    sample_rate: int = 22050


def fetch_feed(url: str, timeout_s: int = 15) -> list[NewsItem]:
    req = urllib.request.Request(url, headers={"User-Agent": "bangla-news-avatar/1.1"})
    with urllib.request.urlopen(req, timeout=timeout_s) as response:
        body = response.read()

    root = ET.fromstring(body)
    items: list[NewsItem] = []

    for item in root.findall(".//item"):
        title = get_text(item, "title")
        link = get_text(item, "link")
        source = get_text(item, "source") or urllib.parse.urlparse(url).netloc
        published = parse_pubdate(get_text(item, "pubDate") or get_text(item, "published"))
        if title:
            items.append(NewsItem(title=normalize_text(title), source=source, link=link, published=published))

    if items:
        return items

    # Atom fallback
    ns = "{http://www.w3.org/2005/Atom}"
    for entry in root.findall(f".//{ns}entry"):
        title = get_text(entry, f"{ns}title")
        link = ""
        for link_node in entry.findall(f"{ns}link"):
            href = link_node.attrib.get("href")
            rel = link_node.attrib.get("rel", "alternate")
            if href and rel in {"alternate", ""}:
                link = href
                break

        source = urllib.parse.urlparse(url).netloc
        published = parse_pubdate(get_text(entry, f"{ns}updated") or get_text(entry, f"{ns}published"))
        if title:
            items.append(NewsItem(title=normalize_text(title), source=source, link=link, published=published))

    return items


def load_manual_headlines(path: str) -> list[NewsItem]:
    """Load headlines from UTF-8 text file (one headline per line)."""
    out: list[NewsItem] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            title = normalize_text(line)
            if title:
                out.append(NewsItem(title=title, source="manual", link="", published=None))
    return out


def get_text(node: ET.Element, tag: str) -> str:
    child = node.find(tag)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def parse_pubdate(value: str) -> dt.datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        pass

    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def normalize_text(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def neutralize_headline(title: str) -> str:
    cleaned = title
    for pattern in SENSATIONAL_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"[!]{1,}", "", cleaned)
    cleaned = re.sub(r"[?]{2,}", "?", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,-")
    return cleaned or "সংবাদ আপডেট"


def rank_news(items: Iterable[NewsItem]) -> list[NewsItem]:
    now = dt.datetime.now(dt.timezone.utc)

    def score(item: NewsItem) -> tuple[int, int, int]:
        freshness = 0
        if item.published:
            ts = item.published if item.published.tzinfo else item.published.replace(tzinfo=dt.timezone.utc)
            age_hours = max((now - ts).total_seconds() / 3600.0, 0)
            freshness = max(0, int(96 - age_hours))

        source_weight = sum(ord(ch) for ch in item.source) % 13
        title_len = min(len(item.title), 120)
        return freshness, source_weight, title_len

    uniq: dict[str, NewsItem] = {}
    for item in items:
        key = re.sub(r"\W+", "", item.title.lower())
        if key and key not in uniq:
            uniq[key] = item

    return sorted(uniq.values(), key=score, reverse=True)


def build_script(items: list[NewsItem], headline_count: int) -> str:
    selected = items[:headline_count]
    today_bn = dt.datetime.now().strftime("%d-%m-%Y")

    lines = [
        f"আজকের শীর্ষ খবর, তারিখ {today_bn}।",
        "সংবাদের মূল তথ্যগুলো সংক্ষেপে তুলে ধরা হলো।",
    ]

    for idx, item in enumerate(selected, start=1):
        lines.append(f"খবর {idx}: {neutralize_headline(item.title)}।")

    lines.append("এগুলো ছিল এই মুহূর্তের প্রধান খবর। বিস্তারিত জানুন নির্ভরযোগ্য সংবাদমাধ্যম থেকে।")
    return " ".join(lines)


def estimate_duration_seconds(script: str, words_per_minute: int = 118) -> float:
    words = len(script.split())
    return (words / max(words_per_minute, 1)) * 60.0


def choose_headline_count(ranked_items: list[NewsItem], minimum: int, maximum: int, target_min_s: int, target_max_s: int) -> int:
    if not ranked_items:
        return 0

    min_count = max(1, minimum)
    max_count = max(min_count, min(maximum, len(ranked_items)))

    best_count = min_count
    best_score = float("inf")
    target_mid = (target_min_s + target_max_s) / 2.0

    for count in range(min_count, max_count + 1):
        draft = build_script(ranked_items, count)
        duration = estimate_duration_seconds(draft)
        if target_min_s <= duration <= target_max_s:
            return count
        score = abs(duration - target_mid)
        if score < best_score:
            best_score = score
            best_count = count

    return best_count


def synthesize_tts(script: str, output_path: str, cfg: TTSConfig) -> None:
    payload = {
        "inputs": [script],
        "target_language_code": cfg.language_code,
        "speaker": cfg.speaker,
        "model": cfg.model,
        "speech_sample_rate": cfg.sample_rate,
        "enable_preprocessing": True,
    }

    # Sarvam examples typically use `api-subscription-key`; we also send bearer auth for compatibility.
    headers = {
        "Content-Type": "application/json",
        "api-subscription-key": cfg.api_key,
        "Authorization": f"Bearer {cfg.api_key}",
    }

    req = urllib.request.Request(
        cfg.endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=90) as response:
        content_type = response.headers.get("Content-Type", "")
        data = response.read()

    if "audio" in content_type:
        with open(output_path, "wb") as handle:
            handle.write(data)
        return

    parsed = json.loads(data.decode("utf-8"))
    audio_b64 = parsed.get("audios", [None])[0] or parsed.get("audio")
    if not audio_b64:
        raise RuntimeError(f"TTS response missing audio field: {parsed}")

    with open(output_path, "wb") as handle:
        handle.write(base64.b64decode(audio_b64))


def run(args: argparse.Namespace) -> int:
    all_items: list[NewsItem] = []

    if args.headlines_file:
        all_items.extend(load_manual_headlines(args.headlines_file))

    if not args.no_feed:
        for feed_url in args.feeds:
            try:
                all_items.extend(fetch_feed(feed_url))
            except (urllib.error.URLError, ET.ParseError, TimeoutError) as exc:
                print(f"[warn] feed unavailable {feed_url}: {exc}", file=sys.stderr)

    if not all_items:
        print("No headlines found. Provide --headlines-file or enable reachable feeds.", file=sys.stderr)
        return 1

    ranked = rank_news(all_items)
    count = choose_headline_count(
        ranked,
        minimum=args.min_headlines,
        maximum=args.max_headlines,
        target_min_s=args.target_seconds_min,
        target_max_s=args.target_seconds_max,
    )
    script = build_script(ranked, count)
    duration = estimate_duration_seconds(script)

    print("\n=== Generated Bangla Headlines Script ===\n")
    print(script)
    print(f"\nEstimated duration: {duration:.1f} sec ({duration / 60:.2f} min), headlines used: {count}")

    if args.output_script:
        with open(args.output_script, "w", encoding="utf-8") as handle:
            handle.write(script + "\n")

    if args.generate_audio:
        api_key = args.sarvam_api_key or os.getenv("SARVAM_API_KEY")
        if not api_key:
            print("Missing SARVAM API key. Use --sarvam-api-key or SARVAM_API_KEY.", file=sys.stderr)
            return 2

        cfg = TTSConfig(
            api_key=api_key,
            endpoint=args.sarvam_endpoint,
            model=args.model,
            language_code=args.language_code,
            speaker=args.speaker,
            sample_rate=args.sample_rate,
        )

        try:
            synthesize_tts(script, args.output_audio, cfg)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
            print(f"Sarvam TTS HTTP error {exc.code}: {body}", file=sys.stderr)
            return 3
        except urllib.error.URLError as exc:
            print(f"Sarvam TTS network error: {exc}", file=sys.stderr)
            return 3

        print(f"Audio saved to {args.output_audio}")

    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--feeds", nargs="+", default=DEFAULT_FEEDS, help="RSS/Atom feed URLs")
    p.add_argument("--headlines-file", default="", help="Optional local UTF-8 file with one headline per line")
    p.add_argument("--no-feed", action="store_true", help="Skip online feeds (use with --headlines-file)")
    p.add_argument("--min-headlines", type=int, default=6)
    p.add_argument("--max-headlines", type=int, default=14)
    p.add_argument("--target-seconds-min", type=int, default=60)
    p.add_argument("--target-seconds-max", type=int, default=90)
    p.add_argument("--output-script", default="headlines_bn.txt")
    p.add_argument("--generate-audio", action="store_true")
    p.add_argument("--output-audio", default="headlines_bn.wav")
    p.add_argument("--sarvam-api-key", default="")
    p.add_argument("--sarvam-endpoint", default="https://api.sarvam.ai/text-to-speech")
    p.add_argument("--model", default="bulbul:v2")
    p.add_argument("--language-code", default="bn-IN")
    p.add_argument("--speaker", default="Aayan")
    p.add_argument("--sample-rate", type=int, default=22050)
    return p


if __name__ == "__main__":
    raise SystemExit(run(parser().parse_args()))
