# Cast

Three friends in their twenties who end up in a different time or place in every video.
Made for an adult audience (18+): realistic proportions, simple faces, muted colours.
The humour comes from what they say, not from looking cartoonish.

All three are drawn by code (`maker/characters.py`), so they look identical in every scene.
To redraw the line-up: `python -m maker.characters lineup`
To check every pose and expression: `python -m maker.characters sheet` (see `sheet.png`)

Poses: stand, point, shrug, shock, wave, scared, explain, run, facepalm.
Expressions: default, happy, shock, scared, sad, annoyed, curious, smirk, serious.
The story's MOOD picks the expression automatically; whoever is speaking gets a moving mouth.

## Acting styles (each character performs every emotion and pose differently)

- **KAI**: big, fast, open reactions. Huge eyes and eyebrows, open-mouth grins, both hands when talking,
  fidgets when standing, grabs his head when shocked. Fast, bouncy walk; sprinting run.
- **IRIS**: small, controlled, a bit smug. Arms folded when listening, one-eyebrow raises, closed-mouth
  smiles, eye-rolls. Talks with one hand, on the beat. Neat walk, efficient run.
- **BOB**: deadpan and lazy. Half-closed eyes, hands in pockets, slouch, reacts late. His shock is a stare;
  his laugh is a huge belly laugh. Slow lumbering walk, heavy flailing run.

See `acting.png` (every expression, per character) and `python -m maker.showcase out.mp4` for motion.

| | KAI | IRIS | BOB |
|---|---|---|---|
| Role | The curious one: asks what the viewer is thinking | The smart one: explains, sometimes overconfident | The funny one: dry jokes, reacts, gets into trouble |
| Never changes | Messy black hair with a cowlick, burnt-orange hoodie with pocket, dark jeans, dark sneakers | Dark brown ponytail, rectangular glasses, teal jacket over white tee, black jeans, white sneakers | Olive beanie, brown beard, red flannel shirt open over a mustard tee, blue jeans, brown boots, bigger build |
| Colour | Burnt orange #C8642B | Teal #2F7F78 | Red flannel #8C3B2E / mustard #D6B04A |
| Typical line | "Wait, why is everyone wearing bedsheets?" | "Those are togas. And we have 24 hours." | "Great. I'm going to die in a bedsheet." |

This is the default standing pose: arms relaxed, no props.
Props and actions (holding, pointing, running) belong to scenes, never to the character itself.

Silhouettes are different on purpose (cowlick / ponytail / beanie + beard and wider build),
so each one is recognisable in a split second, even small on a phone.

Backup characters are added to this file when the first story needs them.
