SUMMARY_PROMPT_TEMPLATE = """You are summarizing a meeting transcript for personal notes.

Write a concise summary with these sections:
- Key discussion points
- Decisions made
- Action items (with owners, if mentioned in the transcript)

Only use information present in the transcript below -- do not invent details.

Transcript:
{transcript}

Summary:"""
