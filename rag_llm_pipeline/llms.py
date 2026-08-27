"""
WATHBA — LLM Generation Layer (Production: Groq-hosted, no local Ollama needed)

Same interface as the local-Ollama version of llm.py — generate_answer()
keeps the exact same signature — so nothing else in the project (rag.py,
benchmark.py, api_example.py) needs to change.

Requires: pip install groq
Set GROQ_API_KEY in your Render environment variables (never commit it).
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Groq model IDs (check console.groq.com/docs/models for current list)
DEFAULT_MODEL = os.getenv("WATHBA_LLM_MODEL", "llama-3.1-8b-instant")
# Other options to test: "llama-3.3-70b-versatile", "qwen/qwen3-32b"


SYSTEM_PROMPT = """
You are WATHBA, a scientific biomechanics assistant for sprint analysis.

You may receive up to two sources of information:

1. RESEARCH CONTEXT: excerpts from peer-reviewed sprint biomechanics papers.
2. ATHLETE DATA: biomechanical KPIs extracted by computer vision from a
   specific athlete's own race video. These numbers are measured, not
   invented by you — treat them as ground truth about THIS athlete.

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

4. When comparing the athlete to research benchmarks, state the athlete's
   value first, the research benchmark next (with citation), then the
   comparison — only using comparisons the numbers actually support.

5. Carefully distinguish sprint phases: acceleration, maximal velocity,
   deceleration. Never compare or combine values across different phases.

6. Distinguish population-level values from individual/extreme values.
   When asked for "typical" or "average", use population-level values.

7. Keep the answer concise and scientifically precise.

CITATION FORMAT (research claims only): [Paper: filename, Page: X]
Never create a citation that is not present in the Research Context.
"""


def format_athlete_data(athlete_data: dict) -> str:
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
    return "\n".join(lines)


def generate_answer(question: str, context_text: str, model: str = DEFAULT_MODEL,
                     athlete_data: dict = None) -> str:
    """
    Same signature as the Ollama version — drop-in replacement.
    """
    sections = [f"Research Context:\n-----------------\n{context_text}\n-----------------"]

    athlete_block = format_athlete_data(athlete_data)
    if athlete_block:
        sections.append(f"Athlete Data:\n-------------\n{athlete_block}\n-------------")

    sections.append(f"Question:\n{question}")
    sections.append("Answer the question based strictly on the information above.")

    user_prompt = "\n\n".join(sections)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    from rag_llm_pipeline.rag import retrieve

    question = "What is the typical ground contact time of elite sprinters during maximum velocity sprinting?"
    top_docs, context_text = retrieve(question)
    answer = generate_answer(question, context_text)

    print(answer)