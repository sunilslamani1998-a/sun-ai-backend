# Android/browser web-only mode

SUN.AI's dashboard is a responsive web app; on Android, open its HTTPS service URL in Chrome. This mode does not require installing or compiling an APK.

## Run chat without a generative AI provider

Set `ASSISTANT_MODE=web`. In this mode, Bittu sends the user's query to the configured web search provider and returns the search excerpts and source links directly. It does not initialize or call Gemini (or another generative model). This is source retrieval, not open-ended AI reasoning: answers may be incomplete, and users should open and verify cited sources.

Configure `TAVILY_API_KEY` in the hosting service's environment settings. Do not put that key or `SUNAI_API_TOKEN` in the browser or commit either secret. Keep `SUNAI_API_TOKEN` set; API authentication remains required.

The repository's Render configuration defaults to web-only chat. After deployment completes, open the Render HTTPS URL on Android, enter the SUN.AI API token, and allow microphone access if using browser speech input. HTTPS is required for microphone access on most browsers. A free hosting instance may sleep when idle.

Gemini Live voice streaming is a separate feature and still requires Gemini credentials/model configuration. Web-only chat provides text answers from web search; it does not create live speech conversation or perform arbitrary phone actions.
