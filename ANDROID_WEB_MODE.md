# SUN.AI / Bittu on Android

SUN.AI's responsive dashboard is available at the backend root URL. Deploy with `uvicorn android_app:app --host 0.0.0.0 --port $PORT` or the Render blueprint, then open the HTTPS service URL in Chrome on Android.

## Search-first chat and internet learning without a generative AI

With `ASSISTANT_MODE=web`, text chat performs an explicit bounded web search and returns excerpts and source URLs. `POST /api/web-learning` does the same and stores excerpts as a **pending** learning record. Approve or reject records in the dashboard; only approved records are provided as context to the configured chat mode. This is retrieval and storage, not model training or advanced open-ended reasoning.

Set `TAVILY_API_KEY` in the hosting provider's secret environment settings. Keep `SUNAI_API_TOKEN` private. Search results are untrusted; verify the linked sources. Bittu does not crawl continuously or execute actions from page content.

## Android voice

The dashboard provides tap-to-speak using browser SpeechRecognition when the browser supports it, then browser speech synthesis for spoken output. HTTPS and microphone permission are needed. Device and language support vary. It is not always-listening like Siri and does not control Android settings or apps. The separate Gemini Live backend still requires its configured Gemini API; web search mode does not provide live generative voice.

## Existing dashboard capabilities

- Search-first text chat and source links
- Research records pending owner approval
- Owner-scoped memory management
- Feedback submission
- Existing code improvement proposal workflow (no automatic file writes or code execution)
- Browser tap-to-speak and spoken responses

The API remains protected by the SUN.AI bearer token. Free hosting may sleep when idle and `/tmp` storage can be lost when the service restarts; use persistent storage for durable records.
