# yt-story-video-maker

Turns a story `.txt` file into a finished YouTube video with 3 thumbnails.

## How to make a video
1. Paste [stories/template.txt](stories/template.txt) into ChatGPT or Claude with your topic.
2. Save the answer as a new file in `stories/new/`, e.g. `002-ancient-egypt.txt`.
3. Go to **Actions → Make video → Run workflow → Run workflow**.
4. When it finishes (about 45-75 minutes), open the run and download **VIDEO-...** at the bottom.
   Inside: the MP4, `thumbnail_1/2/3.png`, and `upload.txt` (title, description, sources, tags).

The story then moves to `stories/done/` automatically.

## Parts
- Story format: [docs/story-format.md](docs/story-format.md), checker: `python -m maker.story FILE`
- Cast: [characters/cast.md](characters/cast.md), voices: [voices.json](voices.json) (never change after publishing)
- Engine: `maker/render.py` (video), `maker/backgrounds.py` (places and props), `maker/sound.py` (music, effects),
  `maker/thumbnail.py` (thumbnails), `.github/workflows/make-video.yml` (the Run button)
