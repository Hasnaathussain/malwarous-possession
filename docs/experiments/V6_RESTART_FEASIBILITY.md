# Restart fusion qualification

Decision: **not validated; no fusion candidate shipped or target tag payload read**.

The official [Smart Tagging loader](https://github.com/metrica-sports/more-than-a-hack-2027/blob/f8f2629ff1e0985f81d7e59d8413678514ee1530/starter/load_smart_tagging.py) specifies video-relative seconds converted to frames by rounding at25fps. Its restart tags are approximate windows around a restart, about5seconds wide with roughly1second timing accuracy. They are not an exact stoppage duration or a guarantee that the end is the restart instant. Therefore this audit does not fill those windows with D or hard-seed their endpoint as a team possession.

The [external dataset paper](https://www.nature.com/articles/s41597-025-04505-y) describes manual event annotation, timestamped events and set-piece event categories. This permits external supervision but does not by itself certify that a proposed event feature is independent of the BallStatus/BallPossession scoring fields or semantically comparable to automatic Smart Tagging. A source event list is not a validated noisy tag channel. No event-derived dense feature, target consistency score or fusion weights were constructed in this campaign.

Under the committed V6 protocol, incomplete annotation-independence, restart timing and cross-channel semantic evidence fails the qualification gate. No fusion was scored or promoted. The official FAQ already permits algorithmic Smart Tagging use; this is a validation limitation, not a claim it is banned. No organizer issue was necessary to ask whether an explicitly permitted asset is permitted.

P2/P3 new heads/label definitions and P4 camera alignment were not executed in this bounded final campaign. They require separate externally justified registrations, implementation and full comparative fits; they were not silently inferred from target public-window diagnostics. ExistingV3/V4/V5 failed gates remain rejected. These choices preserve the frozen verified candidate rather than shipping unvalidated changes.
