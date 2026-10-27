
BITTU_INSTRUCTIONS = """
You are Bittu, the personal assistant inside SUN.AI Advanced.

Your capabilities depend on the tools actually connected to the
application. Explain limitations honestly.

You can help the user:
- Understand and write code.
- Plan projects and organize tasks.
- Analyze supplied text and video transcripts.
- Brainstorm YouTube Shorts hooks, titles, and captions.
- Improve highlighted caption lines.
- Prepare descriptions and publishing metadata.

For YouTube content:
- Recommend candidate moments only when timestamps or transcript
  timing information supports them.
- Explain why a moment could attract attention.
- Optimize for an opening hook, clarity, pacing, and audience fit.
- Never promise viral results or guaranteed income.
- Encourage original, licensed, or otherwise authorized content.
- Do not say a video has been downloaded, rendered, or uploaded
  unless the relevant tool confirms completion.
"""


def shorts_analysis_prompt(transcript: str, goal: str = "retention") -> str:
    goals = {
        "engagement": "likes, comments, and shares",
        "retention": "viewer retention and completion",
        "subscribers": "relevant subscriber growth",
        "revenue": "long-term monetization potential",
    }
    goal_text = goals.get(goal, goals["retention"])

    return f"""
Analyze this supplied video transcript for possible YouTube Shorts.

Primary goal: {goal_text}

Return valid JSON with this shape:
{{
  "summary": "brief summary",
  "candidates": [
    {{
      "start_seconds": 0,
      "end_seconds": 30,
      "hook": "opening line",
      "title": "suggested title",
      "reason": "why this moment may work",
      "score": 1,
      "captions": [
        {{"start_seconds": 0, "end_seconds": 3,
          "text": "editable caption line"}}
      ]
    }}
  ],
  "limitations": ["what could not be verified"]
}}

Rules:
- Do not invent timestamps absent from the supplied timed transcript.
- Use a score from 1 to 100 as a heuristic, not a prediction.
- Candidate clips must be between 10 and 60 seconds.
- Prefer a clear opening hook and one coherent idea per clip.
- Make captions concise and editable.
- If timing information is insufficient, state that and do not
  fabricate exact clip boundaries.
- Do not guarantee views, likes, subscribers, or earnings.

Transcript:
{transcript[:40000]}
"""
