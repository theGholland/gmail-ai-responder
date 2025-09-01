# app.py
# pip install flask google-api-python-client google-auth-oauthlib openai
from flask import Flask, request, send_from_directory, jsonify, Response, stream_with_context
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from openai import OpenAI
import base64, email, os, pickle, re, logging
import tiktoken
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import dotenv

dotenv.load_dotenv()
logging.basicConfig(level=logging.INFO)

TOKENIZER = None


def log_token_count(text: str, label: str) -> int:
    global TOKENIZER
    if TOKENIZER is None:
        try:
            TOKENIZER = tiktoken.get_encoding("cl100k_base")
        except Exception as e:  # pragma: no cover - tokenizer optional
            logging.warning(f"Could not load tokenizer: {e}")
            return 0
    tokens = TOKENIZER.encode(text)
    count = len(tokens)
    logging.info(f"{label}: {count} tokens")
    return count


def log_openai_usage(usage, model: str | None = None) -> None:
    model = model or llm_model()
    cost = openai_cost(model, usage.prompt_tokens, usage.completion_tokens)
    extra = f", cost: ${cost:.6f}" if cost else ""
    logging.info(
        "OpenAI usage - prompt: %s tokens, completion: %s tokens, total: %s tokens%s",
        usage.prompt_tokens,
        usage.completion_tokens,
        usage.total_tokens,
        extra,
    )

SCOPES = os.getenv("SCOPES", "https://www.googleapis.com/auth/gmail.modify").split()  # read + create drafts
LLM_URL = os.getenv("LLM_URL", "http://127.0.0.1:11434/v1")                      # Ollama default
MODEL  = os.getenv("MODEL", "llama3.1")                                        # or qwen2.5:14b-instruct
USE_OPENAI = os.getenv("USE_OPENAI", "false").lower() == "true"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Pricing as of May 2024 (USD per 1K tokens)
OPENAI_PRICING = {
    "gpt-4o": {"prompt": 0.005, "completion": 0.015},
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
    "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
    "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
}


def openai_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = OPENAI_PRICING.get(model.lower())
    if not pricing:
        return 0.0
    return (
        prompt_tokens * pricing["prompt"] + completion_tokens * pricing["completion"]
    ) / 1000


def llm_client():
    if USE_OPENAI:
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY required when USE_OPENAI=true")
        return OpenAI(api_key=OPENAI_API_KEY)
    return OpenAI(base_url=LLM_URL, api_key="ollama")


def llm_model():
    return OPENAI_MODEL if USE_OPENAI else MODEL

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


def scrub_formatting(text: str) -> str:
    """Drop HTML formatting tags and collapse excess blank lines."""

    # Remove simple HTML tags like <b> or </div> while preserving angle-bracketed
    # data such as email addresses. Tags with attributes are also stripped.
    text = re.sub(r"</?[a-zA-Z][a-zA-Z0-9]*(?:\s+[^<>]*)?>", "", text)
    # Reduce three or more consecutive newlines to just two to avoid bloated
    # prompts while keeping paragraph breaks.
    return re.sub(r"\n{3,}", "\n\n", text)


def scrub_links(text: str) -> str:
    """Replace any http(s) URL with its bare domain.

    This keeps prompts concise by dropping long paths and query strings.
    Example: ``https://linkedin.com/long/path?query=123`` -> ``linkedin.com``.
    """

    def repl(match: re.Match) -> str:
        url = match.group(0)
        stripped = url.rstrip('.,)')
        trailing = url[len(stripped):]
        return urlparse(stripped).netloc + trailing

    return re.sub(r"https?://\S+", repl, text)


@app.route("/", methods=["GET"])
def serve_ui():
    return send_from_directory("static", "index.html")


@app.route("/api/threads", methods=["GET"])
def api_threads():
    svc = gmail_service()
    q = request.args.get("q") or "is:important"
    thread_refs = (
        svc.users()
        .threads()
        .list(userId="me", q=q, maxResults=3)
        .execute()
        .get("threads", [])
    )
    threads = []
    for t in thread_refs:
        meta = (
            svc.users()
            .threads()
            .get(
                userId="me",
                id=t["id"],
                format="metadata",
                metadataHeaders=["Subject"],
            )
            .execute()
        )
        subject = ""
        snippet = ""
        msgs = meta.get("messages", [])
        if msgs:
            m0 = msgs[0]
            headers = m0["payload"].get("headers", [])
            subject = next(
                (h["value"] for h in headers if h["name"].lower() == "subject"),
                "",
            )
            snippet = BeautifulSoup(m0.get("snippet", ""), "html.parser").get_text()
        threads.append({"id": t["id"], "subject": subject, "snippet": snippet})
    return jsonify(threads)


@app.route("/api/thread/<thread_id>", methods=["GET"])
def api_thread(thread_id):
    svc = gmail_service()
    text, _ = thread_text(svc, thread_id)
    return jsonify({"thread": text})

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
    thread = scrub_formatting(thread)
    thread = scrub_links(thread)  # drop URL paths so the model only sees domains
    prompt = (
        f"You are a communication coach.\nA) THREAD: <<<{thread}>>>\n"
        f"B) MY DRAFT: <<<{draft}>>>\nC) GOAL: {goal}\n"
        "Tasks: diagnose tone; critique; two rewrites (Alpha minimal, Beta assertive). Keep facts intact."
    )
    client = llm_client()
    model = llm_model()
    last = th["messages"][-1]["payload"]["headers"]
    subj = next((h["value"] for h in last if h["name"].lower()=="subject"), "Re: (no subject)")
    to   = next((h["value"] for h in last if h["name"].lower()=="from"), "")

    def generate():
        output = ""
        usage_info = None
        stream_kwargs = {}
        if USE_OPENAI:
            stream_kwargs["stream_options"] = {"include_usage": True}
        stream = client.chat.completions.create(
            model=model,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            **stream_kwargs,
        )
        for chunk in stream:
            text = getattr(chunk.choices[0].delta, "content", "")
            if text:
                output += text
                yield text
            if USE_OPENAI and getattr(chunk, "usage", None) is not None:
                usage_info = chunk.usage
        if usage_info:
            log_openai_usage(usage_info, model)
        else:
            pt = log_token_count(prompt, "Prompt tokens")
            ct = log_token_count(output, "Completion tokens")
            cost = openai_cost(model, pt, ct)
            if cost:
                logging.info("Estimated OpenAI cost: $%.6f", cost)
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
    thread = scrub_formatting(thread)
    thread = scrub_links(thread)  # drop URL paths so the model only sees domains
    prompt = (
        f"You are a communication expert.\nTHREAD: <<<{thread}>>>\n"
        "Identify the tone of the message, infer the type of person they are using Myers Briggs personailty types, listed under 'Tone:' and 'Personality:'."
        " Determine their explicitly stated wants, and determine their implicit needs based on how they speak. List these under 'Needs:' as bullet points."
        " Finally, under 'Template:', please craft a fill-in-the-blank repliy that will be well-received by the Personality type. Reply will address every Need,"
        " using [placeholders] for missing details and asserting how issues will be resolved."
    )
    client = llm_client()
    model = llm_model()
    last = th["messages"][-1]["payload"]["headers"]
    subj = next((h["value"] for h in last if h["name"].lower()=="subject"), "Re: (no subject)")
    to   = next((h["value"] for h in last if h["name"].lower()=="from"), "")

    def generate():
        output = ""
        usage_info = None
        stream_kwargs = {}
        if USE_OPENAI:
            stream_kwargs["stream_options"] = {"include_usage": True}
        stream = client.chat.completions.create(
            model=model,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            **stream_kwargs,
        )
        for chunk in stream:
            text = getattr(chunk.choices[0].delta, "content", "")
            if text:
                output += text
                yield text
            if USE_OPENAI and getattr(chunk, "usage", None) is not None:
                usage_info = chunk.usage
        if usage_info:
            log_openai_usage(usage_info, model)
        else:
            pt = log_token_count(prompt, "Prompt tokens")
            ct = log_token_count(output, "Completion tokens")
            cost = openai_cost(model, pt, ct)
            if cost:
                logging.info("Estimated OpenAI cost: $%.6f", cost)
        match = re.search(r"(?s)Template\s*[:\-]?\s*(.*)", output)
        template = match.group(1).strip() if match else None
        if template:
            create_gmail_draft(svc, to, subj, template)
        else:
            raise ValueError("Model output missing 'Template' section")

    return Response(stream_with_context(generate()), mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=7860, debug=True)
