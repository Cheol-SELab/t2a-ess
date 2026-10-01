"""Single-pass T2A-ESS extraction with the Claude CLI (isolated; see experiments/common/claude_cli.py).

Conditions (system prompts in prompts/):
  repository  benchmark-repository.md  the repository's extraction prompt at the pinned revision (cafe example)
  bench-corr  benchmark-corrected.md   the corrected contract with the relation vocabulary of the pinned revision
  corrected   corrected-contract.md    the corrected contract used on the sealed scenarios
One call per run; the answer must be JSON with `slot_relations`. Failure policy as in the Korean runs:
2 retries after an infrastructure failure (20 s pause), 1 retry after a format failure or a truncated answer.
Records: runs/<condition>/<model>/<input>_r<k>.json (+ attempts/ with every raw answer). Existing ok records
are never overwritten.
usage: python run_llm.py --condition corrected --models claude-sonnet-5 claude-opus-5-5 --inputs PORT GREEN ... --repeats 9 [--workers 6]
"""
import argparse, concurrent.futures as cf, datetime, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))
import claude_cli as C  # noqa: E402

PROMPTS = {"repository": "benchmark-repository.md", "bench-corr": "benchmark-corrected.md", "corrected": "corrected-contract.md"}
USER_TEMPLATE = (
    "Extract the T2A-ESS slot JSON from the following scenario text.\n"
    "Use the paragraph labels P1, P2, ... as `source_unit_id` values and cite them in `source_ref`.\n"
    "Return valid JSON only.\n\n{text}"
)
INFRA_RETRIES, FORMAT_RETRIES, TIMEOUT = 2, 1, 2400


def truncated(env):
    u = env.get("usage") or {}
    it = u.get("iterations") or []
    cont = bool(it) and (u.get("output_tokens") or 0) - (it[-1].get("output_tokens") or 0) >= 1000
    return cont or env.get("stop_reason") == "max_tokens"


def job(cond, model, name, rep, out_root):
    path = os.path.join(out_root, cond, model, f"{name}_r{rep}.json")
    if os.path.exists(path) and json.load(open(path, encoding="utf-8"))["meta"].get("ok"):
        return name, rep, "skipped"
    prompt = os.path.join(HERE, "prompts", PROMPTS[cond])
    inp = os.path.join(HERE, "inputs", f"{name}.txt")
    text = open(inp, encoding="utf-8").read()
    user = USER_TEMPLATE.format(text=text)
    att = os.path.join(out_root, cond, model, f"{name}_r{rep}")
    os.makedirs(att, exist_ok=True)
    infra, fmt, n, t0, cost = INFRA_RETRIES, FORMAT_RETRIES, 0, time.time(), 0.0
    while True:
        n += 1
        env, elapsed, rc = C.run_claude(model, prompt, user, TIMEOUT)
        cost += env.get("total_cost_usd") or 0
        rec = {"attempt": n, "started_utc": datetime.datetime.utcnow().isoformat(timespec="seconds"), "elapsed_s": round(elapsed, 1),
               "returncode": rc, "is_error": env.get("is_error"), "usage": env.get("usage"), "total_cost_usd": env.get("total_cost_usd"),
               "stop_reason": env.get("stop_reason"), "models_used": list((env.get("modelUsage") or {}).keys()),
               "result_text": env.get("result"), "stderr": env.get("stderr")}
        if rc != 0 or env.get("is_error") or not env.get("result"):
            rec["failure"] = "infrastructure"
        elif truncated(env):
            rec["failure"] = "truncated"
        else:
            try:
                parsed = C.parse_json(env["result"])
                parsed = parsed.get("text2activity_extraction_model", parsed)
                rec["failure"] = None if "slot_relations" in parsed else "missing slot_relations"
            except Exception as e:  # noqa: BLE001
                rec["failure"] = f"unparsable: {str(e)[:200]}"
        json.dump(rec, open(os.path.join(att, f"attempt{n}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        if rec["failure"] is None:
            ok = True
            break
        if rec["failure"] == "infrastructure" and infra > 0:
            infra -= 1
            time.sleep(20)
            continue
        if rec["failure"] != "infrastructure" and fmt > 0:
            fmt -= 1
            continue
        ok = False
        break
    meta = {"input": name, "repeat": rep, "condition": cond, "model_requested": model, "models_used": rec["models_used"],
            "prompt": PROMPTS[cond], "prompt_sha256": C.sha_file(prompt), "input_sha256": C.sha_file(inp), "user_sha256": C.sha_text(user),
            "runner_sha256": C.sha_file(os.path.abspath(__file__)), "ok": ok, "attempts": n, "failure": rec["failure"],
            "elapsed_s": round(time.time() - t0, 1), "total_cost_usd": round(cost, 4), "usage": rec["usage"],
            "cli": "claude -p (isolated, experiments/common/claude_cli.py)"}
    json.dump({"meta": meta, "result_text": rec["result_text"] if ok else None}, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return name, rep, f"ok={ok} attempts={n} {meta['elapsed_s']:.0f}s ${cost:.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", required=True, choices=sorted(PROMPTS))
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--inputs", nargs="+", required=True)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--first-repeat", type=int, default=1)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default=os.path.join(HERE, "runs"))
    a = ap.parse_args()
    jobs = [(m, n, r) for m in a.models for n in a.inputs for r in range(a.first_repeat, a.first_repeat + a.repeats)]
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(job, a.condition, m, n, r, a.out): (m, n, r) for m, n, r in jobs}
        for f in cf.as_completed(futs):
            m = futs[f][0]
            print(datetime.datetime.utcnow().strftime("%H:%M:%S"), a.condition, m, *f.result(), flush=True)


if __name__ == "__main__":
    main()
