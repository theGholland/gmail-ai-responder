const { useState, useEffect } = React;

function App() {
  const [q, setQ] = useState('in:inbox');
  const [threads, setThreads] = useState([]);
  const [threadId, setThreadId] = useState('');
  const [threadText, setThreadText] = useState('');
  const [draft, setDraft] = useState('');
  const [goal, setGoal] = useState('');
  const [output, setOutput] = useState('');

  const fetchThreads = async () => {
    const resp = await fetch(`/api/threads?q=${encodeURIComponent(q)}`);
    const data = await resp.json();
    setThreads(data);
    if (data.length) {
      selectThread(data[0].id);
    }
  };

  const selectThread = async (id) => {
    setThreadId(id);
    const resp = await fetch(`/api/thread/${id}`);
    const data = await resp.json();
    setThreadText(data.thread);
  };

  const streamToState = async (resp, setter) => {
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value);
      setter(buf);
    }
  };

  const handleCoach = async () => {
    setOutput('');
    const form = new FormData();
    form.append('draft', draft);
    form.append('goal', goal);
    form.append('thread_id', threadId);
    const resp = await fetch('/coach', { method: 'POST', body: form });
    await streamToState(resp, setOutput);
  };

  const handleMadlibs = async () => {
    setOutput('');
    const form = new FormData();
    form.append('thread_id', threadId);
    const resp = await fetch('/madlibs', { method: 'POST', body: form });
    await streamToState(resp, setOutput);
  };

  useEffect(() => { fetchThreads(); }, []);

  return (
    <div className="grid-container">
      <div>
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="search" />
        <button onClick={fetchThreads}>Fetch</button>
        <ul>
          {threads.map(t => (
            <li key={t.id}>
              <a href="#" onClick={() => selectThread(t.id)}>{t.snippet}</a>
            </li>
          ))}
        </ul>
      </div>
      <div>
        <textarea value={draft} onChange={e => setDraft(e.target.value)} placeholder="Your draft…" />
        <input value={goal} onChange={e => setGoal(e.target.value)} placeholder="Goal (e.g., confirm ETA, under 120 words)" />
        <button onClick={handleCoach}>Coach</button>
        <button onClick={handleMadlibs}>Identify</button>
      </div>
      <div className="thread-box">{threadText || 'Thread will appear here.'}</div>
      <div className="output-box">{output || 'Model output will appear here.'}</div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
