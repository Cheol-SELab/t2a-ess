"""Build the LLM inputs and the scorer manifest from the English data.

Benchmark inputs (MUMT/NGHE/AV x easy/medium/hard): the body paragraphs of each benchmark realization, without
the title line (which names the difficulty) and the block quote (which states that the text was generated from
the gold), numbered [P1]..[Pn]; `paragraph_to_units` comes from the gold's `benchmark_realizations`.
Sealed inputs (nine scenarios): the sealed text as written ([P1]..[P13]); paragraph Pk is source unit Pk.
usage: python experiments/llm/make_inputs.py
"""
import hashlib, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(HERE, "inputs")
os.makedirs(OUT, exist_ok=True)
rel = lambda p: os.path.relpath(p, ROOT).replace(os.sep, "/")  # noqa: E731

manifest = {}
for key, k in (("MUMT", "mumt"), ("NGHE", "nghe"), ("AV", "av")):
    gold_path = os.path.join(ROOT, "data", "gold", k, f"{k}.gold.json")
    gold = json.load(open(gold_path, encoding="utf-8"))["text2activity_extraction_model"]
    for br in gold["benchmark_realizations"]:
        text = open(os.path.join(os.path.dirname(gold_path), br["document"]), encoding="utf-8").read()
        paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip() and not p.lstrip().startswith(("#", ">"))]
        para_units = {i + 1: [] for i in range(len(paras))}
        for entry in br["source_unit_map"]:
            for idx in entry["paragraph_index"]:
                para_units[idx].append(entry["source_unit_id"])
        assert all(para_units.values()), (key, br["difficulty"], para_units)
        body = "\n\n".join(f"[P{i + 1}] {p}" for i, p in enumerate(paras))
        name = f"{key}_{br['difficulty']}"
        open(os.path.join(OUT, name + ".txt"), "w", encoding="utf-8", newline="\n").write(body + "\n")
        manifest[name] = {"domain": key, "difficulty": br["difficulty"], "gold": rel(gold_path), "source_document": br["document"],
                          "coverage": "data/gold/coverage_requirements.json", "coverage_key": k, "paragraphs": len(paras),
                          "paragraph_to_units": {f"P{i}": u for i, u in para_units.items()},
                          "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()}
for k in ("port", "dc", "fire", "green", "water", "blackout", "tunnel", "cold", "ship"):
    src = os.path.join(ROOT, "data", "sealed", k, f"{k}.txt")
    text = open(src, encoding="utf-8").read()
    paras = re.findall(r"^\[(P\d+)\]", text, re.M)
    name = f"{k.upper()}_sealed"
    open(os.path.join(OUT, name + ".txt"), "w", encoding="utf-8", newline="\n").write(text.rstrip("\n") + "\n")
    manifest[name] = {"domain": k.upper(), "difficulty": "sealed", "gold": f"data/sealed/{k}/{k}.gold.json", "paragraphs": len(paras),
                      "paragraph_to_units": {p: [p] for p in paras}, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
os.makedirs(os.path.join(HERE, "scoring", "inputs"), exist_ok=True)
json.dump(manifest, open(os.path.join(HERE, "scoring", "inputs", "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print({k: v["paragraphs"] for k, v in manifest.items()})
