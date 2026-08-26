import time

from rag import retrieve
from llm import generate_answer


# ============================================================
# MODELS
# ============================================================

MODELS = [
    "llama3.1:latest",
    "qwen2.5:7b"
]


# ============================================================
# TEST QUESTIONS
# ============================================================

QUESTIONS = [

    "What is the typical ground contact time during the acceleration phase of sprinting?",

    "What is the typical ground contact time during maximum velocity sprinting?",

    "Was shorter ground contact time associated with higher sprinting speed?",

    "What was the ground contact time of the fastest sprinter?",

    "What is the typical flight time during maximum velocity sprinting?",

    "What is the typical ground contact time during early acceleration?",

    "What relationship was found between sprinting speed and stride length?",

    "What relationship was found between sprinting speed and ground contact time?",

    "What was the maximum sprinting speed reported for the athletes?",

    "What is the optimal ground contact time for winning an Olympic gold medal?"
]


# ============================================================
# BENCHMARK
# ============================================================

print("\n" + "=" * 100)
print("WATHBA LLM BENCHMARK")
print("=" * 100)


results = []


for question_number, question in enumerate(QUESTIONS, 1):

    print("\n")
    print("=" * 100)
    print(f"QUESTION {question_number}")
    print("=" * 100)
    print(question)


    # --------------------------------------------------------
    # RAG
    # --------------------------------------------------------

    rag_start = time.perf_counter()

    top_docs, context_text = retrieve(
        question,
        retrieval_limit=20,
        final_limit=5
    )

    rag_time = time.perf_counter() - rag_start


    print(f"\nRAG TIME: {rag_time:.2f} seconds")


    # --------------------------------------------------------
    # Test both models
    # --------------------------------------------------------

    for model in MODELS:

        print("\n" + "-" * 100)
        print(f"MODEL: {model}")
        print("-" * 100)


        start_time = time.perf_counter()

        answer = generate_answer(
            question,
            context_text,
            model
        )

        llm_time = time.perf_counter() - start_time

        total_time = rag_time + llm_time


        print(f"\nLLM TIME: {llm_time:.2f} seconds")
        print(f"TOTAL TIME: {total_time:.2f} seconds")

        print("\nANSWER:")
        print(answer)


        results.append({
            "question": question_number,
            "model": model,
            "rag_time": rag_time,
            "llm_time": llm_time,
            "total_time": total_time,
            "answer": answer
        })


# ============================================================
# SUMMARY
# ============================================================

print("\n\n")
print("=" * 100)
print("BENCHMARK SUMMARY")
print("=" * 100)


for model in MODELS:

    model_results = [
        r for r in results
        if r["model"] == model
    ]

    avg_llm = sum(
        r["llm_time"]
        for r in model_results
    ) / len(model_results)

    avg_total = sum(
        r["total_time"]
        for r in model_results
    ) / len(model_results)


    print("\n" + "-" * 80)
    print(f"MODEL: {model}")
    print("-" * 80)

    print(
        f"Average LLM time:   {avg_llm:.2f} seconds"
    )

    print(
        f"Average total time: {avg_total:.2f} seconds"
    )