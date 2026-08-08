"""Compute + verify every deterministic expected answer used in the prompt suite."""
from itertools import product, permutations
from fractions import Fraction

OUT = []
def rec(k, v):
    OUT.append((k, v))

# ───────────────────────── TOOLS ─────────────────────────
rec("T5 celsius->F 37C", 37 * 9 / 5 + 32)

# ───────────────────────── APPLIED ───────────────────────
# P1 log triage
LOGS = """2026-08-04T02:11:07Z INFO  llama-swap: loading model qwen3.6-27b-mtp-q8
2026-08-04T02:11:09Z INFO  llama-server: n_ctx=131072 n_batch=4096
2026-08-04T02:12:44Z WARN  llama-server: kv cache 91% full, ctx shift armed
2026-08-04T02:13:02Z INFO  llama-swap: model ready in 115.3s
2026-08-04T02:19:51Z WARN  llama-server: slot 0 prompt truncated (2148 tokens dropped)
2026-08-04T02:20:15Z INFO  llama-swap: request completed in 8.42s
2026-08-04T02:31:40Z WARN  llama-swap: healthcheck slow (14.2s of 900s budget)
2026-08-04T02:44:03Z ERROR llama-server: CUDA error: out of memory on device 1
2026-08-04T02:44:03Z INFO  llama-swap: process exited rc=1
2026-08-04T02:44:06Z INFO  llama-swap: restarting profile qwen3.6-27b-mtp-q8
2026-08-04T02:46:01Z WARN  llama-server: falling back to --n-cpu-moe 12
2026-08-04T02:46:58Z INFO  llama-swap: model ready in 52.0s"""
levels = {}
for line in LOGS.strip().split("\n"):
    lv = line.split("Z ")[1].split()[0]
    levels[lv] = levels.get(lv, 0) + 1
rec("P1 level counts", levels)
rec("P1 total lines", len(LOGS.strip().split("\n")))
err = [l for l in LOGS.strip().split("\n") if " ERROR " in l]
rec("P1 error line", err)

# P3 KV cache math
# bytes = 2 (K and V) * n_layers * n_kv_heads * head_dim * ctx * bytes_per_elem
n_layers, n_kv_heads, head_dim, ctx = 62, 8, 128, 131072
for name, bpe in (("f16", 2), ("q8_0 (1.0625 B/elem)", 1.0625)):
    b = 2 * n_layers * n_kv_heads * head_dim * ctx * bpe
    rec(f"P3 KV {name} bytes", b)
    rec(f"P3 KV {name} GiB", b / (1024 ** 3))
# saving
b16 = 2 * n_layers * n_kv_heads * head_dim * ctx * 2
b8 = 2 * n_layers * n_kv_heads * head_dim * ctx * 1.0625
rec("P3 saving GiB", (b16 - b8) / (1024 ** 3))
rec("P3 f16 fits in 11.0 GiB free?", b16 / (1024 ** 3) <= 11.0)

# P5 backup job table
JOBS = [
    # name, status, protected_GiB
    ("anf-prod-vol01", "SUCCESS", 812),
    ("anf-prod-vol02", "SUCCESS_WITH_WARNINGS", 1140),
    ("anf-prod-vol03", "FAILED", 0),
    ("anf-dev-vol01", "SUCCESS", 96),
    ("anf-prod-vol04", "SUCCESS_WITH_WARNINGS", 640),
    ("anf-dr-vol01", "SUCCESS", 2044),
    ("anf-dev-vol02", "SKIPPED", 0),
    ("anf-prod-vol05", "SUCCESS", 388),
]
# policy: SUCCESS_WITH_WARNINGS counts as NOT protected; SKIPPED excluded from denominator
counted = [j for j in JOBS if j[1] != "SKIPPED"]
protected = [j for j in counted if j[1] == "SUCCESS"]
rec("P5 denominator (non-skipped)", len(counted))
rec("P5 fully protected count", len(protected))
rec("P5 compliance pct", round(100 * len(protected) / len(counted), 1))
rec("P5 protected GiB", sum(j[2] for j in protected))
rec("P5 unprotected prod volumes", sorted(j[0] for j in counted if j[1] != "SUCCESS" and "prod" in j[0]))

# ───────────────────────── FINANCE ───────────────────────
# F1 amortising payment
P, apr, n = 285000.0, 0.0625, 360
i = apr / 12
pay = P * i / (1 - (1 + i) ** -n)
rec("F1 monthly payment", pay)
rec("F1 total interest", pay * n - P)

# F2 EAR
ear = (1 + 0.054 / 12) ** 12 - 1
rec("F2 EAR pct", ear * 100)

# F3 NPV / IRR
CF = [-125000, 32000, 41000, 47000, 53000, 28000]
def npv(r, cf=CF):
    return sum(c / (1 + r) ** t for t, c in enumerate(cf))
rec("F3 NPV @9%", npv(0.09))
lo, hi = 0.0, 1.0
for _ in range(300):
    mid = (lo + hi) / 2
    if npv(mid) > 0:
        lo = mid
    else:
        hi = mid
rec("F3 IRR", lo)
rec("F3 IRR pct", lo * 100)

# F4 local inference cost per 1M output tokens
watts, rate, tps = 700, 0.29, 18.2
hours = (1_000_000 / tps) / 3600
cost = hours * (watts / 1000) * rate
rec("F4 hours per 1M tok", hours)
rec("F4 kWh per 1M tok", hours * watts / 1000)
rec("F4 $ per 1M output tokens", cost)
rec("F4 vs $3.00/1M api ratio", 3.00 / cost)

# F5 FCF
rev, cogs, opex, da, taxrate, capex, dnwc = 48_200_000, 21_690_000, 12_400_000, 3_150_000, 0.24, 5_400_000, 1_180_000
ebitda = rev - cogs - opex
ebit = ebitda - da
nopat = ebit * (1 - taxrate)
fcf = nopat + da - capex - dnwc
rec("F5 EBITDA", ebitda)
rec("F5 EBIT", ebit)
rec("F5 NOPAT", nopat)
rec("F5 FCF", fcf)
rec("F5 FCF margin pct", 100 * fcf / rev)

# ───────────────────────── CODING ────────────────────────
# K1 reference impl for chunk_by_bytes
def chunk_by_bytes(text, limit):
    out, cur = [], ""
    for word in text.split(" "):
        if len(word.encode("utf-8")) > limit:
            raise ValueError("word exceeds limit")
        cand = word if not cur else cur + " " + word
        if len(cand.encode("utf-8")) <= limit:
            cur = cand
        else:
            out.append(cur)
            cur = word
    if cur:
        out.append(cur)
    return out
rec("K1 case a", chunk_by_bytes("the quick brown fox", 10))
rec("K1 case b", chunk_by_bytes("naïve café brûlée", 8))
rec("K1 case c", chunk_by_bytes("", 5))
try:
    chunk_by_bytes("supercalifragilistic", 5)
    rec("K1 case d", "NO RAISE")
except ValueError as e:
    rec("K1 case d", f"ValueError: {e}")

# K2 buggy dedupe-preserving-order fix
def dedupe_buggy(rows):
    seen = set()
    out = []
    for r in rows:
        key = r["id"]
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out
rows = [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}, {"id": 1, "v": "c"}]
rec("K2 correct behaviour", dedupe_buggy(rows))

# K3 CRUXEval-style output prediction
def f(s):
    parts = s.split("-")
    out = []
    for i, p in enumerate(parts):
        if i % 2 == 0:
            out.append(p.upper())
        else:
            out.append(p[::-1])
    return "-".join(out).replace("--", "|")
rec("K3 f('ab-cde--fg')", repr(f("ab-cde--fg")))
rec("K3 f('x-y-z')", repr(f("x-y-z")))

# K4 semver compare
def semver_cmp(a, b):
    def key(v):
        core, _, pre = v.partition("-")
        nums = [int(x) for x in core.split(".")]
        if pre == "":
            return (nums, [])
        ids = []
        for p in pre.split("."):
            ids.append((0, int(p), "") if p.isdigit() else (1, 0, p))
        return (nums, ids)
    ka, kb = key(a), key(b)
    if ka[0] != kb[0]:
        return -1 if ka[0] < kb[0] else 1
    if not ka[1] and not kb[1]:
        return 0
    if not ka[1]:
        return 1
    if not kb[1]:
        return -1
    if ka[1] == kb[1]:
        return 0
    return -1 if ka[1] < kb[1] else 1
cases = [("1.0.0", "1.0.1"), ("1.0.0-alpha", "1.0.0"), ("1.0.0-alpha.1", "1.0.0-alpha.beta"),
         ("1.0.0-rc.1", "1.0.0-rc.1"), ("2.1.0", "2.1.0-9999"), ("1.0.0-alpha.10", "1.0.0-alpha.9")]
rec("K4 semver results", [(a, b, semver_cmp(a, b)) for a, b in cases])

# K5 stateful generator trace
def g(n):
    total = 0
    for i in range(n):
        total += i
        if total % 3 == 0:
            yield ("hit", i, total)
            total -= 1
        elif i % 4 == 3:
            yield ("skip", i, total)
    yield ("done", total)
rec("K5 list(g(9))", list(g(9)))

# ───────────────────────── REASONING ─────────────────────
# R1 CRT variant: widget/machines
# 7 machines make 7 widgets in 7 minutes -> 1 machine 1 widget in 7 min -> 140 machines 140 widgets in 7 min
rec("R1 answer minutes", 7)
# variant used: a lathe + a bit cost $1.34 total; lathe costs $1.20 more than the bit
# bit = (1.34-1.20)/2
bit = (Fraction(134, 100) - Fraction(120, 100)) / 2
rec("R1b bit cost", float(bit), )
rec("R1b lathe cost", float(bit + Fraction(120, 100)))

# R3 variable tracking
assigns = [("X1", 42), ("X2", "X1"), ("X3", 17), ("X4", "X2"), ("X5", "X3"),
           ("X6", "X4"), ("X7", "X5"), ("X8", "X6"), ("X9", "X8")]
env = {}
for name, val in assigns:
    env[name] = val if isinstance(val, int) else env[val]
rec("R3 vars equal 42", sorted([k for k, v in env.items() if v == 42]))
rec("R3 vars equal 17", sorted([k for k, v in env.items() if v == 17]))

# R4 logic grid: 4 hosts, 4 models, 4 GPUs
hosts = ["halo", "shaft", "steffi", "mox"]
models = ["glm", "qwen", "gemma", "laguna"]
gpus = ["3090", "3080", "5060ti", "a4000"]
sols = []
for mp in permutations(models):
    for gp in permutations(gpus):
        M = dict(zip(hosts, mp))
        G = dict(zip(hosts, gp))
        # clues
        if M["halo"] == "glm":
            continue                                  # 1: halo does not run glm
        if G["shaft"] != "3080":
            continue                                  # 2: shaft has the 3080
        if M["steffi"] == "gemma":
            continue                                  # 3: steffi is not the gemma box
        host_glm = [h for h in hosts if M[h] == "glm"][0]
        if G[host_glm] != "3090":
            continue                                  # 4: glm runs on the 3090
        host_qwen = [h for h in hosts if M[h] == "qwen"][0]
        if G[host_qwen] == "a4000":
            continue                                  # 5: qwen is not on the a4000
        if M["mox"] != "laguna" and G["mox"] != "5060ti":
            continue                                  # 6: mox runs laguna or has the 5060ti
        if M["shaft"] == "laguna":
            continue                                  # 7: shaft does not run laguna
        if G["halo"] == "a4000":
            continue                                  # 8: halo does not have the a4000
        sols.append((M, G))
rec("R4 solution count", len(sols))
for s in sols:
    rec("R4 solution", s)

# R5 quantified truth network (knights/knaves with cardinality)
# 7 agents A..G. Statements:
names = list("ABCDEFG")
def check(t):
    T = dict(zip(names, t))
    n_true = sum(t)
    st = {
        "A": (n_true >= 4),
        "B": (not T["A"]),
        "C": (T["A"] and T["B"]),
        "D": (n_true == 3),
        "E": (T["D"] or T["F"]),
        "F": (not T["E"]),
        "G": (sum(1 for x in "ABCD" if T[x]) == 2),
    }
    return all(T[k] == st[k] for k in names)
sol5 = [t for t in product([False, True], repeat=7) if check(t)]
rec("R5 solution count", len(sol5))
for s in sol5:
    rec("R5 truth-tellers", [n for n, v in zip(names, s) if v])
    rec("R5 liars", [n for n, v in zip(names, s) if not v])

# ───────────────────────── MATH ──────────────────────────
# M1 last three digits of F(200)
a, b = 0, 1
for _ in range(200):
    a, b = b, (a + b)
rec("M1 F(200)", a)
rec("M1 F(200) mod 1000", a % 1000)

# M2 number of length-12 strings over {A,B,C} with no two adjacent equal AND not starting/ending same
cnt = 0
for s in product("ABC", repeat=12):
    if any(s[i] == s[i + 1] for i in range(11)):
        continue
    if s[0] == s[-1]:
        continue
    cnt += 1
rec("M2 count", cnt)

# M3 multiplicative order of 7 mod 1013
p = 1013
def is_prime(n):
    if n < 2: return False
    i = 2
    while i * i <= n:
        if n % i == 0: return False
        i += 1
    return True
rec("M3 1013 prime?", is_prime(p))
k, x = 1, 7 % p
while x != 1:
    x = x * 7 % p
    k += 1
rec("M3 ord_1013(7)", k)

# M4 lattice points in annulus 30 <= x^2+y^2 <= 2026
import math
c = 0
R = int(math.isqrt(2026)) + 1
for x in range(-R, R + 1):
    for y in range(-R, R + 1):
        v = x * x + y * y
        if 30 <= v <= 2026:
            c += 1
rec("M4 lattice count", c)

# M5 binary strings length 28, no three consecutive 1s
n = 28
dp = {(0, 0): 1}
for _ in range(n):
    nd = {}
    for (run, _z), v in dp.items():
        # place 0
        nd[(0, 0)] = nd.get((0, 0), 0) + v
        if run < 2:
            nd[(run + 1, 0)] = nd.get((run + 1, 0), 0) + v
    dp = nd
rec("M5 count", sum(dp.values()))
# brute-force check at n=18
bf = sum(1 for s in product("01", repeat=18) if "111" not in "".join(s))
dp2 = {(0, 0): 1}
for _ in range(18):
    nd = {}
    for (run, _z), v in dp2.items():
        nd[(0, 0)] = nd.get((0, 0), 0) + v
        if run < 2:
            nd[(run + 1, 0)] = nd.get((run + 1, 0), 0) + v
    dp2 = nd
rec("M5 bruteforce n=18 match", bf == sum(dp2.values()), )
rec("M5 n=18 value", bf)

for k, v in OUT:
    print(f"{k:42s} : {v}")
