"""Concurrency/load smoke (NFR §9 proxy). Stdlib only — host Python.

Logs in once, then fires concurrent authenticated requests at a list endpoint and reports
P50/P95/P99 latency, throughput, and error rate. NOTE: the dev stack runs 2 gunicorn workers
x 4 threads, so this is a smoke at moderate concurrency, not a true 500-VU load test.
"""
import json, time, urllib.request, urllib.parse, http.cookiejar
from concurrent.futures import ThreadPoolExecutor

BASE = "http://localhost:8080"
CONCURRENCY = 40
TOTAL = 800
ENDPOINT = "/api/method/frappe.client.get_list?doctype=Sales%20Order&limit_page_length=20"

# login -> cookie jar
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
data = urllib.parse.urlencode({"usr": "Administrator", "pwd": "admin"}).encode()
opener.open(urllib.request.Request(BASE + "/api/method/login", data=data), timeout=30).read()
sid = "; ".join(f"{c.name}={c.value}" for c in cj)

def one(_):
    t = time.perf_counter()
    try:
        req = urllib.request.Request(BASE + ENDPOINT, headers={"Cookie": sid})
        with urllib.request.urlopen(req, timeout=60) as r:
            r.read()
            return (time.perf_counter() - t) * 1000, r.status
    except Exception as e:
        return (time.perf_counter() - t) * 1000, getattr(e, "code", "ERR")

t0 = time.perf_counter()
with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
    res = list(ex.map(one, range(TOTAL)))
wall = time.perf_counter() - t0

lat = sorted(r[0] for r in res)
errs = sum(1 for r in res if r[1] != 200)
def pct(p): return lat[min(len(lat) - 1, int(p / 100 * len(lat)))]
print(f"LOAD endpoint      : {ENDPOINT}")
print(f"LOAD concurrency   : {CONCURRENCY}  total requests: {TOTAL}")
print(f"LOAD wall time     : {wall:.1f}s   throughput: {TOTAL / wall:.0f} req/s")
print(f"LOAD errors        : {errs}/{TOTAL} ({100*errs/TOTAL:.1f}%)")
print(f"LOAD latency p50/p95/p99/max : {pct(50):.0f} / {pct(95):.0f} / {pct(99):.0f} / {lat[-1]:.0f} ms")
print(f"LOAD verdict       : {'PASS' if errs == 0 and pct(95) < 2000 else 'REVIEW'} (target: 0 errors, P95<2000ms)")
