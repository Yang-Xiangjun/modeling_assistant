"""Small non-blocking chat window for the assistant MVP."""

from __future__ import annotations

import queue
import threading
from typing import Any

from drawgen.assistant.agent import AssistantAgent
from drawgen.assistant.harness import HarnessAdapter
from drawgen.assistant.log import SessionLog
from drawgen.backends.live import LiveBackend


def run_panel(
    backend: LiveBackend, harness: HarnessAdapter, *, log: SessionLog | None = None
) -> None:
    """Run the chat window; only the panel thread touches Tkinter."""
    import tkinter as tk
    from tkinter import messagebox

    events: queue.Queue[tuple[str, Any]] = queue.Queue()
    agent = AssistantAgent(backend, harness, log=log)
    root = tk.Tk()
    root.title("drawgen assistant")
    root.geometry("620x520")
    transcript = tk.Text(root, state="disabled", wrap="word")
    transcript.pack(fill="both", expand=True, padx=8, pady=8)
    entry = tk.Entry(root)
    entry.pack(fill="x", padx=8, pady=(0, 8))
    send = tk.Button(root, text="Send")
    send.pack(anchor="e", padx=8, pady=(0, 8))

    def append(text: str) -> None:
        transcript.configure(state="normal")
        transcript.insert("end", text + "\n")
        transcript.see("end")
        transcript.configure(state="disabled")

    def confirm(preview: str) -> bool:
        done = threading.Event()
        answer: dict[str, bool] = {}
        events.put(("confirm", (preview, done, answer)))
        done.wait()
        return answer.get("value", False)

    def worker(message: str) -> None:
        try:
            result = agent.run(message, confirm=confirm)
            events.put(("result", result))
        except Exception as exc:  # panel must remain usable after a failed turn
            events.put(("error", str(exc)))

    def submit(_: Any = None) -> None:
        message = entry.get().strip()
        if not message:
            return
        entry.delete(0, "end")
        append(f"you> {message}")
        send.configure(state="disabled")
        threading.Thread(target=worker, args=(message,), daemon=True).start()

    def poll() -> None:
        try:
            while True:
                kind, value = events.get_nowait()
                if kind == "confirm":
                    preview, done, answer = value
                    answer["value"] = bool(
                        messagebox.askyesno("Confirm NX operation", preview, parent=root)
                    )
                    done.set()
                elif kind == "result":
                    if value.answer:
                        append(f"assistant> {value.answer}")
                    if value.ask_user:
                        append(f"assistant> {value.ask_user}")
                    send.configure(state="normal")
                else:
                    append(f"assistant error> {value}")
                    send.configure(state="normal")
        except queue.Empty:
            pass
        root.after(50, poll)

    entry.bind("<Return>", submit)
    send.configure(command=submit)
    append("drawgen assistant ready; bridge and harness are local")
    root.after(50, poll)
    root.mainloop()
