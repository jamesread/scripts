#!/usr/bin/env python3
"""Check (and mechanically fix) a logo.svg against the jwr logo style.

Usage:
    logo_style.py check [logo.svg]          report only; exit 1 if anything FAILs
    logo_style.py fix [logo.svg] [out.svg]  write out.svg (default logo.fixed.svg)
                                            only when a mechanical fix was needed

Mechanical fixes: canvas size/viewBox, outline stroke width and colour, and
fitting the artwork to the canvas margin. Colour/gradient findings are
reported for a human (or agent) to judge.
"""

import colorsys
import math
import os
import re
import subprocess
import sys
import tempfile

from lxml import etree

# --- The style -------------------------------------------------------------

CANVAS = 512.0                 # width == height == viewBox size, in px
STROKE_WIDTH = 20.7874         # effective outline stroke (5.5 mm @ 96 dpi)
STROKE_TOLERANCE = 0.5
STROKE_COLOR = "#000000"
HAIRLINE_RATIO = 0.25          # strokes thinner than this * STROKE_WIDTH are hairlines
MARGIN = 22.0                  # visual bbox edge -> canvas edge, on the longest axis
MARGIN_TOLERANCE = 4.0
SHORT_AXIS_OFFSET_MAX = 16.0   # allowed optical off-centre on the shorter axis

GRADIENT_MAX_HUE_SPREAD = 8.0      # degrees
GRADIENT_MIN_LIGHTNESS_DELTA = 3.0  # percentage points
GRADIENT_MAX_LIGHTNESS_DELTA = 20.0
BOLD_MIN_SATURATION = 40.0
# WCAG contrast of each fill colour against the black outline. Measured from
# the SickRock reference logo (greens #d4ec9d..#b1e24e = 16.3..13.9:1), so
# every hue keeps the black division lines equally easy to make out.
CONTRAST_MIN = 13.5
CONTRAST_MAX = 16.5
CONTRAST_TARGET = (14.0, 16.0)  # where suggested replacements are placed
MAX_HUE_FAMILIES = 3
HUE_FAMILY_WIDTH = 30.0

# --- SVG helpers -----------------------------------------------------------

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
SHAPES = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "text", "use"}
NON_DRAWABLE = {"defs", "namedview", "metadata", "title", "desc", "style", "script"}
SKIP_ANCESTORS = {"defs", "clipPath", "mask", "marker", "pattern", "symbol"}

IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def local(el):
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


def mul(m, n):
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + c * B, b * A + d * B, a * C + c * D, b * C + d * D,
            a * E + c * F + e, b * E + d * F + f)


def parse_transform(s):
    m = IDENTITY
    for name, args in re.findall(r"(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)", s or ""):
        v = [float(x) for x in re.split(r"[\s,]+", args.strip()) if x]
        if name == "matrix":
            t = tuple(v)
        elif name == "translate":
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == "scale":
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "rotate":
            r = math.radians(v[0])
            t = (math.cos(r), math.sin(r), -math.sin(r), math.cos(r), 0, 0)
            if len(v) == 3:
                t = mul(mul((1, 0, 0, 1, v[1], v[2]), t), (1, 0, 0, 1, -v[1], -v[2]))
        elif name == "skewX":
            t = (1, 0, math.tan(math.radians(v[0])), 1, 0, 0)
        else:
            t = (1, math.tan(math.radians(v[0])), 0, 1, 0, 0)
        m = mul(m, t)
    return m


def fmt_matrix(m):
    return "matrix(%s)" % ",".join("%.6g" % x for x in m)


def scale_of(m):
    return math.sqrt(abs(m[0] * m[3] - m[1] * m[2]))


def style_dict(el):
    out = {}
    for decl in (el.get("style") or "").split(";"):
        if ":" in decl:
            k, v = decl.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def set_style(el, key, value):
    d = style_dict(el)
    d[key] = value
    el.set("style", ";".join("%s:%s" % kv for kv in d.items()))
    if el.get(key) is not None:
        del el.attrib[key]


def prop(el, key, default=None):
    """Resolve a (possibly inherited) presentation property."""
    node = el
    while node is not None and isinstance(node.tag, str):
        v = style_dict(node).get(key, node.get(key))
        if v is not None and v != "inherit":
            return v
        node = node.getparent()
    return default


def length_px(v):
    m = re.match(r"^\s*([-+0-9.eE]+)\s*(px|mm|cm|in|pt|pc)?\s*$", v or "")
    if not m:
        return None
    unit = {"px": 1, None: 1, "mm": 96 / 25.4, "cm": 96 / 2.54, "in": 96, "pt": 96 / 72, "pc": 16}
    return float(m.group(1)) * unit[m.group(2)]


def ctm(el):
    m = IDENTITY
    chain = []
    node = el
    while node is not None and isinstance(node.tag, str) and local(node) != "svg":
        chain.append(node)
        node = node.getparent()
    for n in reversed(chain):
        m = mul(m, parse_transform(n.get("transform")))
    return m


def drawable_shapes(root):
    for el in root.iter():
        if local(el) not in SHAPES:
            continue
        if any(local(a) in SKIP_ANCESTORS for a in el.iterancestors()):
            continue
        yield el


NAMED = {"black": "#000000", "white": "#ffffff", "red": "#ff0000", "lime": "#00ff00", "blue": "#0000ff"}


def hex_color(v):
    v = (v or "").strip().lower()
    v = NAMED.get(v, v)
    if re.match(r"^#[0-9a-f]{3}$", v):
        v = "#" + "".join(ch * 2 for ch in v[1:])
    return v if re.match(r"^#[0-9a-f]{6}$", v) else None


def hsl(hexc):
    r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, s * 100, l * 100


def contrast_on_black(hexc):
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(int(hexc[i:i + 2], 16) / 255) for i in (1, 3, 5))
    return (0.2126 * r + 0.7152 * g + 0.0722 * b + 0.05) / 0.05


def with_contrast(hexc, target):
    """Same hue and saturation, lightness moved until contrast vs black ~= target."""
    h, s, _ = hsl(hexc)
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        r, g, b = colorsys.hls_to_rgb(h / 360, mid, s / 100)
        c = "#%02x%02x%02x" % tuple(round(v * 255) for v in (r, g, b))
        if contrast_on_black(c) < target:
            lo = mid
        else:
            hi = mid
    return c


def contrast_finding(label, c):
    ratio = contrast_on_black(c)
    if CONTRAST_MIN <= ratio <= CONTRAST_MAX:
        return None
    target = CONTRAST_TARGET[0] if ratio < CONTRAST_MIN else CONTRAST_TARGET[1]
    side = "too dark" if ratio < CONTRAST_MIN else "too pale"
    return ("WARN", "%s: %s contrast vs black outline %.1f:1 (%s; want %.1f-%.1f:1), try %s"
            % (label, c, ratio, side, CONTRAST_MIN, CONTRAST_MAX, with_contrast(c, target)))


def is_neutral(hexc):
    _, s, l = hsl(hexc)
    return s < 10 or l < 8 or l > 97


def hue_dist(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def id_index(root):
    return {el.get("id"): el for el in root.iter() if isinstance(el.tag, str) and el.get("id")}


def gradient_stops(grad, ids):
    seen = set()
    node = grad
    while node is not None and id(node) not in seen:
        seen.add(id(node))
        stops = [s for s in node if local(s) == "stop"]
        if stops:
            return stops
        href = node.get("{%s}href" % XLINK_NS) or node.get("href")
        node = ids.get(href[1:]) if href and href.startswith("#") else None
    return []


def gradient_attr(grad, key, ids):
    node = grad
    for _ in range(10):
        if node is None:
            return None
        if node.get(key) is not None:
            return node.get(key)
        href = node.get("{%s}href" % XLINK_NS) or node.get("href")
        node = ids.get(href[1:]) if href and href.startswith("#") else None
    return None


# --- Analysis --------------------------------------------------------------

def outline_strokes(root):
    """Yield (element, colour, effective_width, own_width, scale)."""
    for el in drawable_shapes(root):
        stroke = prop(el, "stroke", "none")
        if stroke in ("none", "transparent") or float(prop(el, "stroke-opacity", "1")) == 0:
            continue
        if prop(el, "display") == "none" or prop(el, "visibility") == "hidden":
            continue
        own = length_px(prop(el, "stroke-width", "1"))
        if own is None:
            continue
        k = 1.0 if prop(el, "vector-effect") == "non-scaling-stroke" else scale_of(ctm(el))
        yield el, stroke, own * k, own, k


def inkscape_bbox(svg_bytes):
    """Visual bbox (x, y, w, h) of the whole drawing, via Inkscape."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        f.write(svg_bytes)
        path = f.name
    try:
        out = subprocess.run(["inkscape", "--query-all", path], capture_output=True, text=True, timeout=120).stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    finally:
        os.unlink(path)
    first = out.strip().splitlines()[0] if out.strip() else ""
    parts = first.split(",")
    return tuple(float(p) for p in parts[1:5]) if len(parts) == 5 else None


def canvas_ok(root):
    vb = [float(x) for x in re.split(r"[\s,]+", (root.get("viewBox") or "").strip()) if x]
    return (length_px(root.get("width")) == CANVAS and length_px(root.get("height")) == CANVAS
            and vb == [0, 0, CANVAS, CANVAS])


def margin_findings(bbox):
    """Return (fails, notes) for a visual bbox."""
    x, y, w, h = bbox
    left, top, right, bottom = x, y, CANVAS - x - w, CANVAS - y - h
    notes = ["visual bbox x=%.1f y=%.1f w=%.1f h=%.1f; margins L=%.1f T=%.1f R=%.1f B=%.1f"
             % (x, y, w, h, left, top, right, bottom)]
    fails = []
    long_pair, short_pair = ((left, right), (top, bottom)) if w >= h else ((top, bottom), (left, right))
    for side in long_pair:
        if abs(side - MARGIN) > MARGIN_TOLERANCE:
            fails.append("longest-axis margin %.1f px, want %.0f±%.0f" % (side, MARGIN, MARGIN_TOLERANCE))
            break
    if abs(w - h) <= 2 * MARGIN_TOLERANCE:
        for side in short_pair:
            if abs(side - MARGIN) > MARGIN_TOLERANCE:
                fails.append("square-ish artwork: margin %.1f px, want %.0f±%.0f" % (side, MARGIN, MARGIN_TOLERANCE))
                break
    elif abs(short_pair[0] - short_pair[1]) / 2 > SHORT_AXIS_OFFSET_MAX:
        fails.append("shorter axis off-centre by %.1f px (max %.0f)"
                     % (abs(short_pair[0] - short_pair[1]) / 2, SHORT_AXIS_OFFSET_MAX))
    if min(left, top, right, bottom) < 0:
        fails.append("artwork is clipped by the canvas edge")
    return fails, notes


def analyse(root, svg_bytes):
    report = []  # (level, message)
    if canvas_ok(root):
        report.append(("PASS", "canvas %dx%d, viewBox 0 0 %d %d" % (CANVAS, CANVAS, CANVAS, CANVAS)))
    else:
        report.append(("FAIL", "canvas width=%s height=%s viewBox=%s, want %d/%d/'0 0 %d %d'"
                       % (root.get("width"), root.get("height"), root.get("viewBox"), CANVAS, CANVAS, CANVAS, CANVAS)))

    if root.find(".//{%s}style" % SVG_NS) is not None:
        report.append(("WARN", "<style> element present; CSS rules are not evaluated by this checker"))

    outlines = 0
    for el, stroke, eff, _, _ in outline_strokes(root):
        label = el.get("id") or local(el)
        if eff < STROKE_WIDTH * HAIRLINE_RATIO:
            report.append(("INFO", "%s: hairline stroke %.2f px (hidden under outlines? otherwise remove)" % (label, eff)))
            continue
        outlines += 1
        if abs(eff - STROKE_WIDTH) > STROKE_TOLERANCE:
            report.append(("FAIL", "%s: outline stroke %.3f px, want %.4f" % (label, eff, STROKE_WIDTH)))
        c = hex_color(stroke)
        if c != STROKE_COLOR:
            level = "FAIL" if c and hsl(c)[2] < 20 else "WARN"
            report.append((level, "%s: outline stroke colour %s, want %s" % (label, stroke, STROKE_COLOR)))
        if float(prop(el, "stroke-opacity", "1")) < 1:
            report.append(("WARN", "%s: stroke-opacity < 1" % label))
    if outlines == 0:
        report.append(("WARN", "no outline strokes found; the style expects black outlines"))
    else:
        report.append(("INFO", "%d outline stroke(s) checked" % outlines))

    report += colour_findings(root)

    bbox = inkscape_bbox(svg_bytes) if canvas_ok(root) else None
    if bbox:
        fails, notes = margin_findings(bbox)
        report += [("INFO", n) for n in notes]
        report += [("FAIL", f) for f in fails] or [("PASS", "margins")]
    elif canvas_ok(root):
        report.append(("WARN", "inkscape not available; margins not checked"))
    return report


def colour_findings(root):
    ids = id_index(root)
    report = []
    hues = []
    seen_grads = set()
    outlines = {el for el, _, w, _, _ in outline_strokes(root) if w >= STROKE_WIDTH * HAIRLINE_RATIO}
    for el in drawable_shapes(root):
        fill = prop(el, "fill", "#000000")
        if float(prop(el, "fill-opacity", "1")) == 0 or fill == "none":
            continue
        label = el.get("id") or local(el)
        m = re.match(r"url\(#([^)]+)\)", fill)
        if not m:
            c = hex_color(fill)
            if c and not is_neutral(c):
                hues.append(hsl(c)[0])
                if hsl(c)[1] < BOLD_MIN_SATURATION:
                    report.append(("WARN", "%s: fill %s is muted (S=%.0f%%); prefer bold colours" % (label, c, hsl(c)[1])))
                if el in outlines:
                    report.append(("INFO", "%s: outline path has fill %s; outlines should be fill:none (contrast not checked)" % (label, c)))
                else:
                    f = contrast_finding(label + " fill", c)
                    if f:
                        report.append(f)
            continue
        grad = ids.get(m.group(1))
        if grad is None or m.group(1) in seen_grads:
            continue
        seen_grads.add(m.group(1))
        stops = [hex_color(prop(s, "stop-color")) for s in gradient_stops(grad, ids)]
        stops = [s for s in stops if s]
        if len(stops) < 2:
            continue
        hs = [hsl(s) for s in stops]
        hues += [h[0] for h in hs if not is_neutral(stops[hs.index(h)])]
        spread = max(hue_dist(a[0], b[0]) for a in hs for b in hs)
        dl = max(h[2] for h in hs) - min(h[2] for h in hs)
        desc = "%s gradient %s: hue spread %.1f°, lightness Δ %.1f" % (label, "→".join(stops), spread, dl)
        if spread > GRADIENT_MAX_HUE_SPREAD:
            report.append(("WARN", desc + " — gradient should stay within one hue"))
        elif dl > GRADIENT_MAX_LIGHTNESS_DELTA:
            report.append(("WARN", desc + " — too strong; keep it subtle"))
        elif dl < GRADIENT_MIN_LIGHTNESS_DELTA:
            report.append(("INFO", desc + " — practically flat"))
        else:
            report.append(("PASS", desc))
        if local(grad) == "linearGradient":
            x1, x2 = (float(gradient_attr(grad, k, ids) or 0) for k in ("x1", "x2"))
            y1, y2 = (float(gradient_attr(grad, k, ids) or 0) for k in ("y1", "y2"))
            if not (abs(x2 - x1) < abs(y2 - y1) * 0.25 and y2 > y1 and hs[0][2] >= hs[-1][2]):
                report.append(("WARN", "%s: gradient should run top (lighter) to bottom (darker)" % label))
        if any(h[1] < BOLD_MIN_SATURATION for h, s in zip(hs, stops) if not is_neutral(s)):
            report.append(("WARN", "%s: gradient stops are muted; prefer bold colours" % label))
        for stop in stops:
            f = None if is_neutral(stop) else contrast_finding(label + " stop", stop)
            if f:
                report.append(f)

    families = []
    for h in hues:
        if not any(hue_dist(h, f) <= HUE_FAMILY_WIDTH for f in families):
            families.append(h)
    level = "WARN" if len(families) > MAX_HUE_FAMILIES else "PASS"
    report.append((level, "%d hue famil%s in fills (max %d)" % (len(families), "y" if len(families) == 1 else "ies", MAX_HUE_FAMILIES)))
    return report


# --- Fixing ----------------------------------------------------------------

def wrap_content(root):
    """Move all drawable top-level children into one group and return it."""
    group = etree.SubElement(root, "{%s}g" % SVG_NS)
    group.set("id", "logo-style-fit")
    for child in list(root):
        if child is group or not isinstance(child.tag, str) or local(child) in NON_DRAWABLE:
            continue
        group.append(child)
    return group


def normalise_strokes(root):
    changed = False
    for el, stroke, eff, own, k in list(outline_strokes(root)):
        if eff < STROKE_WIDTH * HAIRLINE_RATIO:
            continue
        if abs(eff - STROKE_WIDTH) > 1e-3:
            set_style(el, "stroke-width", "%.6g" % (STROKE_WIDTH / k))
            changed = True
        c = hex_color(stroke)
        if c != STROKE_COLOR and c and hsl(c)[2] < 20:
            set_style(el, "stroke", STROKE_COLOR)
            changed = True
    return changed


def fix(root):
    changed = False
    group = None

    if not canvas_ok(root):
        vb = [float(x) for x in re.split(r"[\s,]+", (root.get("viewBox") or "").strip()) if x]
        if len(vb) != 4:
            vb = [0, 0, length_px(root.get("width")) or CANVAS, length_px(root.get("height")) or CANVAS]
        s = CANVAS / max(vb[2], vb[3])
        m = mul((1, 0, 0, 1, (CANVAS - vb[2] * s) / 2, (CANVAS - vb[3] * s) / 2),
                mul((s, 0, 0, s, 0, 0), (1, 0, 0, 1, -vb[0], -vb[1])))
        group = wrap_content(root)
        group.set("transform", fmt_matrix(m))
        root.set("width", "%d" % CANVAS)
        root.set("height", "%d" % CANVAS)
        root.set("viewBox", "0 0 %d %d" % (CANVAS, CANVAS))
        changed = True

    changed |= normalise_strokes(root)

    for _ in range(5):
        bbox = inkscape_bbox(etree.tostring(root))
        if bbox is None:
            print("WARN: inkscape not available; artwork not fitted to margins", file=sys.stderr)
            break
        fails, _ = margin_findings(bbox)
        if not fails:
            break
        x, y, w, h = bbox
        # Strokes are re-normalised after scaling, so scale only the geometry.
        target = CANVAS - 2 * MARGIN
        s = (target - STROKE_WIDTH) / (max(w, h) - STROKE_WIDTH)
        cx, cy = x + w / 2, y + h / 2
        fit = mul((1, 0, 0, 1, CANVAS / 2, CANVAS / 2), mul((s, 0, 0, s, 0, 0), (1, 0, 0, 1, -cx, -cy)))
        if group is None:
            group = wrap_content(root)
        group.set("transform", fmt_matrix(mul(fit, parse_transform(group.get("transform")))))
        normalise_strokes(root)
        changed = True
    return changed


# --- CLI -------------------------------------------------------------------

def load(path):
    parser = etree.XMLParser(remove_blank_text=False, huge_tree=True)
    tree = etree.parse(path, parser)
    return tree, tree.getroot()


def print_report(report):
    for level, msg in report:
        print("%-4s %s" % (level, msg))
    return any(level == "FAIL" for level, _ in report)


def main(argv):
    if len(argv) < 2 or argv[1] not in ("check", "fix"):
        print(__doc__)
        return 2
    src = argv[2] if len(argv) > 2 else "logo.svg"
    tree, root = load(src)
    print("== %s" % src)
    failed = print_report(analyse(root, etree.tostring(root)))

    if argv[1] == "check":
        return 1 if failed else 0

    dst = argv[3] if len(argv) > 3 else os.path.join(os.path.dirname(src), "logo.fixed.svg")
    if not fix(root):
        print("\nNo mechanical fixes needed; %s not written." % dst)
        return 0
    tree.write(dst, xml_declaration=True, encoding="UTF-8", standalone=False)
    print("\n== %s (after mechanical fixes)" % dst)
    failed = print_report(analyse(root, etree.tostring(root)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
