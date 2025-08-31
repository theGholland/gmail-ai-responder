# app.py
# pip install flask google-api-python-client google-auth-oauthlib openai
from flask import Flask, request, render_template_string, Response, stream_with_context
from urllib.parse import quote_plus
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from openai import OpenAI
import base64, email, os, pickle, re, logging
from bs4 import BeautifulSoup
import dotenv

dotenv.load_dotenv()
logging.basicConfig(level=logging.INFO)

SCOPES = os.getenv("SCOPES", "https://www.googleapis.com/auth/gmail.modify").split()  # read + create drafts
LLM_URL = os.getenv("LLM_URL", "http://127.0.0.1:11434/v1")                      # Ollama default
MODEL  = os.getenv("MODEL", "llama3.1")                                        # or qwen2.5:14b-instruct

app = Flask(__name__)

def gmail_service():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"  # or http://localhost if that URI is registered
            auth_url, _ = flow.authorization_url(prompt="consent")
            print(f"Visit this URL to authorize:\n{auth_url}")
            auth_code = input("Enter the authorization code: ")
            flow.fetch_token(code=auth_code)
            creds = flow.credentials
        with open("token.pickle", "wb") as f:
            pickle.dump(creds, f)
    return build("gmail","v1",credentials=creds)

def thread_text(svc, thread_id):
    def collect_parts(payload):
        plain_parts, html_parts = [], []

        def walk(part):
            mime = part.get("mimeType", "")
            body = part.get("body", {})
            if mime.startswith("multipart/"):
                for sp in part.get("parts") or []:
                    walk(sp)
            elif mime.startswith("text/plain"):
                data = body.get("data")
                if data:
                    plain_parts.append(
                        base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                    )
            elif mime.startswith("text/html"):
                data = body.get("data")
                if data:
                    html = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                    html_parts.append(BeautifulSoup(html, "html.parser").get_text())

        walk(payload)
        return plain_parts or html_parts

    th = svc.users().threads().get(userId="me", id=thread_id, format="full").execute()
    parts = []
    for m in th["messages"]:
        texts = collect_parts(m["payload"])
        if texts:
            parts.append("\n".join(texts))
    return "\n\n---\n\n".join(parts), th

def create_gmail_draft(svc, to_addr, subj, body):
    msg = email.message.EmailMessage()
    msg["To"] = to_addr
    msg["Subject"] = subj
    msg.set_content(body)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return svc.users().drafts().create(userId="me", body={"message":{"raw":raw}}).execute()

TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Tone Coach</title>
  <link rel="stylesheet" href="/static/vaporwave.css">
</head>
<body class="vaporwave">
  <div class="grid-container">
    <form method="get" action="/">
      <input name="q" placeholder="search (e.g., subject:kickoff newer_than:7d)" value="{{ q|e }}"/>
      <button>Fetch</button>
      {% if threads %}
      <ul>
      {% for t in threads %}
        <li><a href="/?q={{ quote_plus(q)|e }}&thread_id={{t['id']}}">{{t['snippet']}}</a></li>
      {% endfor %}
      </ul>
      {% endif %}
    </form>
    <form id="coachForm" method="post" action="/coach">
      <textarea name="draft" placeholder="Your draft…">{{draft or ""}}</textarea>
      <input name="goal" placeholder="Goal (e.g., confirm ETA, under 120 words)"/>
      <input type="hidden" name="thread_id" value="{{thread_id or ""}}"/>
      <button>Coach</button>
      <button type="button" id="madlibsBtn">Identify</button>
    </form>
    <div class="thread-box">{{thread or "Thread will appear here."}}</div>
    <div id="output" class="output-box">{{output or "Model output will appear here."}}</div>
  </div>
  <script>
const form = document.getElementById('coachForm');
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const output = document.getElementById('output');
  output.textContent = "";
  const resp = await fetch('/coach', { method: 'POST', body: new FormData(form) });
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    output.textContent += decoder.decode(value);
  }
});

const madlibsBtn = document.getElementById('madlibsBtn');
  madlibsBtn.addEventListener('click', async () => {
    const output = document.getElementById('output');
    output.textContent = "";
    const resp = await fetch('/madlibs', { method: 'POST', body: new FormData(form) });
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      output.textContent += decoder.decode(value);
    }
  });
  </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    svc = gmail_service()
    q = request.args.get("q") or "in:inbox"            # default heuristic
    threads = (
        svc.users()
        .threads()
        .list(userId="me", q=q, maxResults=3)
        .execute()
        .get("threads", [])
    )
    thread_id = request.args.get("thread_id")
    thread_text = "No threads found."
    get_thread_text = thread_text  # alias to avoid shadowing
    if not thread_id and threads:
        thread_id = threads[0]["id"]
    thread_text = ""
    text = ""
    if thread_id:
        thread_text, _ = globals()["thread_text"](svc, thread_id) #get_thread_text(svc, thread_id)
    return render_template_string(
        TEMPLATE,
        thread=thread_text,
        thread_id=thread_id,
        draft="",
        output="",
        threads=threads,
        q=q,
        quote_plus=quote_plus,
    )

@app.route("/coach", methods=["POST"])
def coach():
    svc = gmail_service()
    thread_id = request.form.get("thread_id")
    draft = request.form.get("draft")
    goal = request.form.get("goal")

    if thread_id is None:
        return "Missing thread_id", 400
    if draft is None:
        return "Missing draft", 400
    if goal is None:
        return "Missing goal", 400

    thread, th = thread_text(svc, thread_id)
    prompt = (
        f"You are a communication coach.\nA) THREAD: <<<{thread}>>>\n"
        f"B) MY DRAFT: <<<{draft}>>>\nC) GOAL: {goal}\n"
        "Tasks: diagnose tone; critique; two rewrites (Alpha minimal, Beta assertive). Keep facts intact."
    )
    client = OpenAI(base_url=LLM_URL, api_key="ollama")
    last = th["messages"][-1]["payload"]["headers"]
    subj = next((h["value"] for h in last if h["name"].lower()=="subject"), "Re: (no subject)")
    to   = next((h["value"] for h in last if h["name"].lower()=="from"), "")

    def generate():
        output = ""
        stream = client.chat.completions.create(
            model=MODEL,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        for chunk in stream:
            text = getattr(chunk.choices[0].delta, "content", "")
            output += text
            yield text
        match = re.search(r"(?s)(?:^|\n)Beta\s*[:\-]?\s*(.*)", output)
        beta = match.group(1).strip() if match else None
        if beta:
            create_gmail_draft(svc, to, subj, beta)
        else:
            raise ValueError("Model output missing 'Beta' section")

    return Response(stream_with_context(generate()), mimetype="text/plain")

@app.route("/madlibs", methods=["POST"])
def madlibs():
    svc = gmail_service()
    thread_id = request.form.get("thread_id")

    if thread_id is None:
        return "Missing thread_id", 400

    thread, th = thread_text(svc, thread_id)
    prompt = (
        f"You are a communication expert.\nTHREAD: <<<{thread}>>>\n"
        "Identify the tone of the message, infer the type of person they are using Myers Briggs personailty types, listed under 'Tone:' and 'Personality:'."
        " Determine their explicitly stated wants, and determine their implicit needs based on how they speak. List these under 'Needs:' as bullet points."
        " Finally, under 'Template:', please craft a fill-in-the-blank repliy that will be well-received by the Personality type. Reply will address every Need,"
        " using [placeholders] for missing details and asserting how issues will be resolved."
    )
    client = OpenAI(base_url=LLM_URL, api_key="ollama")
    last = th["messages"][-1]["payload"]["headers"]
    subj = next((h["value"] for h in last if h["name"].lower()=="subject"), "Re: (no subject)")
    to   = next((h["value"] for h in last if h["name"].lower()=="from"), "")

    def generate():
        output = ""
        stream = client.chat.completions.create(
            model=MODEL,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        for chunk in stream:
            text = getattr(chunk.choices[0].delta, "content", "")
            output += text
            yield text
        match = re.search(r"(?s)Template\s*[:\-]?\s*(.*)", output)
        template = match.group(1).strip() if match else None
        if template:
            create_gmail_draft(svc, to, subj, template)
        else:
            raise ValueError("Model output missing 'Template' section")

    return Response(stream_with_context(generate()), mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=7860, debug=True)
