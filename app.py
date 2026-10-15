"""
JARVIS AI Assistant - Tehmina Anwar
Console-based assistant. Web-related search commands automatically open your
default web browser and also show search results in the terminal.
"""

from __future__ import annotations

import ast
import json
import operator
import os
import re
import webbrowser
from datetime import datetime
from pathlib import Path
from textwrap import shorten
from urllib.parse import quote_plus

from dotenv import load_dotenv
from groq import Groq
from ddgs import DDGS
from pypdf import PdfReader

# -------------------- Configuration --------------------
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

MEMORY_FILE = DATA_DIR / "memory.json"
NOTES_FILE = DATA_DIR / "notes.json"
TASKS_FILE = DATA_DIR / "tasks.json"
PDF_TEXT_FILE = DATA_DIR / "loaded_pdf.txt"

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
API_KEY = os.getenv("GROQ_API_KEY", "").strip()
client = Groq(api_key=API_KEY) if API_KEY else None
MAX_MEMORY_ITEMS = 200
MAX_MEMORY_CHARS = 3000


# -------------------- JSON storage and memory --------------------
def read_json(path: Path, default):
    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
    except (OSError, json.JSONDecodeError):
        pass
    return default


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(value, file, ensure_ascii=False, indent=2)


def load_memory():
    value = read_json(MEMORY_FILE, [])
    return value if isinstance(value, list) else []


def save_memory(role: str, content: str):
    memory = load_memory()
    memory.append({
        "role": role,
        "content": str(content)[:MAX_MEMORY_CHARS],
        "time": datetime.now().isoformat(timespec="seconds"),
    })
    write_json(MEMORY_FILE, memory[-MAX_MEMORY_ITEMS:])


def get_recent_history(limit=10):
    history = []
    for item in load_memory()[-limit:]:
        role = item.get("role")
        content = item.get("content", "")
        if role in {"user", "assistant"} and content:
            history.append({"role": role, "content": content})
    return history


# -------------------- AI --------------------
def ask_ai(prompt: str, system=None, history=None) -> str:
    if not client:
        return (
            "Groq API key missing. Create a .env file beside app.py and add:\n"
            "GROQ_API_KEY=your_actual_groq_api_key"
        )
    messages = [{
        "role": "system",
        "content": system or (
            "You are JARVIS, a helpful AI assistant created for Tehmina. "
            "Answer clearly and helpfully. Use simple explanations and examples."
        ),
    }]
    if history:
        messages.extend(history[-10:])
    messages.append({"role": "user", "content": prompt})
    try:
        response = client.chat.completions.create(
            model=MODEL, messages=messages, temperature=0.4, max_tokens=1600
        )
        return (response.choices[0].message.content or "No response received.").strip()
    except Exception as exc:
        return f"AI request error: {exc}\nCheck GROQ_API_KEY, GROQ_MODEL, and internet connection."


# -------------------- Safe calculator --------------------
def calculate(expression: str):
    binary_ops = {
        ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod, ast.Pow: operator.pow,
    }
    unary_ops = {ast.UAdd: operator.pos, ast.USub: operator.neg}

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in binary_ops:
            right = evaluate(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ValueError("Exponent is too large.")
            result = binary_ops[type(node.op)](evaluate(node.left), right)
            if isinstance(result, (int, float)) and abs(result) > 1e100:
                raise ValueError("Result is too large.")
            return result
        if isinstance(node, ast.UnaryOp) and type(node.op) in unary_ops:
            return unary_ops[type(node.op)](evaluate(node.operand))
        raise ValueError("Use numbers, +, -, *, /, //, %, **, and parentheses only.")

    return evaluate(ast.parse(expression, mode="eval"))


# -------------------- Automatic browser + web search --------------------
def get_search_query(command: str):
    """Return a search query for common natural-language web commands."""
    text = command.strip()
    patterns = [
        r"^(?:please\s+)?(?:open\s+)?(?:the\s+)?(?:web\s+)?browser\s+and\s+search\s+(?:for\s+)?(.+)$",
        r"^(?:please\s+)?open\s+(?:google\s+)?chrome\s+and\s+(?:search\s+for|google)\s+(.+)$",
        r"^(?:please\s+)?open\s+(?:the\s+)?(?:vs\s+code\s+)?browser\s+panel\s+and\s+search\s+(?:for\s+)?(.+)$",
        r"^(?:please\s+)?google\s+search\s+(.+)$",
        r"^(?:please\s+)?search(?:\s+the\s+web)?(?:\s+for)?\s+(.+)$",
        r"^(?:please\s+)?look\s+up\s+(.+)$",
        r"^(?:please\s+)?google\s+(.+)$",
        r"^(?:please\s+)?find\s+(?:information|details|news|websites|articles)\s+(?:about|on|for)\s+(.+)$",
    ]
    for pattern in patterns:
        match = re.match(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def web_search(query: str, max_results=6):
    query = query.strip()
    if not query:
        print("Please enter a search query.")
        return

    # Open the user's default browser automatically to Google results.
    search_url = "https://www.google.com/search?q=" + quote_plus(query)
    try:
        opened = webbrowser.open_new_tab(search_url)
        if opened:
            print("\n🌐 Opened your default web browser for:", query)
        else:
            print("\nBrowser could not be launched automatically. Open this URL:")
            print(search_url)
    except Exception as exc:
        print("Could not open browser:", exc)
        print("Search URL:", search_url)

    results = []
    try:
        with DDGS() as search_client:
            for item in search_client.text(query, max_results=max_results):
                results.append({
                    "title": str(item.get("title", "Untitled")),
                    "body": str(item.get("body", "")),
                    "href": str(item.get("href", "")),
                })
    except Exception as exc:
        print(f"\nSearch-results provider error: {exc}")
        print("The browser search page has still been opened.")
        return

    if not results:
        print("\nNo search results were returned by the results provider.")
        print("Use the Google results page that was opened in your browser.")
        return

    print("\n========== WEB SEARCH RESULTS ==========")
    for index, item in enumerate(results, 1):
        print(f"\n{index}. {item['title']}")
        if item["body"]:
            print("   " + shorten(item["body"].replace("\n", " "), width=260, placeholder="..."))
        if item["href"]:
            print("   Link: " + item["href"])
    print("\nBrowser opened automatically. Search results are also shown above.")


# -------------------- PDF assistant --------------------
def get_pdf_text(path_text: str):
    path = Path(path_text.strip().strip('"'))
    if not path.is_absolute():
        path = BASE_DIR / path
    if not path.exists() or not path.is_file():
        print("PDF not found. Please enter its full file path.")
        return ""
    try:
        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        if not text.strip():
            print("No selectable text found. This may be a scanned PDF requiring OCR.")
            return ""
        PDF_TEXT_FILE.write_text(text, encoding="utf-8")
        print(f"PDF loaded: {path.name} | Pages: {len(reader.pages)} | Characters: {len(text)}")
        return text
    except Exception as exc:
        print("PDF loading error:", exc)
        return ""


def loaded_pdf_text():
    try:
        return PDF_TEXT_FILE.read_text(encoding="utf-8") if PDF_TEXT_FILE.exists() else ""
    except OSError:
        return ""


def summarize_pdf():
    text = loaded_pdf_text()
    if not text:
        print("Load a PDF first using option 9.")
        return
    answer = ask_ai("Summarize this PDF using headings, key points, important details, and a conclusion:\n\n" + text[:18000])
    print("\nJARVIS:\n", answer)


def ask_pdf():
    text = loaded_pdf_text()
    if not text:
        print("Load a PDF first using option 9.")
        return
    question = input("Question about the PDF: ").strip()
    if not question:
        return
    answer = ask_ai(
        "Answer using the PDF content below. If the answer is not present, say so. "
        "Include a short supporting excerpt when possible.\n\nPDF CONTENT:\n"
        + text[:18000] + "\n\nQUESTION:\n" + question
    )
    print("\nJARVIS:", answer)
    save_memory("user", "PDF question: " + question)
    save_memory("assistant", answer)


# -------------------- Chat and assistants --------------------
def ai_chat():
    print("\nJARVIS Chat started. Type 'back' to return to the main menu.")
    print("Examples: search latest AI news | google Python internships | calculate 25*50")
    while True:
        user_input = input("\nYou: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"back", "exit", "quit"}:
            break

        query = get_search_query(user_input)
        if query:
            web_search(query)
            save_memory("user", user_input)
            save_memory("assistant", f"Web search performed for: {query}")
            continue

        lower = user_input.lower()
        if lower.startswith(("calculate ", "calc ")):
            expression = re.sub(r"^(calculate|calc)\s+", "", user_input, flags=re.I)
            try:
                answer = str(calculate(expression))
            except Exception as exc:
                answer = f"Calculator error: {exc}"
        elif any(term in lower for term in (
            "what time", "current time", "date today", "today's date",
            "what is the date", "time now", "current date",
        )):
            answer = datetime.now().strftime("%A, %d %B %Y | %I:%M:%S %p")
        else:
            answer = ask_ai(user_input, history=get_recent_history(limit=10))
        print("\nJARVIS:", answer)
        save_memory("user", user_input)
        save_memory("assistant", answer)


def calculator_menu():
    expression = input("Math expression (e.g. 25*50 or (100+20)/4): ").strip()
    try:
        print("Answer:", calculate(expression))
    except Exception as exc:
        print("Calculator error:", exc)


def date_time_menu():
    print("Current date and time:", datetime.now().strftime("%A, %d %B %Y | %I:%M:%S %p"))


def study_assistant():
    topic = input("Topic or question: ").strip()
    if topic:
        print("\n" + ask_ai(
            "Teach this topic to a beginner using simple language, headings, examples, and a short quiz:\n\n" + topic,
            system="You are a patient, beginner-friendly study tutor. Explain clearly.",
        ))


def coding_assistant():
    question = input("Coding problem or request: ").strip()
    if question:
        print("\n" + ask_ai(
            "Help with this programming task. Give correct code when needed and explain how to run it:\n\n" + question,
            system="You are a practical Python and software development mentor.",
        ))


# -------------------- Notes and tasks --------------------
def notes_manager():
    notes = read_json(NOTES_FILE, [])
    if not isinstance(notes, list):
        notes = []
    print("\n1. Add note\n2. View notes\n3. Delete note\n0. Back")
    choice = input("Choose: ").strip()
    if choice == "1":
        title = input("Note title: ").strip() or "Untitled"
        content = input("Note content: ").strip()
        if content:
            notes.append({"title": title, "content": content, "created": datetime.now().isoformat(timespec="seconds")})
            write_json(NOTES_FILE, notes)
            print("Note saved.")
    elif choice == "2":
        if not notes:
            print("No notes saved yet.")
        for i, note in enumerate(notes, 1):
            print(f"{i}. {note.get('title', 'Untitled')} — {note.get('content', '')}")
    elif choice == "3":
        for i, note in enumerate(notes, 1):
            print(f"{i}. {note.get('title', 'Untitled')}")
        try:
            index = int(input("Note number to delete: ")) - 1
            if 0 <= index < len(notes):
                notes.pop(index)
                write_json(NOTES_FILE, notes)
                print("Note deleted.")
            else:
                print("Invalid note number.")
        except ValueError:
            print("Enter a valid number.")


def task_manager():
    tasks = read_json(TASKS_FILE, [])
    if not isinstance(tasks, list):
        tasks = []
    print("\n1. Add task\n2. View tasks\n3. Mark complete\n4. Delete task\n0. Back")
    choice = input("Choose: ").strip()
    if choice == "1":
        task = input("Task description: ").strip()
        if task:
            tasks.append({"task": task, "done": False, "created": datetime.now().isoformat(timespec="seconds")})
            write_json(TASKS_FILE, tasks)
            print("Task saved.")
    elif choice in {"2", "3", "4"}:
        if not tasks:
            print("No tasks saved yet.")
            return
        for i, task in enumerate(tasks, 1):
            print(f"{i}. [{'DONE' if task.get('done') else 'PENDING'}] {task.get('task', '')}")
        if choice in {"3", "4"}:
            try:
                index = int(input("Task number: ")) - 1
                if not 0 <= index < len(tasks):
                    print("Invalid task number.")
                    return
                if choice == "3":
                    tasks[index]["done"] = True
                    print("Task marked complete.")
                else:
                    tasks.pop(index)
                    print("Task deleted.")
                write_json(TASKS_FILE, tasks)
            except ValueError:
                print("Enter a valid number.")


def memory_menu():
    memory = load_memory()
    print(f"\nSaved conversation entries: {len(memory)}")
    for item in memory[-10:]:
        print(f"[{item.get('time', '')}] {item.get('role', '')}: {shorten(str(item.get('content', '')), width=180)}")
    if input("\nClear all conversation memory? Type YES to confirm, or press Enter: ").strip() == "YES":
        write_json(MEMORY_FILE, [])
        print("Conversation memory cleared.")


def email_writer():
    purpose = input("What is the email or message for? ").strip()
    tone = input("Tone (professional/friendly/formal): ").strip() or "professional"
    if purpose:
        print("\n" + ask_ai(
            f"Write a ready-to-send email or message.\nPurpose: {purpose}\nTone: {tone}\n"
            "Include a subject if it is an email. Do not invent personal facts.",
            system="You are a professional writing assistant.",
        ))


def help_menu():
    print("""
JARVIS HELP
AI Chat web examples:
  search ecommerce trends 2026
  search for Python AI internships
  Google search latest AI news
  open Chrome and search AI tools
  calculate 25*50
  What time is it?

Browser:
  A web-related search command opens your default browser automatically
  to Google search results, and also prints DuckDuckGo search results here.
  If a website blocks embedded viewing, use the normal browser tab.

PDF:
  1. Load a PDF using option 9.
  2. Ask questions using option 10.
  3. Summarize it using option 11.

Saved data is stored in the data folder beside app.py.
""")


# -------------------- Login and main menu --------------------
def login():
    expected_username = os.getenv("JARVIS_USERNAME", "Tehmina")
    expected_password = os.getenv("JARVIS_PASSWORD", "12345")
    print("========== JARVIS LOGIN ==========")
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    if username == expected_username and password == expected_password:
        print("\nLogin successful!\n")
        return True
    print("Login failed. Check JARVIS_USERNAME and JARVIS_PASSWORD in .env.")
    return False


def main():
    print("=" * 54)
    print("       JARVIS AI ASSISTANT - TEHMINA ANWAR")
    print("=" * 54)
    if not login():
        return

    while True:
        print("""
========== JARVIS MAIN MENU ==========
1.  AI Chat
2.  Calculator
3.  Date and Time
4.  Web Search (opens browser automatically)
5.  Study Assistant
6.  Coding Assistant
7.  Notes Manager
8.  Task Manager
9.  Load PDF
10. Ask Questions About PDF
11. Summarize PDF
12. Conversation Memory
13. Help
14. Email and Message Writer
0.  Exit
""")
        choice = input("Choose an option: ").strip()
        if choice == "1":
            ai_chat()
        elif choice == "2":
            calculator_menu()
        elif choice == "3":
            date_time_menu()
        elif choice == "4":
            query = input("Search query: ").strip()
            if query:
                web_search(query)
        elif choice == "5":
            study_assistant()
        elif choice == "6":
            coding_assistant()
        elif choice == "7":
            notes_manager()
        elif choice == "8":
            task_manager()
        elif choice == "9":
            path = input("Full path to the PDF: ").strip()
            if path:
                get_pdf_text(path)
        elif choice == "10":
            ask_pdf()
        elif choice == "11":
            summarize_pdf()
        elif choice == "12":
            memory_menu()
        elif choice == "13":
            help_menu()
        elif choice == "14":
            email_writer()
        elif choice == "0":
            print("JARVIS shutting down. Goodbye!")
            break
        else:
            print("Invalid option. Choose a number from 0 to 14.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nJARVIS stopped.")
