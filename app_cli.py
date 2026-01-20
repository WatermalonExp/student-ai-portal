from db import init_db, log_chat
from ai import ask_llm

def main():
    init_db()
    print("CLI Chat ready. Type 'exit' to quit.\n")
    while True:
        user_text = input("You: ").strip()
        if user_text.lower() in {"exit", "quit"}:
            break

        try:
            answer = ask_llm(user_text)
        except Exception as e:
            print(f"Bot: ERROR -> {e}\n")
            continue

        print(f"Bot: {answer}\n")
        log_chat(user_text, answer)

if __name__ == "__main__":
    main()
