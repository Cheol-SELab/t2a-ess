"""Move run records that failed for infrastructure reasons (session/usage limit, CLI error) together with their
attempt folders to runs/_infra_failed/<utc>/, so that a rerun starts clean and the failures stay auditable.
Records that failed for any other reason (format, truncation) are left in place and reported.
usage: python experiments/llm/archive_infra_failed.py
"""
import datetime, glob, json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "runs")


def main():
    stamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    moved, other = 0, []
    for f in glob.glob(os.path.join(RUNS, "*", "*", "*_r*.json")):
        if f.endswith(".score.json") or "_infra_failed" in f or "_e2e" in f:
            continue
        m = json.load(open(f, encoding="utf-8"))["meta"]
        if m.get("ok"):
            continue
        if m.get("failure") != "infrastructure":
            other.append(os.path.relpath(f, RUNS))
            continue
        rel = os.path.relpath(f, RUNS)
        dst = os.path.join(RUNS, "_infra_failed", stamp, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(f, dst)
        if os.path.isdir(f[:-5]):
            shutil.move(f[:-5], dst[:-5])
        moved += 1
    print(f"moved {moved} infrastructure failures to runs/_infra_failed/{stamp}; other failures left: {other}")


if __name__ == "__main__":
    main()
