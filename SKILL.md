---
name: animation-meme-rig
description: Composite hand-drawn PNG parts into looping animation-meme GIFs and moving stickers. Use this whenever someone uploads several character parts (head, hair, arms, tie, effects) and asks to make them move — "rig this", "animate this", "make it a GIF", "make an animation meme", "make this emoji move". If several parts arrive together with any instruction about order or motion, use this skill without waiting for the word "skill". Background pattern loops, logo sprite animation, and diagnosing misaligned joints are also in scope.
---

# animation-meme-rig

The artist draws parts as separate layers and exports them as PNGs. This skill
composites those parts frame by frame into a looping GIF.

**Never generate artwork. Only use the parts you were given.**

## How to read this document

Statements here are not all equally binding. Each is labelled:

- **Constraint** — a limit of *this renderer*, not of animation. A different pipeline
  may not have it.
- **Rule** — holds regardless of art style or subject. Breaking it produces a defect.
- **Heuristic** — usually right. Judge it against the case in front of you.
- **Case note** — observed on one or two jobs. The reasoning may transfer; the
  numbers almost certainly will not.

If you find yourself applying a Case note as if it were a Rule, stop and re-measure.

## 0. Scope

This rig moves **existing 2D raster parts** with rigid per-part transforms —
translate, rotate, scale, opacity, and part swapping — composited in layers.

**Supported**
- cutout character animation from separate parts
- props, vehicles, effects
- looping stickers and GIFs
- pose-to-pose transitions
- secondary motion (lag, stagger, phase offset)

**Partially supported**
- walk and run cycles — possible, but needs limbs split at the joint; unverified here
- facial animation — works by part swapping; no morphing
- camera motion — pan and scale of the whole composite only
- multi-character scenes — works, but you compose each character's transforms yourself

**Not supported**
- mesh deformation, warping, Live2D-style rigs
- skeletal IK, bone weights, parent-transform inheritance
- automatic inbetweening
- generating artwork that does not exist

**Constraint** — the renderer applies each layer's transform independently. If a part
should follow its parent (hair following a tilting head), you add the parent's
rotation to the child's yourself when generating frames. There is no parent field.

## 1. Inspect assets before anything else

Run this first. Measure coordinates; do not judge by eye.

```bash
python3 scripts/inspect_parts.py <upload_folder>
```

It reports canvas size, format, alpha presence, and content bounding box per file.

- **Constraint — mismatched canvas sizes.** This implementation assumes every part of
  one character shares one canvas, so parts align at the same coordinates. Ask for a
  re-export. (Other rigs use per-part crops plus an anchor coordinate; that is a valid
  approach, just not this one.)
- **Rule — no alpha (flattened onto white).** Anything layered behind it disappears.
  Name the file and ask for a transparent export. If a transparent copy of the same
  part already exists, use that and move on.
- **Heuristic — duplicate bounding boxes are a warning, not proof.** `open_eye.png`
  and `closed_eye.png` legitimately share a box, as do alternate mouths and
  expressions. Compare pixel content before treating either as redundant. Deleting a
  swap state because its box matched is a real failure mode.

### Two upload accidents worth checking every time

- **Rule** — large images can be downscaled and re-encoded as JPEG in transit,
  destroying alpha. If `inspect_parts.py` reports JPEG, stop and ask for a zip
  instead; zips are not re-encoded.
- **Rule** — zips made on macOS store non-ASCII filenames in decomposed form (NFD).
  String matching on filenames then fails silently. Normalize with
  `unicodedata.normalize('NFC', name)` and build a lookup table, or copy the files to
  ASCII working names. Ignore any `__MACOSX/` folder.

## 2. Reading the brief

Briefs usually arrive as a list of poses:

```
1. bring arms and legs to the centre
2. stretch legs out, one bounce up and down
3. back to centre
4. arms out sideways, one leg beat
```

Read it as **beats**. One beat = one pose plus whatever repeats inside it.

**Rule — resolve ambiguous motion words into an explicit cycle before rendering,**
and state the reading back. "One bounce" means different things to different people.
Default convention here: *one bounce = one complete oscillation*, returning to the
starting offset. If the artist meant two, they will say so once they see it named.

## 3. Layer order — infer it from occlusion

**Rule — decide z-order from what should visually hide what, not from body-part
names.** Part names break immediately on side views, on characters with front and
back hair as separate parts, and on poses where one arm is in front and the other
behind.

Ask, per pose:

1. Which part must hide which?
2. Which seam needs to be tucked under another part to look attached?
3. Does that relationship change between poses, or hold for the whole shot?

**Heuristic — common outcomes**, offered as examples rather than laws:

| Situation | Usually | If you get it wrong |
|---|---|---|
| Arm raised above the head | In front of the head | The arm vanishes behind the head |
| Arm stretched sideways | Behind the torso | It covers the shoulder line, straps, tie |
| Legs | Behind the torso | The hip seam shows |
| Flames, smoke, effects | Behind the body | The effect covers the body and its markings |

Do not ask the artist which layer the arm belongs on. Decide, then report what you did
and why, so they can correct one judgement instead of answering ten questions.

## 4. Pivots follow the intended motion

**Rule — the pivot is determined by the movement you intend, not by the kind of part
it is.**

| Intended motion | Pivot |
|---|---|
| Swinging while attached (hair, arm, tie, flame) | The attachment point |
| Spinning in place (wheel, propeller, fan) | The part's visual centre |
| Orbiting something else | A point outside the part |
| Growing from where it is anchored | The attachment point |
| Pulsing uniformly (a glow, a heartbeat) | The part's visual centre |

**Rule — a pivot far from the part turns scaling into translation.** A 10% flame
flicker pivoted on the fuselage centre walked the flame clean off the canvas.

Measure attachment points from the alpha channel rather than eyeballing them:

```python
a = np.array(im)[..., 3] > 10
ys, xs = np.where(a)
x1 = xs.max()                                   # root on the right edge
root = (x1, int(np.median(ys[xs >= x1 - 15])))
```

## 5. Keeping parts connected

When parts do not look attached, something has to move. **Heuristic — move whichever
part damages the intended silhouette least.**

That is the actual criterion. It usually resolves to:

- The limb is drawn with a shape worth preserving → move the body instead
- The body position is fixed by the composition → move the limb, or ask for a patch part
- Neither can move → ask for an overlapping cover part
- The joint itself bends wrong → the part needs splitting at that joint

**Case note — crouching character.** A crouched leg was drawn with the thigh splaying
wider than the hip, which is correct drawing. Pulling the leg inward killed the splay
and ruined the pose; lowering the torso until the hip covered the top of the thigh
kept the original drawing intact. Diagnosis used there:

1. Measure the torso's x range at its bottom edge.
2. Measure each leg's top edge and its x range at that height.
3. If the leg's x range falls outside the torso's, lower the torso until they overlap
   where the leg widens.
4. Required drop = (y where the ranges start to overlap) − (torso bottom y).

**Case note — head burial on a crouch.** Dropping the head 40–55px toward the torso
buried the neck and read as hunching. That number is tied to that character at that
canvas size; express it as a fraction of head height if you reuse the idea, and
measure until the neck gap closes rather than trusting the figure.

**Heuristic — prefer more overlap than looks right at rest.** Under motion it reads
correctly, and gaps are far more noticeable than excess overlap.

## 6. Overlay coverage

**Rule — when one part exists to hide a seam or an unfinished silhouette on another,
verify the cover holds at every frame, not just the rest pose.**

This covers more than hair: sleeves over shoulders, a torso over a hip joint, a skirt
over legs, a helmet over a head, a vehicle body over its rider, smoke over an exhaust
seam. All the same failure.

Measure before rendering:

```python
seam = base_alpha & seam_box            # box over the area that must stay covered
exposed = (seam & ~cover_alpha).sum()   # take the worst value across all frames
```

Target the worst frame under 5% of the seam area. Above that, search over the cover
part's `dx`, `dy`, `scale`, and rotation amplitude.

**Rule — do not fix coverage by scaling the cover part up until it covers.** Coverage
is never worth losing silhouette features. Antenna hair, spikes, and cowlicks are what
identify a character; bury them and you get a helmet.

**Case note — hair over a smooth scalp.** Two of two characters drawn this way showed
the same defect: the base layer carried a smooth head silhouette and a separate hair
part supplied the texture, and at some rotations the hair stopped covering the
silhouette. That single frame looked like the head had been sliced flat — and because
it only appeared at certain angles, it read as a rendering bug rather than a coverage
problem. Worst-frame exposure went from 44% to 5.6% on one character and 32% to 3.4%
on the other, purely by adjusting offset and amplitude.

## 7. Motion that costs nothing and reads well

- **Secondary motion** — give a trailing part the same period as its parent with a
  phase offset. A tie lagging the hair by ~0.9 rad reads as the tie following the head.
- **Phase offset between characters** — with several characters on screen, offset each
  one's loop by a few frames. Identical bobbing across four characters looks mechanical.
- **Depth by amplitude** — a character further back should sway less than one in front.
  Equal amplitude flattens the image.
- **Hold most parts.** Three or four moving parts per shot is plenty. What stays still
  is what makes the moving parts read.

## 8. Render and output

```bash
python3 scripts/rig_global_palette.py spec.json 50   # shipping — the default
python3 scripts/rig.py spec.json                     # quick check on white
```

Spec format is in `references/spec-format.md`.

**Rule — use `rig_global_palette.py` for anything the artist will publish.** Giving
each frame its own adaptive palette makes some decoders draw rotated frames
incorrectly while the file inspects as perfectly fine on your side. See section 10.

This script builds one palette from all frames, keeps the background transparent, and
auto-crops to the union bounding box of every frame (second argument is the margin).

**Rule — never guess the crop from a single frame.** Union the alpha of every frame,
take the bounding box, add a margin. A crop that fits one frame will clip another.

Delivery conventions:

- **GIF** — 560–620px tall, infinite loop, one global palette
- **Sticker** — cut frame count and background complexity to meet the platform's size cap
- **Preview** — contact sheet, see section 9
- **Rule — never add a watermark**
- Treat your output as a preview; the artist re-renders the final locally

## 9. Verify

After writing the GIF, **always** build a contact sheet and look at it.

```bash
python3 scripts/contact_sheet.py <gif_path>
```

**Rule — missing parts, joint gaps, and layer-order errors do not appear in
coordinates.** They appear when you look at every frame side by side. Check the loop
seam too: the last frame should lead back into the first without a jump.

Then hand over the GIF and name what can be adjusted: bounce amplitude, beat speed,
background density, secondary-character placement.

## 10. When it only breaks on the artist's screen

Sometimes frames extracted on your side look fine and the artist still sees it broken.
**Do not guess and re-send.** Wrong guesses burn their time and their session.

1. Ask which frames look right and which do not.
2. Map the good frame numbers onto the animation cycle. If only the frames where
   `dy`/`rot` land on zero look right, the cause is encoding or resampling, not parts.
3. If the damage sits at a fixed place regardless of rotation, look at coverage
   (section 6).

If you cannot identify the cause, say so and ask for a marked-up screenshot.

**Case note — per-frame palettes.** In a 48-frame float cycle, exactly the two frames
where rotation landed on zero looked correct on the artist's machine and the other 46
did not. Cause: `convert('P', palette=ADAPTIVE)` called once per frame gives every
frame its own palette, and combined with `disposal=2` some decoders — macOS Preview
among them — draw the transitions wrong. Three wrong diagnoses were tried first
(canvas clipping, viewer thumbnail cropping, part coverage). The frame numbers were
the clue, not the pixels.

## 11. What to ask the artist for

Map the problem to the asset that solves it:

| Problem | Ask for |
|---|---|
| A joint bends wrong or cannot reach the pose | That limb split at the joint |
| Two poses snap too hard between beats | One inbetween drawing |
| An attachment point is ambiguous | A joint marker layer — same canvas size, shoulder/hip/neck marked as dots. Never rendered; it just lets you place pivots exactly |
| Overlap exposes a gap | A patch or cover part |
| The expression needs to change | Alternate face states. A single closed-eye PNG is the cheapest high-impact part there is |
| The silhouette changes substantially | New artwork for that pose — no transform will fake it |
| Seams are visible where parts meet | Part edges tinted to the body colour |

## 12. Case notes index

Verified jobs behind this document, so you can judge how far a claim generalises:

- **Crouch-and-stretch character** (sections 5, 11) — human proportions, chibi, short
  limbs, four-beat sticker loop
- **Four characters on aircraft** (sections 4, 6, 8, 10) — vehicles plus riders,
  scrolling background, 216-frame sequence, four separate characters

Two case studies. Anything in this document not marked Rule or Constraint should be
read against that number.

## 13. Not yet covered

Open, and worth a case note if you get one:

- Eight-head-tall figures. Long limbs make a 1–2° joint error visible, and arms
  probably need splitting at the elbow. Untested here.
- Walk and run cycles.
- Blinking and eyebrow rigs — the format supports part swapping, but no conventions
  are established yet.
- Camera work beyond pan and scale.
- Output formats other than GIF.
- Easing helpers. Frame values are currently computed in your own script, so timing
  quality depends entirely on how you write that script.
