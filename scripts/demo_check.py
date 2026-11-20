"""Pre-demo check. Start the server first (start_aihub.bat), then run:
    python scripts/demo_check.py
It also warms up the AI model so the first demo question is fast."""
import requests

BASE = "http://127.0.0.1:8000"
SID = "demo-check"
failed = []


def post(path, payload):
    r = requests.post(BASE + path, json=payload, timeout=180)
    data = r.json()
    if not r.ok:
        raise RuntimeError(data.get("error", f"HTTP {r.status_code}"))
    return data


def check(name, fn):
    print(f"... {name}", flush=True)
    try:
        print(f"[PASS] {fn()}")
    except Exception as e:  # report every problem, not just the first
        failed.append(name)
        print(f"[FAIL] {name}: {e}")


def server():
    requests.get(BASE + "/health", timeout=5).raise_for_status()
    return "Server is running"


def documents():
    docs = requests.get(BASE + "/api/documents", timeout=10).json()["documents"]
    if not docs:
        raise RuntimeError("No PDF is indexed. Upload rag_study_guide.pdf on the page.")
    return "PDF indexed: " + ", ".join(f"{k} ({v} chunks)" for k, v in docs.items())


def chat():
    d = post("/api/chat", {"session_id": SID, "message": "Hello, who are you?"})
    return f"AI answers (badge: {d['route']})"


def rag():
    q = "What is the default chunk size and overlap in AIHub?"
    d = post("/api/chat", {"session_id": SID, "message": q})
    if d["route"] != "rag" or "1000" not in d["answer"].replace(",", ""):
        raise RuntimeError(f"Wrong badge or answer (badge {d['route']}): {d['answer'][:90]}")
    return "PDF question correct (badge: rag)"


def sql():
    q = "Which city has the most customers?"
    d = post("/api/chat", {"session_id": SID, "message": q})
    if d["route"] != "sql" or "Lahore" not in d["answer"]:
        raise RuntimeError(f"Wrong badge or answer (badge {d['route']}): {d['answer'][:90]}")
    return "Database question correct (badge: sql)"


def summarize():
    url = "https://en.wikipedia.org/wiki/Retrieval-augmented_generation"
    d = post("/api/summarize", {"url": url})
    return f"Summarizer works ({d['type']})"


check("Server", server)
if "Server" in failed:
    print("\nNOT READY: start the server first (double-click start_aihub.bat).")
    raise SystemExit(1)
check("PDF", documents)
check("Chat (needs internet and Groq key)", chat)
check("PDF question", rag)
check("Database question", sql)
check("Summarizer (needs internet)", summarize)
requests.delete(f"{BASE}/api/chat/{SID}", timeout=10)
print("\nREADY FOR DEMO" if not failed else f"\nNOT READY. Fix: {', '.join(failed)}")
