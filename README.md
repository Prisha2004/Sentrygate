# 🛡️ SentryGate: Universal AI Gateway & Semantic Memory Engine

[[https://img.shields.io/badge/License-MIT-emerald.svg]](https://www.google.com/search?q=LICENSE)
[[https://img.shields.io/badge/Python-3.10%2B-blue.svg]](https://www.google.com/search?q=https://www.python.org/)
[[https://img.shields.io/badge/Docker-Ready-cyan.svg]](https://www.google.com/search?q=Dockerfile)
[[https://img.shields.io/badge/Tests-100%25%20Passed-success.svg]](https://www.google.com/search?q=test_suite.py)
[[https://img.shields.io/badge/Cache%20Latency-4.52ms-brightgreen.svg]](https://www.google.com/search?q=)
[[https://img.shields.io/badge/Live%20Demo-Online-purple.svg]](https://sentrygate-9ght.onrender.com)

A lightweight, open-source AI Gateway providing sub-10ms semantic vector caching, resilient multi-provider routing, and telemetry verification dossiers in a single drop-in URL.

Live Public Cloud Instance (Zero Downloads Required):
[https://sentrygate-9ght.onrender.com](https://sentrygate-9ght.onrender.com)

---

## ⚡ The Problem: Why Developers Need SentryGate

In production LLM applications, 30% to 50% of incoming queries are semantically repetitive.

Calling frontier models repeatedly for identical or near-identical prompts leads to three major challenges:

1. **Unnecessary Token Expenses**: Paying commercial APIs repeatedly for the same answers.
2. **High Latency**: Users wait 2 to 6 seconds for prompts that could be served from local memory.
3. **Outages & Rate Limits**: Applications crash when providers return 429 Too Many Requests or experience downtime.

### Direct LLM Calls vs. SentryGate

| Metric | Direct LLM Calls | With SentryGate |
| --- | --- | --- |
| **Repeat Query Latency** | 2,000ms – 5,000ms | 4ms – 10ms (Sub-10ms Vector Cache) |
| **Repeat Query Token Cost** | Standard API rates ($0.02–$0.06/query) | $0.00 (Bypasses Upstream LLM) |
| **Outage Handling** | Application crashes on 429 / 500 | Self-healing multi-provider fallback |
| **Negation Accuracy** | Naive vector search confuses negations | Dual-Stage Polarity Guard |
| **Integration Effort** | Full pipeline rewrite | 1-Line URL swap (base_url) |

---

## 🚀 60-Second Quickstart (Zero Downloads)

SentryGate strictly adheres to the universal OpenAI HTTP specification. You can plug SentryGate into existing applications by updating one single configuration line (base_url):

### Python (OpenAI SDK / LangChain / CrewAI)

```python
from openai import OpenAI

# Drop-in replacement: Point base_url to your live SentryGate instance
client = OpenAI(
    base_url="https://sentrygate-9ght.onrender.com/v1",
    api_key="your-key-or-none"
)

# Your existing calls run 100% unchanged:
response = client.chat.completions.create(
    model="sentry-auto",
    messages=[{"role": "user", "content": "What is SentryGate and how does it reduce inference cost?"}]
)

print(response.choices[0].message.content)

```

### TypeScript / Next.js (Vercel AI SDK)

```typescript
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "https://sentrygate-9ght.onrender.com/v1",
  apiKey: "optional-provider-key",
});

const completion = await client.chat.completions.create({
  model: "sentry-auto",
  messages: [{ role: "user", content: "Explain binary search." }],
});
console.log(completion.choices[0].message.content);

```

### Developer IDEs (Cursor & Windsurf)

1. In Cursor: Open Settings -> Models -> OpenAI API Base URL.
2. Set to: [https://sentrygate-9ght.onrender.com/v1](https://www.google.com/url?sa=E&source=gmail&q=https://sentrygate-9ght.onrender.com/v1)
3. Cursor now routes repetitive code generation through SentryGate, caching duplicate lookups automatically.

### Direct cURL

```bash
curl -X POST https://sentrygate-9ght.onrender.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "sentry-auto", "messages": [{"role": "user", "content": "Hello SentryGate!"}]}'

```

---

## 🏗️ System Architecture

```
                 Incoming Request (/v1/chat/completions)
                                  │
                                  ▼
                     [FastEmbed CPU Embedding]
                      (384-dim vector in ~3ms)
                                  │
                                  ▼
               [ChromaDB Cosine Similarity Lookup]
                                  │
                 ┌────────────────┴────────────────┐
                 │                                 │
           (Cache Hit)                       (Cache Miss)
                 │                                 │
                 ▼                                 ▼
      [Polarity / Negation Guard]          [Universal Router]
                 │                    (Groq / Gemini / Ollama)
                 ▼                                 │
          Return in <10ms                          ▼
         (Cost Saved: 100%)                 Save to ChromaDB

```

---

## 🛡️ Core Engineering Features

### 1. Sub-10ms Semantic Vector Caching

Powered by FastEmbed (BAAI/bge-small-en-v1.5) running locally on CPU in ~3ms, paired with persistent ChromaDB storage. Semantically equivalent queries bypass upstream LLMs entirely, returning cached results in 4.52 ms.

### 2. Dual-Stage Polarity Guard (Negation Safety)

Naive vector embeddings often treat negated prompts as identical (e.g., "with eggs" vs. "without eggs" having >0.92 cosine similarity). SentryGate runs a lexical token analysis on critical negation words (not, without, never, except) before accepting a cache hit, preventing false-positive matches.

### 3. Temporal Query Bypass

A regex-based temporal classifier automatically detects time-sensitive indicators (today, now, current, latest, stock, weather) and bypasses the cache to ensure real-time accuracy.

### 4. Hybrid Local & Cloud Runtime

* Local Mode: Runs completely air-gapped on Apple Silicon / Linux using local Ollama (gemma3:4b, llama3) with zero internet dependencies.
* Cloud Mode: Deployed to serverless cloud containers on Render using lightweight, cost-effective inference endpoints.

### 5. Verification Dossier & Telemetry Headers

Every response includes detailed audit telemetry returned via custom HTTP headers:

* X-Sentry-Cache-Hit: true or false
* X-Sentry-Latency-Ms: Exact latency recorded in milliseconds
* X-Sentry-Cost-Saved: Dollar savings calculated against baseline commercial API token rates

---

## 🧪 Automated Test Suite

SentryGate includes a self-contained test harness covering cold generation, sub-10ms cache retrieval, and polarity guard assertions:

```bash
python3 test_suite.py

```

### Verified Test Output:

```text
============================================================
🚀 SENTRYGATE AUTOMATED PRODUCTION TEST HARNESS
============================================================
[TEST 1] Verifying System Health...          ✅ 200 OK
[TEST 2] Cold Query Generation...            ✅ Model Generated & Cached
[TEST 3] Semantic Cache Retrieval...         ⚡ CACHE HIT (4.52 ms)
[TEST 4] Polarity & Negation Guard...        🛡️ PASSED (Rejected False Match)
============================================================
🎉 ALL 4 TESTS PASSED (100% SUCCESS RATE)
============================================================

```

---

## 💻 Local Development (Mac / Linux / Windows)

```bash
# 1. Clone repository
git clone https://github.com/Prisha2004/Sentrygate.git
cd Sentrygate

# 2. Set up virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start local gateway
uvicorn app:app --port 8000 --reload

```

Open http://localhost:8000 in your browser to access the local interactive dashboard.

---

## 📄 License

Distributed under the MIT License. Free for developers, startups, and open-source projects forever.
