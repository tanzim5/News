#!/usr/bin/env python3
"""Minimal web UI server for Bangla News Avatar Studio."""

from __future__ import annotations

import json
import tempfile
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from bangla_news_avatar import (
    TTSConfig,
    build_script,
    choose_headline_count,
    estimate_duration_seconds,
    load_manual_headlines,
    rank_news,
    synthesize_tts,
)

ROOT = Path(__file__).resolve().parent
UI_DIR = ROOT / "ui"
OUTPUT_DIR = ROOT / "ui_output"
OUTPUT_DIR.mkdir(exist_ok=True)


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/index.html"}:
            return self._send_file(UI_DIR / "index.html", "text/html; charset=utf-8")
        if self.path == "/styles.css":
            return self._send_file(UI_DIR / "styles.css", "text/css; charset=utf-8")
        if self.path == "/app.js":
            return self._send_file(UI_DIR / "app.js", "application/javascript; charset=utf-8")
        if self.path.startswith("/audio/"):
            safe_name = self.path.replace("/audio/", "", 1)
            return self._send_file(OUTPUT_DIR / safe_name, "audio/wav")

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/generate":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except Exception as exc:
            self._send_json({"error": f"Invalid JSON: {exc}"}, status=400)
            return

        headlines = (payload.get("headlines") or "").strip()
        if not headlines:
            self._send_json({"error": "Headlines are required."}, status=400)
            return

        min_headlines = int(payload.get("min_headlines", 6))
        max_headlines = int(payload.get("max_headlines", 14))
        target_min_s = int(payload.get("target_seconds_min", 60))
        target_max_s = int(payload.get("target_seconds_max", 90))
        generate_audio = bool(payload.get("generate_audio", False))
        sarvam_api_key = (payload.get("sarvam_api_key") or "").strip()

        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", delete=True) as temp:
            temp.write(headlines)
            temp.flush()
            items = load_manual_headlines(temp.name)

        ranked = rank_news(items)
        if not ranked:
            self._send_json({"error": "No valid headlines found."}, status=400)
            return

        count = choose_headline_count(ranked, min_headlines, max_headlines, target_min_s, target_max_s)
        script = build_script(ranked, count)
        duration_seconds = estimate_duration_seconds(script)

        result = {
            "script": script,
            "duration_seconds": duration_seconds,
            "duration_minutes": duration_seconds / 60.0,
            "headlines_used": count,
            "message": "Script generated successfully.",
        }

        if generate_audio:
            api_key = sarvam_api_key
            if not api_key:
                self._send_json({"error": "Sarvam API key required for audio generation."}, status=400)
                return

            out_name = f"headlines_{uuid.uuid4().hex}.wav"
            out_path = OUTPUT_DIR / out_name
            cfg = TTSConfig(api_key=api_key)
            try:
                synthesize_tts(script, str(out_path), cfg)
            except Exception as exc:
                self._send_json({"error": f"TTS generation failed: {exc}"}, status=502)
                return

            result["audio_url"] = f"/audio/{out_name}"
            result["message"] = "Script and audio generated successfully."

        self._send_json(result, status=200)


def run() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)
    print("Bangla News Avatar Studio running on http://localhost:8000")
    server.serve_forever()


if __name__ == "__main__":
    run()
