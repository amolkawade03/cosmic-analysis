# Source Key Points

This document distills the themes from the source talk that seeded this
project (a long-form Sadhguru discourse on time, calendar, equinox, and
Panchangam, from the *360* program). The full transcript is held locally
only (see `PROJECT_ORIGIN.md` and `.gitignore`); this file is the public,
fair-use reference that the model and documentation should track against.

Each section below pairs a brief attributed quote with a paraphrase of the
idea and a timestamp link to the original on YouTube
(<https://www.youtube.com/watch?v=vkow6IyuaVo>). Use these as the philosophical
acceptance criteria for the engine and docs.

---

## 1. Time is the field, not a counter

> "Time is that which holds the entire universe together. Even gravity is one
> byproduct of time."  — [00:00:17](https://www.youtube.com/watch?v=vkow6IyuaVo&t=17)

Time / Kala is treated as the substrate of physical creation, not a
measurement device. The talk explicitly contrasts this against the modern,
economic view of time as scheduling.

**Implication for the model:** the engine should not present its output as a
schedule of "good vs. bad slots." Time windows are observations of cosmic
geometry, not verdicts.

---

## 2. The Gregorian calendar is a marketplace tool

> "It is a numerical convenience that ignores the larger geometry of the
> cosmos entirely."  — [08:00](https://www.youtube.com/watch?v=vkow6IyuaVo&t=480)

The talk traces the Gregorian system back to Roman tax collection ("calendae")
and frames it as deliberately decoupled from celestial geometry — useful for
accounting, inadequate for human experience.

**Implication for the model:** anywhere the engine falls back to Gregorian
month/day boundaries (e.g., the current `ritu_and_ayana` in `cosmic_engine.py`)
contradicts the source premise. Sidereal Sankranti boundaries should drive
ritu and ayana, not 12/22 and 6/21.

---

## 3. Microcosm / macrocosm — pinda and brahmanda

> "The human system is a microcosm of the larger cosmos."
> — [09:56](https://www.youtube.com/watch?v=vkow6IyuaVo&t=596)

The yogic claim used throughout the talk: the body, the planet, and the
cosmos share the same geometry. The 108 / Sun-diameter / Earth-Moon-distance
correspondences are offered as illustration, not proof.

**Implication for the model:** the user is not separate from the calendar.
The dashboard should accept the user's inner state as input, not just date,
location, and activity.

---

## 4. The Panchangam is a five-limbed cosmic-geometry map

> "Panchang means five limbed calendar."
> — [17:31](https://www.youtube.com/watch?v=vkow6IyuaVo&t=1051)

The five limbs the talk names:

1. **Tithi** — the lunar day
2. **Vara** — the weekday tied to a celestial body
3. **Nakshatra** — the Moon's position in 27 lunar mansions
4. **Yoga** — combined Sun + Moon longitude
5. **Karana** — half of a tithi, used for "specific auspicious timings ...
   to empower ourselves to the best possible action"
   ([18:13](https://www.youtube.com/watch?v=vkow6IyuaVo&t=1093))

**Implication for the model:** all five limbs must materially influence the
muhurta score. Computing and displaying them is not enough — currently
Tithi-class, Yoga, and Karana are display-only fields. See `COUNCIL_REVIEW.md`.

---

## 5. The precession is real and the Hindu calendar accounts for it

> "That was the equinox many years ago. They say around 5th century CE but
> today it is about 24 days off."
> — [22:40](https://www.youtube.com/watch?v=vkow6IyuaVo&t=1360)

The talk specifically calls out axial precession and the ~24-day drift of the
Aries equinox as the reason a sidereal frame matters.

**Implication for the model:** the choice of ayanamsha (Lahiri / Raman /
Krishnamurti) is not a minor preference — it is the project's commitment to
sidereal cosmic geometry over tropical convenience. Mixing tropical Gregorian
boundaries with sidereal longitudes inside the same engine breaks this
commitment.

---

## 6. Anti-fatalism — Rahu Kala is not a verdict

> "It is not about blaming the stars or the planet for everything that you do
> or you do not do ... It is about enhancing your ability to respond to
> everything that's happening in this cosmos."
> — [14:38](https://www.youtube.com/watch?v=vkow6IyuaVo&t=878)

The talk explicitly criticizes people who refuse to act during Rahu Kala. The
posture taught is *respond, not react* — awareness, not avoidance.

**Implication for the model:** the current scoring's `Avoid` band label and
−20 / −12 penalties for Rahu Kala / Yamaganda / Ashtama Chandra contradict
this directly. Bands should communicate "lower support / higher friction,"
not prohibition.

---

## 7. Equinox / solstice / Sandhya are transition windows

> "One simple thing to take care of during the equinoxes is to keep your hair
> wet especially during the [sandhyas] or the four times in a day when there's
> a transitionary period — morning, afternoon, evening and midnight."
> — [33:13](https://www.youtube.com/watch?v=vkow6IyuaVo&t=1993)

The four daily sandhi points and the equinox/solstice axis are presented as
the calendar's high-leverage moments — when ions, magnetic envelope, and
solar intensity transition.

**Implication for the model:** Sandhya windows and Brahma Muhurta are
already first-class in the engine; the equinox / solstice axis is not.
A first-class "this week is approaching equinox / solstice" surface in
`daily_alignment_text` would honor the source.

---

## 8. Uttarayana = harvest. Dakshinayana = sadhana.

> "In the yogic tradition, uttarayana is seen as a time of harvest. ...
> Dakshinayana is considered a time to work upon yourself."
> — [38:04](https://www.youtube.com/watch?v=vkow6IyuaVo&t=2284)

The two halves of the year carry different yogic functions: outward growth
vs. inward purification. The talk also flags that this is northern-hemisphere
framing.

**Implication for the model:** ayana should be sidereal (Makara Sankranti
~ Jan 14, Karka Sankranti ~ Jul 14) and should reverse for southern-hemisphere
locations — neither is currently true in `cosmic_engine.py:ritu_and_ayana`.

---

## 9. Festivals are calendar-driven, not belief-driven

> "All Indian festivals are calendar oriented not belief oriented based on
> how the sun, moon and earth are aligned."
> — [35:21](https://www.youtube.com/watch?v=vkow6IyuaVo&t=2121)

Margali / Pongal, Ugadi, Chaitra Pournami, Karkidakam — all named in the talk
as examples of practices timed to specific solar / lunar geometries.

**Implication for the model:** a festival / vrata layer (Ekadashi, Pradosha,
Sankranti, Pournami / Amavasya, equinox, solstice) is missing from the
current build. This is one of the larger documentation-vs-code gaps and
should land on the roadmap.

---

## 10. The terminal node is consciousness, not the calendar

> "The stars and the planets need not decide your experience of life. You and
> you alone should be the one to decide your inner experience."
> — [41:41](https://www.youtube.com/watch?v=vkow6IyuaVo&t=2501)

> "Until you transcend the cycles of time and space, you must learn to ride
> the cycles. To ride the cycles, you need the right kind of calendar."
> — [43:51](https://www.youtube.com/watch?v=vkow6IyuaVo&t=2631)

The talk closes by relativizing the entire calendar: it is a vehicle for
those who have not yet achieved inner liberation. The dashboard is therefore
an aid for *responsiveness*, expressly subordinate to inner work.

**Implication for the model:** `daily_alignment_text` should walk the chain
*Kala → geometry → environment → body/mind → action → awareness* — currently
it stops at "action" with a static template.

---

## How to use this document

When writing or reviewing code, docs, or scoring rules in this project,
check the change against the ten points above. If a feature would deepen
alignment with one of them, it belongs on the roadmap. If a feature
contradicts one of them (e.g., Gregorian-date ritu, fatalistic banding),
the feature is the bug — not the source.

`COUNCIL_REVIEW.md` enumerates the current gaps against this bar.
