import threading
import requests

URL = "http://127.0.0.1:8000/test"
TOTAL_REQUESTS = 20

results = {
    "allowed": 0,
    "blocked": 0
}

lock = threading.Lock()

def hit_api(i):
    try:
        response = requests.get(URL)

        remaining = response.headers.get("X-RateLimit-Remaining")
        limit = response.headers.get("X-RateLimit-Limit")

        with lock:
            if response.status_code == 200:
                results["allowed"] += 1
            elif response.status_code == 429:
                results["blocked"] += 1

            print(
                f"Request {i}: status={response.status_code}, "
                f"limit={limit}, remaining={remaining}"
            )

    except Exception as e:
        print(f"Request {i}: Error: {e}")

threads = []

for i in range(TOTAL_REQUESTS):
    t = threading.Thread(target=hit_api, args=(i,))
    threads.append(t)

for t in threads:
    t.start()

for t in threads:
    t.join()

print("\nResults:")
print("Allowed:", results["allowed"])
print("Blocked:", results["blocked"])