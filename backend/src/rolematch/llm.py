import json
import os
from typing import Any

from dotenv import load_dotenv
from groq import Groq


def call_llm(
    system_prompt: str,
    user_prompt: str,
    *,
    model: str = "openai/gpt-oss-120b",
) -> dict[str, Any]:
    """Request a JSON object from Groq and return it as a Python dictionary.

    Loads GROQ_API_KEY from the environment or .env. Raises ValueError for
    missing credentials or unusable output; Groq API errors propagate.
    Schema validation is the caller's responsibility.
    """
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("Missing GROQ_API_KEY. Set it in the environment or .env.")

    with Groq(api_key=api_key, timeout=60.0) as client:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt + "\nReturn only a valid JSON object.",
                },
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=8192,
            temperature=0,
        )

    if not response.choices:
        raise ValueError("Groq returned no completion choices.")

    choice = response.choices[0]
    if choice.finish_reason != "stop":
        raise ValueError(f"Groq did not finish normally: {choice.finish_reason}.")

    content = choice.message.content
    if not content or not content.strip():
        raise ValueError("Groq returned an empty response.")

    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("Groq returned invalid JSON.") from exc

    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object from Groq.")

    return result
