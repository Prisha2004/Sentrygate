---
title: SentryGate — Universal AI Gateway
emoji: 🛡️
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
---

# 🛡️ SentryGate: Universal AI Gateway & Semantic Memory Engine

[[https://img.shields.io/badge/License-MIT-emerald.svg]](LICENSE)
[[https://img.shields.io/badge/Python-3.10%2B-blue.svg]](https://www.python.org/)
[[https://img.shields.io/badge/Docker-Ready-cyan.svg]](Dockerfile)
[[https://img.shields.io/badge/Tests-100%25%20Passed-success.svg]](test_suite.py)
[[https://img.shields.io/badge/Cache%20Latency-6.49ms-brightgreen.svg]]()

> An open-source AI Gateway providing **sub-10ms semantic vector caching**, **cost-aware model routing**, and an **audited verification dossier** with a 1-line drop-in URL.

---

## ⚡ 60-Second Integration (Zero Downloads)

Drop SentryGate into any application by swapping one single line (`base_url`):

### Python (OpenAI SDK / LangChain)
```python
from openai import OpenAI

client = OpenAI(
    base_url="[https://your-space.hf.space/v1](https://your-space.hf.space/v1)",
    api_key="your-api-key"
)

response = client.chat.completions.create(
    model="sentry-auto",
    messages=[{"role": "user", "content": "Explain our return policy."}]
)