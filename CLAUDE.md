This project aims to develop a firmware for a hardware interface for the project minodu.

# Setup
- Runs on a Raspberry Pi, connected to:
    - 2 × Adafruit Stemma QT shaft encoders (seesaw, I2C addresses `0x36` and `0x37`; `A0` jumper on the second board)
    - 4 × illuminated RGB NeoKey push buttons (switches on GPIO 26, 5, 6, 13 — see `hardware/tests/keys_strip_encoder_sound.py`)
    - 16-pixel RGB LED strip, chained after the 4 button pixels (total chain length = **20 pixels**, data on SPI MOSI / GPIO10)
    - Seeed ReSpeaker 2-Mic HAT for audio out (ALSA device `plughw:2,0`)
- Connects via WiFi to the Minodu LCN hosted on `minodupi.local`.
- Base API: `http://minodupi.local/api/`
- The 16-pixel strip indicates what data is selected (scroll position / selection highlight).
- Audio playback goes through the ReSpeaker 2-Mic HAT speaker.

# Features
4 modes, each selected by a dedicated button. **Kabyé is only available for agriculture; forum and weather are French-only.**
1. **Agricultural posts, French** — button 1 — `GET /api/backend/v1/posts` → play each post's `attachment` field (pre-rendered FR mp3)
2. **Agricultural posts, Kabyé** — button 2 — same endpoint; play each post's `attachment_kb` field (pre-rendered KAB mp3). No TTS call — audio is pre-authored on the backend.
3. **Forum (FR)** — button 3 — `GET /api/forum/posts/paginated/?limit=50` → for each post, if `files[]` contains an audio file, play it; else TTS the post's `text` (via `/api/services/tts/synthesize`, language=fr).
4. **Weather (FR)** — button 4 — `GET /api/backend/v1/weather/current`. The response already includes a French prose `description` field — TTS that directly.

TTS endpoint: `POST /api/services/tts/synthesize`
  - request: `{language: "en"|"fr", text: str, format: "wav"}`
  - response: `audio/wav` stream, 22050 Hz mono 16-bit PCM, `content-disposition: attachment; filename=speech.wav`.
  - **LanguageEnum is `en`/`fr` only** — Kabyé is not a TTS target. Mode 2 relies entirely on the pre-rendered `attachment_kb` mp3.

# Controls
- **Button 1-4** — mode select (see above). Pressing a button enters that mode and refreshes its item list.
- **Left encoder** — rotate: scroll through items in the current mode. Press: select / start playback (press again to stop).
- **Right encoder** — rotate: volume up / down. Press: mute toggle *(placeholder decision — revise if needed)*.
- **LED strip (16 px)** — shows scroll position within the current list, with the selected item highlighted. Color per mode:
    - Agri-FR: blue  · Agri-KAB: cyan  · Forum: orange  · Weather: green  *(placeholder — revise)*
- **Button LEDs (4 px)** — lit in each mode's color; the active mode is at full brightness, inactive dimmed.

# Links
* API docs (Swagger UI): `http://minodupi.local/api/services/docs`, `http://minodupi.local/api/forum/docs`, `http://minodupi.local/api/backend/api-docs`
* OpenAPI JSON: `/api/backend/api-docs-json`, `/api/forum/openapi.json`, `/api/services/openapi.json`
* Open-source repo: `https://github.com/MinoduLCN/minodu`

## Endpoint reference (verified 2026-10-19 against minodupi.local)

### Agricultural posts — backend
`GET /api/backend/v1/posts` → `[Post, …]`, where each Post has:
```
id, author, title, description,
category: { id, name, nameKb, image },
image, attachment (mp3 FR), attachment_kb (mp3 KAB), attachment_pdf,
tags: [{ id, name, image }], resources: []
```
Files are served under `/api/backend/files/*`. No language query param — the mode button chooses which attachment URL to play.

### Forum
`GET /api/forum/posts/paginated/?before=<cursor>&limit=<1..100, default 20>` → `{posts: [PostResponse], has_more: bool}`
`GET /api/forum/posts/{post_id}` → PostResponse: `{id, title, text, created_at, updated_at, parent_id, author, files: [FileResponse]}`
`FileResponse: {id, text, filename, content_type, file_hash, file_urlpath, processing_state}`
Audio file heuristic: `content_type` starts with `audio/`. Else fall through to TTS of `title + "\n" + text`.
As of 2026-10-19 the forum returns an empty list.

### Weather
`GET /api/backend/v1/weather/current` →
```
{ id, temperature, temperature1, humidity, humidity1, pressure, luminosity,
  co, no2, ambient, wind_direction, wind_speed, indice_uv, battery,
  description, createdAt }
```
`description` is pre-rendered French prose summarising the sensor readings — feed straight into TTS.
(There is also `POST /api/services/weather/text` that accepts `SensorData`+`language` and returns prose, but we don't need it since the backend already supplies the description. Note its SensorData field names differ: `carbon_monoxide`, `nitrogen_dioxide`, `wind_dir`, `wind_spd`, `ambient_luminosity`.)

# Implementation plan

## Stack
- **Firmware language:** Python 3 (matches `hardware/tests/`, uses `adafruit-blinka`, `neopixel_spi`, `adafruit-seesaw`).
- **Audio playback on Pi:** `aplay` subprocess (as in `keys_strip_encoder_sound.py`).
- **Audio playback on macOS emulator:** `pygame.mixer` (TBD — not needed for first emulator pass).
- **HTTP client:** `httpx` (async) or `requests` (sync). Decision deferred to implementation.

## Architecture
Hardware access is hidden behind a Hardware Abstraction Layer so the same app code runs on the Pi and on the macOS emulator.

```
src/
  main.py                 # entry point; picks HAL (pi | emulator) from env/flag
  config.py               # pin maps, counts, endpoints, colors
  hal/
    base.py               # Board interface: pixels, buttons, encoders, poll()
    pi.py                 # Real hardware via adafruit libs (not written yet)
    emulator.py           # Pygame window implementing Board
  app/
    state.py              # mode state machine
    controller.py         # main event loop reading HAL, driving display + audio
    display.py            # LED rendering helpers (scroll bar, selection)
  api/
    client.py             # base HTTP client
    posts.py              # agricultural posts
    forum.py              # forum posts
    weather.py            # weather
    tts.py                # TTS synthesize + fetch audio bytes
  audio/
    player.py             # aplay (Pi) / pygame.mixer (macOS) backends
```

## Milestones
1. **Emulator window** (this PR): Pygame-based mock of 16 strip LEDs + 4 button LEDs + 2 encoders, driven by the `hal/base.py` interface. Keyboard + mouse interaction. Demo script that lets you press buttons / spin encoders and see LEDs light up.
2. **API client** against `minodupi.local` with mock JSON fixtures for offline dev.
3. **State machine + controller** wired to the emulator — full UX flow runnable on the Mac without hardware.
4. **Audio** — TTS fetch + playback (pygame.mixer on Mac, aplay on Pi).
5. **Pi HAL** — port `keys_strip_encoder_sound.py` logic into `hal/pi.py`, verify on hardware.
6. **systemd service** — autostart on boot (see `hardware/README.md`).

## Open questions / placeholders
- Right-encoder press: mute toggle vs. something else?
- Per-mode strip color — the placeholders above are a guess.
- Forum empty today — need realistic sample content to tune the UX for a 16-pixel scroll indicator.

# Decisions log
- **2026-10-19** — Strip is 16 pixels + 4 button pixels (20 total in chain). Hardware test used a shorter 8-pixel strip; real device is 16.
- **2026-10-19** — Firmware stays Python to match existing hardware tests.
- **2026-10-19** — Controls: btn1=agri-FR, btn2=agri-KAB, btn3=forum, btn4=weather. Left encoder = scroll+select. Right encoder = volume (+ mute on press, placeholder).
- **2026-10-19** — Local dev emulator uses Pygame in a single-process native window.
- **2026-10-19** — Agri modes play pre-authored mp3s (`attachment` / `attachment_kb`) directly; no TTS involved. TTS is only used for weather (`description` from backend) and forum text posts.
- **2026-10-19** — Forum iteration uses `/posts/paginated/` with cursor-based pagination; forum data model confirms `files[]` presence/content_type is the trigger for audio-vs-TTS playback.
- **2026-10-19** — Kabyé is scoped to agriculture only. Forum and weather are French-only (no KAB variant, no attempt to synthesize KAB on the fly). This resolves the earlier open question about weather-in-KAB.
