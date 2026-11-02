# yt-story-video-maker

Turns a story into a finished stickman YouTube video for a faceless history channel, made the MrBeast way:
**title and thumbnail first, then the story.**

## What's in here

| File / folder | What it is |
|---|---|
| `main-character.png` | Kai, our one main character. Every video draws him from this picture. |
| `template.txt` | The story rules (MrBeast's skills). Change only the title, send it to any AI. |
| `new-story.txt` | Paste the story the AI wrote here, then click Run. |
| `ready-to-upload/` | Videos that are finished and waiting to go on YouTube. One folder per video, named by its title. |
| `previous-videos/` | Videos already on YouTube. Same folder layout. |
| `program/` | Everything the program needs to make the video. |
| `.github/workflows/` | The Run buttons in the Actions tab. |

Every video folder (`ready-to-upload/<title>/` and `previous-videos/<title>/`) holds:

- `thumbnail.png` – the YouTube thumbnail
- `story.txt` – the story the video was made from
- `description.txt` – title, description, tags and settings to copy into YouTube
- `video-link.txt` – the download link (the video file is too big for a folder, so it lives in this repo's **Releases**)

## How to make a video

1. Open `template.txt`, put your title on the TITLE line, and send the whole text to any AI (ChatGPT, Claude, Gemini).
2. Paste the AI's answer into `new-story.txt` and save.
3. *(Optional)* Your own thumbnail: put it in `ready-to-upload/<title>/thumbnail.png`. Otherwise the program makes one.
4. **Actions → Make video → Run workflow.**
5. When it's done, everything is in `ready-to-upload/<title>/`.
6. Upload to YouTube, then **Actions → I uploaded it → Run workflow.** The folder moves to `previous-videos/`.

To redraw a picture you don't like: **Actions → Make video → Run workflow**, type its number from the picture sheet
in the REDO box (e.g. `12, 32b`).

## Program details

- Story format: [program/docs/story-format.md](program/docs/story-format.md), checker: `python -m maker.story FILE`
- How it works: [program/docs/HOW-IT-WORKS.md](program/docs/HOW-IT-WORKS.md)
- Voices: [program/voices.json](program/voices.json) (never change after publishing)
- Engine: `program/maker/render.py` (video), `backgrounds.py` (places and props), `sound.py` (music, effects),
  `thumbnail.py` (thumbnails)
