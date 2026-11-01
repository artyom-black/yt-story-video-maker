# yt-story-video-maker

Turns a story `.txt` file into a finished YouTube video.

## Folders
- **main-character.jpg**: the channel's main character (every video draws him from this picture).
- **new-story.txt**: the story the program is making now.
- **stories/**: every story, named by its video title.
- **thumbnail/**: every thumbnail, named by its video title.
- **ready-to-upload/**: only the video we are working on now (download link, thumbnail, upload text).
- **old-videos/**: videos already posted on YouTube.
- **program/**: everything the program needs.

## How to make a video
1. Put the story into new-story.txt (and its thumbnail into thumbnail/ with the video's title as the name).
2. **Actions → Make video → Run workflow**.
3. When it's done, the video waits in **ready-to-upload/<title>/**.
4. After uploading to YouTube: **Actions → I uploaded it → Run workflow**. The folder moves to **old-videos/**.

To redraw a picture you don't like: **Actions → Make video → Run workflow**, type its number from the
picture sheet in the REDO box (e.g. `12, 32b`).

## Parts
Everything the program needs is in **program/**.
- Story format: [docs/story-format.md](program/docs/story-format.md), checker: `python -m maker.story FILE`
- Cast: [program/characters/cast.md](program/characters/cast.md), voices: [program/voices.json](program/voices.json) (never change after publishing)
- Engine (all in `program/`): `maker/render.py` (video), `maker/backgrounds.py` (places and props), `maker/sound.py` (music, effects),
  `maker/thumbnail.py` (thumbnails), `.github/workflows/make-video.yml` (the Run button)
