"""Shared helpers of the LLM analyses: locating runs, scoring them with scoring/score.py, and the paper's metrics.

Metrics of one scored run (as in the paper):
  weak  pooled micro-F1 of the weak slot types (flows, observations, controls): TP, predictions, and gold pooled
  rel   normalized relation F1 (relation types mapped onto the contract)
  slot  overall slot micro-F1
  S     (weak + rel) / 2
"""
import glob, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LLM = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(LLM))
RUNS = os.path.join(LLM, "runs")
SCORER = os.path.join(LLM, "scoring", "score.py")
MODELS = ["claude-sonnet-5", "claude-opus-5-5"]
WEAK = ["flows", "observations", "controls"]
SEALED = ["PORT_sealed", "DC_sealed", "FIRE_sealed", "GREEN_sealed", "WATER_sealed", "BLACKOUT_sealed", "TUNNEL_sealed", "COLD_sealed", "SHIP_sealed"]
BENCH = ["MUMT_easy", "NGHE_easy", "AV_easy"]


def run_files(cond, model=None, inputs=None, ok_only=True):
    out = []
    for m in ([model] if model else MODELS):
        for f in sorted(glob.glob(os.path.join(glob.escape(os.path.join(RUNS, cond, m)), "*_r*.json"))):
            if f.endswith(".score.json"):
                continue
            meta = json.load(open(f, encoding="utf-8"))["meta"]
            if ok_only and not meta.get("ok"):
                continue
            if inputs and meta["input"] not in inputs:
                continue
            out.append(f)
    return out


def score(files, manifest=None, suffix=".score.json", env_extra=None):
    """Score runs that have no score file yet (the scorer writes <run>.score.json; with `manifest` a different gold
    manifest is used and the result goes to <run><suffix>)."""
    todo = [f for f in files if not os.path.exists(f[:-5] + suffix)]
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1", **(env_extra or {}))
    if manifest:
        env["T2A_MANIFEST"] = manifest
        env["T2A_SCORE_SUFFIX"] = suffix
    for i in range(0, len(todo), 40):
        subprocess.run([sys.executable, SCORER, ROOT] + todo[i:i + 40], check=True, env=env, stdout=subprocess.DEVNULL)
    return [f[:-5] + suffix for f in files]


def metrics(score_path):
    s = json.load(open(score_path, encoding="utf-8"))
    pt = s["slots"]["per_type"]
    tp = sum(pt[t]["tp"] for t in WEAK)
    pr = sum(pt[t]["pred"] for t in WEAK)
    g = sum(pt[t]["gold"] for t in WEAK)
    p, r = (tp / pr if pr else 0), (tp / g if g else 0)
    w = 2 * p * r / (p + r) if p + r else 0
    R = s["relations"]["normalized"]
    return {"S": (w + R["f1"]) / 2, "weak": w, "weak_p": p, "weak_r": r, "rel": R["f1"], "rel_p": R["precision"],
            "rel_r": R["recall"], "slot": s["slots"]["micro"]["f1"], "actions": pt["actions"]["pred"], "gold_actions": pt["actions"]["gold"],
            "weak_tp": tp, "weak_pred": pr, "weak_gold": g}


def model_of(path):
    return os.path.basename(os.path.dirname(path))


def input_of(path):
    return json.load(open(path if not path.endswith(".score.json") else path[:-11] + ".json", encoding="utf-8"))["meta"]["input"]
