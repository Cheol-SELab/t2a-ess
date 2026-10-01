"""Compose paper figures from EFFBD editor renderings.

Panels are crops of the editor's own PNG output (no redrawing): each episode region reported by the
editor's region-subdivision layer, padded to include item nodes drawn on the region border.
usage: python compose_panels.py <out-dir>
"""
import json, os, sys
from PIL import Image, ImageDraw

OUT = sys.argv[1]
DPR = 2          # renderEffbdModelToDataUri captures at deviceScaleFactor 2
PAD_X, PAD_Y = 14, 40   # css px
GAP = 24         # css px between panels


def load(name):
    im = Image.open(os.path.join(OUT, name + ".png")).convert("RGB")
    boxes = json.load(open(os.path.join(OUT, name + ".boxes.json"), encoding="utf-8"))["boxes"]
    return im, boxes


def crop(im, box, pad_x=PAD_X, pad_y=PAD_Y):
    x0 = max(0, (box["x"] - pad_x) * DPR); y0 = max(0, (box["y"] - pad_y) * DPR)
    x1 = min(im.width, (box["x"] + box["width"] + pad_x) * DPR); y1 = min(im.height, (box["y"] + box["height"] + pad_y) * DPR)
    return im.crop((int(x0), int(y0), int(x1), int(y1)))


def region(boxes, suffix):
    hits = [b for b in boxes if b["kind"] == "region" and b["id"].endswith(suffix)]
    assert len(hits) == 1, (suffix, len(hits))
    return hits[0]


def node(boxes, suffix):
    hits = [b for b in boxes if b["kind"] == "node" and b.get("nodeElement") == "FunctionNode" and b["id"].endswith(suffix)]
    assert len(hits) == 1, (suffix, len(hits))
    return hits[0]


def framed(img):
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, img.width - 1, img.height - 1), outline=(205, 205, 205), width=2)
    return img


def column(images, gap=GAP * DPR):
    w = max(i.width for i in images); h = sum(i.height for i in images) + gap * (len(images) - 1)
    out = Image.new("RGB", (w, h), "white"); y = 0
    for i in images:
        out.paste(i, (0, y)); y += i.height + gap
    return out


def row(images, gap=GAP * DPR):
    w = sum(i.width for i in images) + gap * (len(images) - 1); h = max(i.height for i in images)
    out = Image.new("RGB", (w, h), "white"); x = 0
    for i in images:
        out.paste(i, (x, 0)); x += i.width + gap
    return out


def save(img, name):
    p = os.path.join(OUT, name)
    img.save(p, dpi=(300, 300))
    print(name, img.size)


mumt, mb = load("editor-mumt")
ep = {k: framed(crop(mumt, region(mb, s))) for k, s in {
    "E1": "E1 Preparation under normal comms", "E2": "E2 Observation post and FPV threat",
    "E3": "E3 EW jamming and comms degradation", "E4": "E4 Comms recovery and attack resumption"}.items()}
save(column([ep["E1"], ep["E2"]]), "fig-editor-mumt-a.png")
save(column([ep["E3"], ep["E4"]]), "fig-editor-mumt-b.png")

nghe, nb = load("editor-nghe-e2collapsed")
ng = {k: framed(crop(nghe, region(nb, s))) for k, s in {
    "E1": "E1 Site setup and Level 3 start", "E3": "E3 Fog and cyber threat response",
    "E4": "E4 Heavy rain and work stop", "E5": "E5 Recovery and mission completion"}.items()}
e2 = framed(crop(nghe, node(nb, "E2 Level 4 autonomous production"), pad_x=40, pad_y=40))
save(row([ng["E1"], column([ng["E3"], ng["E4"]])]), "fig-editor-nghe-a.png")
save(row([ng["E5"], e2]), "fig-editor-nghe-b.png")
