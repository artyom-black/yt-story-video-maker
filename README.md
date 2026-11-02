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
4. **Make the video:** Actions → Make video → **Run workflow** → green **Run workflow** button.<br>
   👉 **[Open "Make video"](https://github.com/artyom-black/yt-story-video-maker/actions/workflows/make-video.yml)**
5. When it's done, everything is in `ready-to-upload/<title>/` (thumbnail, story, description, video link).
   Nothing goes into `previous-videos/` yet.
6. Download the video from `video-link.txt` and upload it to YouTube with `thumbnail.png` and `description.txt`.
7. **Only after the video is on YouTube:** Actions → I uploaded it → **Run workflow** → leave the box empty →
   green **Run workflow** button.<br>
   👉 **[Open "I uploaded it"](https://github.com/artyom-black/yt-story-video-maker/actions/workflows/i-uploaded-it.yml)**<br>
   About 30 seconds later, the video's folder is **moved** to `previous-videos/<title>/` and **removed** from
   `ready-to-upload/`. A video is never in both folders.<br>
   If more than one video is waiting in `ready-to-upload/`, type the folder name of the one you uploaded in the box.

To redraw a picture you don't like: open
**[Make video](https://github.com/artyom-black/yt-story-video-maker/actions/workflows/make-video.yml)** → Run workflow,
type its number from the picture sheet in the REDO box (e.g. `12, 32b`).

## Program details

- Story format: [program/docs/story-format.md](program/docs/story-format.md), checker: `python -m maker.story FILE`
- How it works: [program/docs/HOW-IT-WORKS.md](program/docs/HOW-IT-WORKS.md)
- Voices: [program/voices.json](program/voices.json) (never change after publishing)
- Engine: `program/maker/render.py` (video), `backgrounds.py` (places and props), `sound.py` (music, effects),
  `thumbnail.py` (thumbnails)
