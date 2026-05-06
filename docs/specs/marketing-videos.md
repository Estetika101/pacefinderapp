# Marketing videos — short looping clips on the marketing site + GitHub README

## Purpose
The product feels static in screenshots — the live dashboard and telemetry comparison are *motion-driven* features. Short looping video clips on the marketing site and the GitHub README show what the product actually does. Cheaper than a full demo video, more compelling than stills.

## Behavior

### Surfaces

**Marketing site (`pacefindermarketing`):**
- Embedded with `<video autoplay loop muted playsinline preload="metadata">` and an MP4 source
- Hosted as static files in `public/videos/`
- Vercel CDN-serves them; no transcoding needed
- Sized to the layout context (don't ship 4K for a 600×400 hero)

**GitHub README (`pacefinderapp`):**
- MP4 uploaded via GitHub's web UI (drag-drop into a comment or issue, copy the resulting `https://github.com/user-attachments/assets/...` URL, then paste that URL into the README)
- GitHub embeds with native player + controls; no autoplay (which is fine on README — user opts in)
- Cannot be done via `gh` CLI — manual step

### Three clips to record

| # | Clip | Length | Where it goes |
|---|---|---|---|
| 1 | **Live dashboard during a hot lap** — speed, throttle, brake, slip ticking in real time | 6–8s loop | Hero of marketing site + top of README |
| 2 | **Telemetry comparison** — hovering across the speed/throttle/brake/delta charts of two laps | 5–6s | Marketing "Features" section + README under "Lap comparison" |
| 3 | **Track map building** — the colorized racing line forming as you drive a lap | 5–7s | Marketing "Preview" section, optional in README |

Clips loop seamlessly — start and end frames should match if possible.

### Encoding settings

| Setting | Value |
|---|---|
| Container | MP4 (H.264 + AAC) |
| Resolution | 1280×720 (sufficient; smaller files than 1080p) |
| Frame rate | 30fps |
| Bitrate | ~1.5 Mbps target (~1MB per 5-second clip) |
| Audio | None — strip it; videos are muted on the site anyway |
| Pixel format | yuv420p (compatibility) |

`ffmpeg` example for re-encoding a screen capture:
```bash
ffmpeg -i raw.mov \
  -c:v libx264 -profile:v high -level 4.0 \
  -pix_fmt yuv420p -movflags +faststart \
  -an \
  -vf "scale=1280:720:flags=lanczos,fps=30" \
  -b:v 1500k -maxrate 1800k -bufsize 3000k \
  out.mp4
```

### File structure

`pacefindermarketing/public/videos/`:
```
hero-dashboard.mp4
telemetry-compare.mp4
track-map.mp4
```

Plus `.poster.jpg` files (first-frame stills) for `<video poster=...>` so layout doesn't jump while the video loads.

### Markup — marketing site

```jsx
<video
  autoPlay
  loop
  muted
  playsInline
  preload="metadata"
  poster="/videos/hero-dashboard.poster.jpg"
  className="w-full h-auto rounded-md border border-[#1a1a1a]"
>
  <source src="/videos/hero-dashboard.mp4" type="video/mp4" />
</video>
```

### Markup — GitHub README

```markdown
https://github.com/user-attachments/assets/<UUID>
```

(Pasting the URL on its own line embeds the player. No image-style markdown needed.)

### Recording checklist

Before recording:
- [ ] Forza running with a real session about to start (not paused/menu)
- [ ] Browser at the dashboard URL, tab active, scrolled to the right component
- [ ] OBS / QuickTime / equivalent set to record the browser window only (not full screen)
- [ ] Hide cursor unless the clip is *about* the cursor (clip #2 needs cursor visible for the hover demo)
- [ ] System notifications muted (no Slack/Discord pop-ups)
- [ ] Browser zoom at 100%, dev-tools closed, ad-blocker off so layout matches production

For each clip:
- [ ] Record at native resolution then downscale to 1280×720
- [ ] Trim to 5–8 seconds
- [ ] Verify start/end frames roughly match for clean loop
- [ ] Run through `ffmpeg` with the settings above
- [ ] Check final file size is ≤ 1MB (hero/key clips) or ≤ 2MB (others)
- [ ] Generate `.poster.jpg` from the first frame

## Scope
- `pacefindermarketing`: add `<video>` elements in the appropriate sections; place files in `public/videos/`; commit `.poster.jpg` stills alongside
- `pacefinderapp`: edit `README.md` to embed the GitHub-hosted video URLs (after the user uploads them via web)
- Recording + encoding: out of code scope — user does this manually

## Out of scope
- Audio narration, captions, or full demo videos longer than ~10s
- Animated GIF fallback (modern browsers all support `<video>`; GIF would be heavier and worse quality)
- A/B testing different hero clips
- Video carousel or playlist UX

## Cross-repo work
- `pacefindermarketing`: code + assets
- `pacefinderapp`: README markdown edits

## Open questions
- Should clip #2 (telemetry comparison) wait until #11 (Reference selector with cross-session laps) ships, since that's the more compelling comparison? Recommend: record once #11 lands, so the demo shows the better feature.
- Hero clip placement on the marketing site — replace the existing animated `TelemetryCanvas` component, or live alongside it? Recommend: replace. Real footage of real telemetry beats a synthetic canvas animation.
- Where do source `.mov` / `.mkv` files live? Don't commit them to the repo (large), but worth keeping somewhere referenced (iCloud drive folder?) so re-encoding is possible without re-recording.
