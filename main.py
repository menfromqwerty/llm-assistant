"""Точка запуска LLM Assistant v1.01."""

from llm_assistant.app import LLMAssistant
from llm_assistant.common import HAS_DND, TkinterDnD, tk

def main() -> None:
    if HAS_DND:
        try:
            root = TkinterDnD.Tk()
        except Exception:
            root = tk.Tk()
    else:
        root = tk.Tk()

    LLMAssistant(root)
    root.mainloop()

if __name__ == "__main__":
    main()
