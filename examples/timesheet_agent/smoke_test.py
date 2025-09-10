from __future__ import annotations

import os

from openai import OpenAI

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def main() -> None:
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI()  # reads OPENAI_API_KEY from environment

    resp = client.responses.create(
        model=model,
        input="Reply with the single word: pong",
    )
    print(resp.output_text)


if __name__ == "__main__":
    main()
