# Story format

Every video starts as one plain `.txt` file in the `stories/` folder.
Any AI chat (Claude, ChatGPT, Gemini...) can write it using the prompt template.
The program reads this file and builds the video from it. Nothing else is needed.

Plain text with simple `KEY: value` lines was chosen on purpose: chat apps copy it
cleanly, you can read and edit it yourself, and small mistakes are easy to spot.

## 1. Header (top of the file, once)

```
TITLE: What If You Lived One Day in Ancient Rome?
THUMBNAIL_TEXT: 24 HOURS IN ROME
THUMBNAIL_IDEA: KAI shocked face, holding a gladiator helmet, Colosseum on fire behind him
THUMBNAIL_IDEA: IRIS pointing at a giant clock, crowd of Romans staring at the camera
THUMBNAIL_IDEA: BOB in a toga running from a chariot, huge "DAY 1" sign
DESCRIPTION: Two or three sentences for the YouTube description.
TAGS: ancient rome, history, what if, roman empire
```

| Key | Required | Notes |
|---|---|---|
| TITLE | yes | Max 70 characters. A question or a "what if" works best. |
| THUMBNAIL_TEXT | yes | 3 words or fewer if possible, max 25 characters. |
| THUMBNAIL_IDEA | yes, 3 times | One line each. The program makes one thumbnail per idea. |
| DESCRIPTION | yes | For YouTube. |
| TAGS | no | Comma separated. |

## 2. Scenes (repeat for the whole story)

```
=== SCENE 1 ===
BEAT: hook
PLACE: Rome, 80 AD, a crowded street at sunrise, smoke from bakeries
CAST: KAI, IRIS
EXTRAS: Roman merchants, a goat
MOOD: curious
CAMERA: zoom-in
MUSIC: mystery
SFX: crowd
NARRATOR: You wake up. The air smells like smoke and bread. And someone is yelling at you in Latin.
KAI: Uh... why is everyone wearing bedsheets?
IRIS: Those are togas, Kai. And we have exactly twenty-four hours to survive here.
```

| Key | Required | Allowed values |
|---|---|---|
| BEAT | yes | `hook`, `setup`, `rise`, `twist`, `peak`, `payoff`, `outro` |
| PLACE | yes | Free text: where and when, as visual as possible. |
| CAST | yes | Who is on screen: `KAI`, `IRIS`, `BOB`, a backup character name, or `NONE`. |
| EXTRAS | no | Background people/things, generated fresh each video. |
| MOOD | yes | `curious`, `funny`, `tense`, `scary`, `sad`, `epic`, `calm`, `shock` |
| CAMERA | no (default `still`) | `still`, `zoom-in`, `zoom-out`, `pan-left`, `pan-right`, `shake`, `slow-push` |
| MUSIC | no (keeps previous) | `mystery`, `tension`, `action`, `comedy`, `sad`, `epic`, `calm`, `none` |
| SFX | no | Comma separated: `crowd`, `whoosh`, `boom`, `swords`, `thunder`, `wind`, `fire`, `footsteps`, `water`, `ding`, `gasp`, `heartbeat` |
| NARRATOR / name | at least 1 line | Spoken lines, in order. Speaker must be `NARRATOR` or someone in CAST. |

## 3. Rules the checker enforces

- Scene 1 must be `BEAT: hook`. The last scene must be `payoff` or `outro`.
- At least one `twist` every 12 scenes (roughly every 2-3 minutes), so viewers never feel safe leaving.
- A scene should be short: 15-70 spoken words. Short scenes mean the picture changes often.
- Total spoken words between 1,400 and 2,800, which is roughly 10-20 minutes of video.
- Every speaker must be NARRATOR or someone listed in that scene's CAST.

Problems are reported as **errors** (the video will not be made) or **warnings**
(the video is made, but the story may be weaker).
