"""
WATHBA — LLM Generation Layer

Takes retrieved research context (from rag.py) and an optional athlete_data
dict (from the computer vision pipeline) and produces a grounded, cited
answer via a local Ollama model.

Author: [your name]
Scope: LLM integration only. Retrieval/reranking/context building (rag.py)
was built by a separate team member.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
DEFAULT_MODEL = os.getenv("WATHBA_LLM_MODEL", "llama3.1:latest")


SYSTEM_PROMPT = """
You are WATHBA, a scientific biomechanics assistant for sprint analysis.

You may receive up to two sources of information:

1. RESEARCH CONTEXT: excerpts from peer-reviewed sprint biomechanics papers.
2. ATHLETE DATA: biomechanical KPIs extracted by computer vision from a
   specific athlete's own race video (e.g. stride length, ground contact
   time, knee angle, trunk lean). These numbers are measured, not invented
   by you — treat them as ground truth about THIS athlete.

STRICT RULES:

1. Use ONLY information explicitly present in the Research Context or the
   Athlete Data provided. NEVER invent, guess, or fabricate a paper name,
   author, year, page number, numerical value, or scientific claim.

2. You may cite ONLY papers and page numbers that appear explicitly in the
   Research Context. Athlete Data does not need a citation — attribute it
   to "the athlete's video analysis" instead.

3. If the Research Context does not contain enough evidence to answer or
   support a comparison, say exactly:
   "The provided research context is insufficient to answer this reliably."

4. When comparing the athlete to research benchmarks:
   - State the athlete's own value first (from Athlete Data).
   - State the relevant research benchmark next (with citation).
   - Then describe how the athlete compares, only using comparisons the
     numbers actually support.

5. Carefully distinguish sprint phases: acceleration, maximal velocity,
   deceleration. Never compare or combine values across different phases.

6. Distinguish between population-level values, individual athlete values,
   extreme/best-case values, and correlations in the Research Context.
   When the question asks for "typical" or "average", use population-level
   values as the main benchmark — not an individual extreme value.

7. Keep the answer concise and scientifically precise.

CITATION FORMAT (research claims only):
[Paper: filename, Page: X]

Never create a citation that is not present in the Research Context.
"""


def format_athlete_data(athlete_data: dict) -> str:
    """
    Turn computer-vision JSON output into a readable block for the prompt.

    Expected shape (adapt keys to match the actual CV pipeline output):
    {
        "athlete_name": "Ahmed A.",
        "clip_id": "race_2026_08_20_01",
        "phase": "maximum_velocity",
        "metrics": {
            "ground_contact_time_s": 0.098,
            "stride_length_m": 2.21,
            "stride_frequency_hz": 4.55,
            "knee_angle_deg": 148,
            "trunk_lean_deg": 6.2,
            "speed_ms": 10.4
        }
    }
    """
    if not athlete_data:
        return None

    lines = [
        f"Athlete: {athlete_data.get('athlete_name', 'Unknown')}",
        f"Clip ID: {athlete_data.get('clip_id', 'N/A')}",
        f"Sprint Phase: {athlete_data.get('phase', 'N/A')}",
        "Measured KPIs:",
    ]

    for key, value in athlete_data.get("metrics", {}).items():
        lines.append(f"  - {key.replace('_', ' ')}: {value}")

    quality_note = athlete_data.get("data_quality_note")
    if quality_note:
        lines.append(f"\nData Quality Caveat: {quality_note}")
        lines.append(
            "When this caveat is present, mention the reduced measurement "
            "confidence in your answer instead of stating the value as certain."
        )

    return "\n".join(lines)


def generate_answer(question: str, context_text: str, model: str = DEFAULT_MODEL,
                     athlete_data: dict = None) -> str:
    """
    Generate a grounded answer from retrieved research context, optionally
    combined with computer-vision athlete data.

    Args:
        question: the user's question.
        context_text: retrieved research passages from rag.py's retrieve().
        model: Ollama model tag (e.g. "llama3.1:latest", "qwen2.5:7b").
        athlete_data: optional dict of computer-vision KPIs for a specific
            athlete's clip. Omit for pure research questions.

    Returns:
        The model's answer as a string.

    Raises:
        requests.HTTPError: if the Ollama request fails.
        requests.Timeout: if the request exceeds the timeout window.
    """

    sections = [f"Research Context:\n-----------------\n{context_text}\n-----------------"]

    athlete_block = format_athlete_data(athlete_data)
    if athlete_block:
        sections.append(f"Athlete Data:\n-------------\n{athlete_block}\n-------------")

    sections.append(f"Question:\n{question}")
    sections.append("Answer the question based strictly on the information above.")

    user_prompt = "\n\n".join(sections)

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.1},
        },
        timeout=300,
    )

    response.raise_for_status()
    data = response.json()

    return data["message"]["content"]


if __name__ == "__main__":
    # Quick manual smoke test — requires rag.py and a running Ollama instance.
    from rag import retrieve

    question = "What is the typical ground contact time of elite sprinters during maximum velocity sprinting?"

    top_docs, context_text = retrieve(question)
    answer = generate_answer(question, context_text, model=DEFAULT_MODEL)

    print("\n" + "=" * 80)
    print("ANSWER")
    print("=" * 80)
    print(answer)
