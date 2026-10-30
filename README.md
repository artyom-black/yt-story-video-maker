# yt-story-video-maker

Turns a story `.txt` file into a finished YouTube video with 3 thumbnails.

## How to make a video
1. Paste [template.txt](template.txt) into ChatGPT or Claude with your topic.
2. Paste the answer into [new-story.txt](new-story.txt) and save (commit).
3. Wait. The program runs by itself every night (or click **Actions → Make video → Run workflow**).
   Pictures take about 3 nights on the free plan.
4. When it's done, the video waits in **ready-to-upload/**: a download link, 3 thumbnails and
   `upload.txt` (title, description, tags). The story is copied to **old-stories/** and new-story.txt is emptied.
5. After uploading to YouTube: **Actions → I uploaded it → Run workflow**. The folder moves to **old-videos/**.

To redraw a picture you don't like: **Actions → Make video → Run workflow**, type its number from the
picture sheet in the REDO box (e.g. `12, 32b`).

## Parts
Everything the program needs is in **program/**.
- Story format: [docs/story-format.md](program/docs/story-format.md), checker: `python -m maker.story FILE`
- Cast: [program/characters/cast.md](program/characters/cast.md), voices: [program/voices.json](program/voices.json) (never change after publishing)
- Engine (all in `program/`): `maker/render.py` (video), `maker/backgrounds.py` (places and props), `maker/sound.py` (music, effects),
  `maker/thumbnail.py` (thumbnails), `.github/workflows/make-video.yml` (the Run button)
