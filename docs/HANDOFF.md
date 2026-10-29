# Handoff: continue the project in a new chat

Paste everything below into a new chat.

---

I'm building a faceless YouTube channel and an automatic video maker.
Repo: **github.com/artyom-black/yt-story-video-maker** (public; you have push access via the session).
Read `docs/HANDOFF.md`, `characters/ai/README.md` and `maker/art_lab.py` first.

## The goal
- MrBeast-level videos, judged on MrBeast's principles: title and thumbnail first, the hook delivered in
  the first minute, re-engagements at about 3:00 and 6:00, rising stakes, no dull moments, an abrupt ending.
  Every decision is judged by whether it gets the click and keeps people watching.
- Format: three friends (**Kai, Iris, Bob**) are thrown into the past and compete in challenges and bets,
  like "$1 vs $1,000,000 Life in the Middle Ages". No narrator. Adult audience (18+), not a kids' show.
- One 10-minute video a week. I paste a story .txt into `stories/new/`, click Run on GitHub Actions,
  then download the MP4, 3 thumbnails and the upload text. No manual editing.
- Channel name: **Kai Films**, handle **@KaiFilms**. I'm in Armenia.
- I want quality over speed.

## Current phase: characters ONLY
We are building the characters from scratch with AI. Don't work on the video or the renderer yet.

- AI art: **Cloudflare Workers AI**, model `@cf/black-forest-labs/flux-2-klein-4b`, free tier
  (10,000 neurons a day, about 115 pictures at 768x1024, reset 00:00 UTC = 04:00 Armenia). No paid plan for now.
- Runs through the GitHub workflow **"Art lab"** (`.github/workflows/art-lab.yml`, input `task`).
  The secrets `CF_ACCOUNT_ID` and `CF_API_TOKEN` are set. Results get force-pushed to the `art-lab` branch;
  clone it to look at them.
  Start a run with: `gh api -X POST repos/artyom-black/yt-story-video-maker/actions/workflows/art-lab.yml/dispatches -f ref=main -f "inputs[task]=NAME"`
- Style: rich 2D animated-comedy look (`RICH_STYLE` in `art_lab.py`), bold outlines, cel shading.
- **Rule: every character looks 20 to 24 years old.** No stubble or wrinkles, but not childish either.

### The trio (new designs)
| | Colour | Style |
|---|---|---|
| **Kai** (lead, curious) | Red | Deep red hoodie, dark blue jeans, dark grey sneakers, short black side-swept hair. **Master locked:** `characters/ai/kai_master.png` (+ `kai_master_ref.png`, 384x512, sent to the AI) |
| **Iris** (smart) | Blue | Not a hoodie. Smart style of her own, e.g. a fitted cobalt-blue blazer with the sleeves pushed up, a white top, dark trousers, glasses. To design. |
| **Bob** (clueless, funny) | Yellow | E.g. an oversized mustard puffer vest, a grey tee, baggy cargo pants, socks with sandals, a bigger build. To design. |

Thumbnails use yellow arrows and circles (not red, which would fight Kai's hoodie).

### Kai progress
- Approved: emotion set **version 1** of all 10 (neutral, talk_closed, talk_open, excited, shocked,
  laughing, scared, disgusted, thinking, pointing), front view (task `kai_set`, seeds `3000`).
- Turnaround (task `kai_turnaround`): consistent, but **rejected for leg physics**. In the turned and side
  views the feet point in opposite directions. Low and high camera angles barely differed from the front.
- **Next step:** redo the turnaround with 4 candidates per angle and a prompt that forces both feet to
  point the same way as the body (correct anatomy). Then **zoom in on the feet, legs, hands and face of
  every picture** and delete any with physics errors before I see them.

### The plan for each character (model sheet)
1. Turnaround: front, ¾ left, ¾ right, side left, side right, back (plus low and high angles, optional).
   I approve one master per angle.
2. Every emotion from every main angle. Always send 2 references: the front master and the matching
   angle master.
3. Pointing in every direction: left, right, up, down, and at the camera.
4. Close-ups (waist-up and face) for each emotion, from the front and both ¾ angles.
5. Talking mouth pairs: the same picture with only the mouth changed (open or closed).
- **No mirror-flipping** (it would flip Kai's side-swept fringe). Delete anything that doesn't match the master.
- About 130 to 150 pictures per character. Then Iris and Bob get the same treatment.

### After the characters (later, not now)
- AI backgrounds per video (the test was good: the hut and castle hall looked like a real show).
- A curated professional sound kit and music, approved once (I rejected the synthesized sounds).
- A new MrBeast-style editor using the character sprites, then a remake of story
  `stories/new/001-dollar-vs-million-middle-ages.txt`.
- Selfie profile picture (Kai, Iris, Bob), made from the three masters. New banner.
- A PDF guide plus the template at the end.

## How to work with me
- Go step by step, show me pictures, explain in simple words, and don't ask more than needed.
- Never ask me for push access to other repos. API keys go only into GitHub Secrets.
- Commits: author `Claude <noreply@anthropic.com>`.
