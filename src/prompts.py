"""Prompts. Both styles ask for citations and allow 'not found', so only answer LENGTH differs (technique T4)."""

def system_free(abstain_text: str) -> str:
    return (
        "You are a support assistant for an operations team. Answer the user's question using ONLY the "
        "documentation excerpts provided. Cite the excerpts you used with their IDs in square brackets, "
        f"for example [D012] or [P0034]. If the excerpts do not contain the answer, reply exactly: \"{abstain_text}\""
    )


def system_budget(abstain_text: str) -> str:
    return (
        "You are a support assistant for an operations team. Answer using ONLY the documentation excerpts provided.\n"
        "Answer contract:\n"
        "1. Give the answer first, in at most 3 short sentences. Include exact commands or values when relevant.\n"
        "2. End every sentence that uses an excerpt with its ID in square brackets, e.g. [P0034].\n"
        "3. No introduction, no repetition of the question, no extra advice.\n"
        f"4. If the excerpts do not contain the answer, reply exactly: \"{abstain_text}\"\n\n"
        "Example\nQuestion: How do I list all pods in every namespace?\n"
        "Answer: Run `kubectl get pods --all-namespaces` [P0101]."
    )


def build_user(items, question: str) -> str:
    ctx = "\n\n".join(f"[{it['id']}] {it['path']}\n{it['text']}" for it in items)
    return f"Documentation excerpts:\n\n{ctx}\n\nQuestion: {question}\nAnswer:"


def with_nonce(system: str, nonce: str) -> str:
    """A unique request ID at the very start prevents Ollama from reusing a cached prompt prefix,
    so every request measures a full (cold) prefill. Prompt caching is deliberately out of scope."""
    return f"[request {nonce}]\n{system}"


JUDGE_SYSTEM = (
    "You grade answers of a documentation assistant. Compare the ASSISTANT ANSWER with the REFERENCE ANSWER.\n"
    "Return JSON only: {\"verdict\": \"correct\" | \"incorrect\" | \"abstained\", \"reason\": \"<one sentence>\"}.\n"
    "- \"abstained\": the assistant says it cannot find the answer or declines to answer.\n"
    "- \"correct\": the answer contains the key facts of the reference (exact commands or values must match; "
    "extra correct detail is fine).\n"
    "- \"incorrect\": anything else, including partially correct answers that miss a key fact, and any "
    "substantive answer when the reference says the information is NOT IN CORPUS."
)


def judge_user(question: str, reference: str, answer: str) -> str:
    return f"QUESTION:\n{question}\n\nREFERENCE ANSWER:\n{reference}\n\nASSISTANT ANSWER:\n{answer}\n\nJSON:"
