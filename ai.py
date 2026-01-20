import subprocess

SYSTEM_PROMPT = (
    "You are a helpful university admissions assistant. "
    "Be clear, structured, and practical."
)
MODEL_NAME = "llama3"

def ask_llm(user_text: str) -> str:
    prompt = f"{SYSTEM_PROMPT}\n\n{user_text}\n"
    result = subprocess.run(
        ["ollama", "run", MODEL_NAME],
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "").strip() or "Ollama failed")
    return (result.stdout or "").strip()
