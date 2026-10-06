import httpx
import time

BASE_URL = "http://localhost:8000"

def test_gateway():
    print("=" * 60)
    print("🚀 SENTRYGATE AUTOMATED PRODUCTION TEST HARNESS")
    print("=" * 60)

    client = httpx.Client(base_url=BASE_URL, timeout=60.0)

    # 1. Health Check
    print("\n[TEST 1] Verifying System Health...")
    r = client.get("/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    print("✅ System Health: 200 OK")

    # 2. Cold Call (Cache Miss)
    prompt_1 = "Explain the difference between a stack and a queue in 2 sentences."
    print(f"\n[TEST 2] Cold Query (Expecting Model Generation)...")
    start = time.time()
    r = client.post("/v1/chat/completions", json={
        "model": "sentry-auto",
        "messages": [{"role": "user", "content": prompt_1}]
    })
    elapsed = round((time.time() - start) * 1000, 2)
    assert r.status_code == 200, f"Call failed: {r.text}"
    assert r.headers.get("X-Sentry-Cache-Hit") == "false"
    print(f"✅ Generated in {elapsed} ms (Saved to local cache)")

    # 3. Warm Call (Semantic Cache Hit)
    prompt_2 = "What is the difference between stack and queue in two sentences?"
    print(f"\n[TEST 3] Semantic Cache Test (Expecting Sub-50ms Hit)...")
    start = time.time()
    r = client.post("/v1/chat/completions", json={
        "model": "sentry-auto",
        "messages": [{"role": "user", "content": prompt_2}]
    })
    elapsed = round((time.time() - start) * 1000, 2)
    assert r.status_code == 200
    assert r.headers.get("X-Sentry-Cache-Hit") == "true", "Expected cache hit!"
    print(f"⚡ CACHE HIT SUCCESSFUL: Returned in {elapsed} ms (Target < 50ms)")

    # 4. Polarity Guard Test (Prevent False Positives)
    prompt_3 = "Explain the difference WITHOUT using stack and queue."
    print(f"\n[TEST 4] Polarity & Negation Guard Test...")
    r = client.post("/v1/chat/completions", json={
        "model": "sentry-auto",
        "messages": [{"role": "user", "content": prompt_3}]
    })
    assert r.headers.get("X-Sentry-Cache-Hit") == "false", "Polarity guard failed to reject negation query!"
    print("🛡️ Polarity Guard: PASSED (Correctly rejected negation match)")

    print("\n" + "=" * 60)
    print("🎉 ALL 4 TESTS PASSED (100% SUCCESS RATE)")
    print("=" * 60)

if __name__ == "__main__":
    test_gateway()