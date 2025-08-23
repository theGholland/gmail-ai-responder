# app.py
# pip install flask google-api-python-client google-auth-oauthlib openai
from flask import Flask, request, redirect, render_template_string
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from openai import OpenAI
import base64, email, os, pickle

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]  # read + create drafts
LLM_URL = "http://127.0.0.1:11434/v1"                      # Ollama default
MODEL  = "llama3.1"                                        # or qwen2.5:14b-instruct

app = Flask(__name__)

def gmail_service():
    creds = None
    if os.path.exists("token.pickle"):
        creds = pickle.load(open("token.pickle","rb"))
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        pickle.dump(creds, open("token.pickle","wb"))
    return build("gmail","v1",credentials=creds)

def thread_text(svc, thread_id):
    th = svc.users().threads().get(userId="me", id=thread_id, format="full").execute()
    parts = []
    for m in th["messages"]:
        payload = m["payload"]
        data = payload.get("body",{}).get("data")
        if not data:
            for p in payload.get("parts") or []:
                if p.get("mimeType","").startswith("text/plain") and p.get("body",{}).get("data"):
                    data = p["body"]["data"]; break
        if data:
            parts.append(base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore"))
    return "\n\n---\n\n".join(parts), th

def local_llm(prompt):
    client = OpenAI(base_url=LLM_URL, api_key="ollama")
    r = client.chat.completions.create(model=MODEL, temperature=0.3, messages=[{"role":"user","content":prompt}])
    return r.choices[0].message.content

def create_gmail_draft(svc, to_addr, subj, body):
    msg = email.message.EmailMessage()
    msg["To"] = to_addr
    msg["Subject"] = subj
    msg.set_content(body)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return svc.users().drafts().create(userId="me", body={"message":{"raw":raw}}).execute()

TEMPLATE = """
<!doctype html>
<title>Tone Coach</title>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;font-family:system-ui;">
  <form method="get" action="/">
    <input style="width:70%" name="q" placeholder="search (e.g., subject:kickoff newer_than:7d)">
    <button>Fetch</button>
  </form>
  <form method="post" action="/coach">
    <textarea name="draft" placeholder="Your draft…" style="width:100%;height:8rem;">{{draft or ""}}</textarea>
    <input name="goal" placeholder="Goal (e.g., confirm ETA, under 120 words)" style="width:100%;"/>
    <input type="hidden" name="thread_id" value="{{thread_id or ""}}"/>
    <button>Coach</button>
  </form>
  <div style="white-space:pre-wrap;border:1px solid #ddd;padding:0.75rem;">{{thread or "Thread will appear here."}}</div>
  <div style="white-space:pre-wrap;border:1px solid #ddd;padding:0.75rem;">{{output or "Model output will appear here."}}</div>
</div>
"""

@app.route("/", methods=["GET"])
def index():
    svc = gmail_service()
    q = request.args.get("q") or "in:inbox"            # default heuristic
    threads = svc.users().threads().list(userId="me", q=q, maxResults=5).execute().get("threads", [])
    thread_id = threads[0]["id"] if threads else None
    text = ""
    if thread_id:
        text, _ = thread_text(svc, thread_id)
    return render_template_string(TEMPLATE, thread=text, thread_id=thread_id, draft="", output="")

@app.route("/coach", methods=["POST"])
def coach():
    svc = gmail_service()
    thread_id = request.form["thread_id"]
    draft = request.form["draft"]
    goal = request.form["goal"]
    thread, th = thread_text(svc, thread_id)
    prompt = f"You are a communication coach.\nA) THREAD: <<<{thread}>>>\nB) MY DRAFT: <<<{draft}>>>\nC) GOAL: {goal}\nTasks: diagnose tone; critique; two rewrites (Alpha minimal, Beta assertive). Keep facts intact."
    output = local_llm(prompt)
    # Optionally create a draft with the Beta version by crude split:
    beta = output.split("Beta",1)[-1].strip()
    # Pull a sensible reply subject and To from the last message:
    last = th["messages"][-1]["payload"]["headers"]
    subj = next((h["value"] for h in last if h["name"].lower()=="subject"), "Re: (no subject)")
    to   = next((h["value"] for h in last if h["name"].lower()=="from"), "")
    create_gmail_draft(svc, to, subj, beta)
    return render_template_string(TEMPLATE, thread=thread, thread_id=thread_id, draft=draft, output=output)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=7860, debug=True)
