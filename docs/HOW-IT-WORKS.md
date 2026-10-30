# Kai Films video maker: how it works

## What you do
1. Write a story with `template.txt` in ChatGPT/Claude (or ask Claude) and paste it into `new-story.txt`.
2. Wait. The program runs every night by itself until the video is done.
3. Open `ready-to-upload/<the video>/`: download the video from the link, pick one of the 3 thumbnails,
   copy the title, description and tags from `upload.txt`, and upload to YouTube.
4. **Actions → I uploaded it → Run workflow**: the folder moves to `old-videos/`.

## What the program does by itself
1. **Checks the story** (every scene has a picture, a line and a mood).
2. **Records Kai** in his fixed voice, acting each line to its mood. Every line is listened back by a
   speech recogniser and recorded again if words are missing.
3. **Draws every picture** with AI: first Kai's costume for the era (always his face, always red), then one
   picture per scene showing exactly what he says, then 3 thumbnail pictures.
   Free limit: about 100 pictures a day. If a video needs more, it continues by itself the next night
   (04:20 Armenia time) and finishes then.
4. **Edits** like a YouTube pro, always by the same rules:
   - every picture moves (slow push-in, pull-out or pan); shocking moments get a fast punch-zoom and a shake;
   - key words pop up big at the exact moment Kai says them;
   - the same set of sounds for the whole video (one hit, one whoosh, one pop...), measured and trimmed so
     they're short, clean and land exactly on the word; whooshes only when the section changes;
   - music chosen by mood (tense, funny, calm, sad, epic) from fitting genres only, crossfaded when the mood
     changes, quieter whenever Kai speaks;
   - loudness set to YouTube's standard.
5. **Makes the thumbnails** (picture + big text) and the upload text.

Nothing is edited by hand, and nothing is picked at random: the same story always gives the same video.
