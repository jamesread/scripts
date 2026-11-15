---
name: jwr-logo-style
description: Checks a logo.svg in the current directory against the jwr flat-logo style (512x512 canvas, fixed margin, bold colours with subtle same-hue gradients, fills at a fixed contrast ratio of about 14-16:1 against the black outline whatever the hue, and a consistent black outline stroke of 20.7874px) and writes logo.fixed.svg when updates are needed. Use when creating, normalising, or reviewing a project logo, or when the user mentions jwr-logo-style, logo consistency, or logo stroke width.
---

# jwr-logo-style

Run in a directory containing `logo.svg`. If the logo already conforms, say so and write nothing. Otherwise write the corrected logo to `logo.fixed.svg` in the same directory. Never modify `logo.svg` itself.

## The style

| Rule | Value |
|---|---|
| Canvas | `width="512" height="512" viewBox="0 0 512 512"` (unitless px) |
| Outline stroke | **`#000000`, effective width `20.7874` px** (5.5 mm at 96 dpi), opacity 1, `stroke-linecap:butt`. Outer silhouettes use `stroke-linejoin:bevel`. This is the most important rule: the width must match across every logo. |
| Effective width | `stroke-width` × the scale of every ancestor `transform` (√\|det\|). A path with `stroke-width:10` inside `scale(2)` is correct. `vector-effect:non-scaling-stroke` means the width is used as written. |
| Margin | The *visual* bounding box (stroke included) sits **22 px ±4** from the canvas edge on its longest axis, so the artwork spans ~468 px. Square-ish artwork gets 22 px on all sides. On the shorter axis it is centred; an optical offset of up to 16 px is fine. |
| Grid | Place nodes on a 32 px grid (16 px for finer detail) where the shape allows. It keeps shapes crisp and symmetric. |
| Colour | Few, bold, saturated colours (HSL saturation ≥ 40%). At most 3 hue families besides black/white. No shadows, glows, blur filters or textures. Lightness is set by the contrast rule below, not by HSL lightness. |
| Contrast with the outline | Every coloured fill and gradient stop has a WCAG contrast ratio of **13.5–16.5:1 against `#000000`** (aim for 14–16:1). This is measured from the reference SickRock logo, whose greens run from `#d4ec9d` (16.3:1) to `#b1e24e` (13.9:1). It keeps the black division lines equally easy to make out in every logo, whatever its hue. |
| Gradients | Subtle and same-hue: hue spread ≤ 8°, lightness difference roughly 5–18 points. Linear, vertical, lighter at the top and darker at the bottom (`gradientUnits="userSpaceOnUse"`, `x1 == x2`). A stop placed before `1`, e.g. `0.63`, holds the darker shade across the lower part. |
| Adjacent regions | Neighbouring regions of the same colour are told apart by a small lightness step (≈5–10 points) in the same hue, not by a new hue. For example, an inner facet is slightly darker or more saturated than the outer one. |
| Layering | Fill shapes sit underneath. Black outlines go on separate top paths (`fill:none`, or `fill-opacity:0`). Outlines are therefore always drawn above every fill, and the internal division lines use the same stroke width as the silhouette. A 1 px hairline on a fill shape that is hidden under an outline is harmless. |

### Contrast across hues

Hues differ a lot in luminance. A green or yellow reaches 14–16:1 while still looking strong, but blue, purple, pink and red only get there when they are quite light (HSL lightness of 85–90%). Do not use HSL lightness to match colours across hues; use the contrast ratio. To keep the lighter hues from looking washed out, push their saturation up to 100%. Suggested starting points, at full saturation unless noted (the gradient top is ≈16:1, the bottom ≈14:1):

| Hue | Gradient top | Gradient bottom |
|---|---|---|
| Green (reference, S≈70%) | `#d4ec9d` | `#b1e24e` |
| Yellow | `#ffe045` | `#facf00` |
| Orange | `#ffdab6` | `#ffc892` |
| Red | `#ffd8d8` | `#ffc5c5` |
| Pink | `#ffd5ea` | `#ffc1e0` |
| Purple | `#ecd9ff` | `#e4c8ff` |
| Blue | `#c9e4ff` | `#b0d7ff` |
| Cyan | `#98eeff` | `#5de4ff` |

The checker computes the contrast for each fill and stop. When one is out of range it suggests a replacement with the same hue and saturation.

## Procedure

1. Run the checker from the directory that holds the logo. It needs `python3` with `lxml`, and `inkscape` on PATH to measure the visual bounding box:

   ```sh
   python3 ~/.claude/skills/jwr-logo-style/logo_style.py fix
   ```

   This prints a PASS/WARN/FAIL/INFO report for `logo.svg`. If anything needs a mechanical fix, it then writes `logo.fixed.svg` and prints a second report on that file. The mechanical fixes are:
   - normalising the canvas to 512×512 (the content is wrapped in a group `logo-style-fit` with a transform);
   - setting every outline stroke to an effective 20.7874 px, accounting for transforms, and turning near-black stroke colours into `#000000`;
   - scaling and centring the artwork so the margins conform. The fixer iterates, because the stroke widths are re-normalised after each scale step.

   `check` instead of `fix` reports only (exit 1 on FAIL).

2. Read the WARN lines and use judgement on what the script leaves alone. Edit `logo.fixed.svg` (copy `logo.svg` to it first if the script did not write one):
   - **Muted or too many colours**: push colours toward bold, saturated versions of the same hues, and merge near-duplicate hues.
   - **Contrast vs black outline out of range**: keep the hue, and move the lightness until the ratio is 14–16:1. The `try #xxxxxx` in the WARN line does that for one colour. For a gradient, put the top stop near 16:1 and the bottom near 14:1 so the gradient survives; don't apply the same suggestion to both stops. Raise the saturation if the result looks washed out.
   - **Gradient too strong / multi-hue / wrong direction**: rebuild it as a vertical, same-hue, light-top-to-dark-bottom gradient with a lightness Δ of about 5–18.
   - **Coloured outline strokes**: if a thick stroke is a deliberate colour accent rather than an outline, leave it, but say so. Otherwise make it black.
   - **No outlines**: add black outline paths over the silhouette and the main internal divisions, at the standard width.
   - Remove filters, drop shadows and raster images if present.
   - Keep the artwork's design and proportions. This skill normalises the style; it does not redesign logos.

3. Re-run `python3 ~/.claude/skills/jwr-logo-style/logo_style.py check logo.fixed.svg` until there are no FAILs. Then render it to look at it:

   ```sh
   inkscape logo.fixed.svg --export-type=png --export-filename=/tmp/logo.fixed.png -w 256
   ```

   View the PNG and compare it with `logo.svg`. Check the strokes look equally heavy and nothing is clipped.

4. Report what changed, and any WARNs you deliberately left. If no changes were needed, say that `logo.svg` already conforms and that `logo.fixed.svg` was not written.

## Notes

- Preserve Inkscape metadata (`sodipodi:*`, `inkscape:*`) and ids. Edit only what the style requires.
- A `<style>` element (CSS classes) is not evaluated by the checker. Inline those styles into the elements before trusting the stroke report.
- Text in a logo should be converted to paths, because fonts are not guaranteed where the SVG is displayed.
