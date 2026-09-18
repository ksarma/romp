---
title: GET /perf says what the feed frame is made of and what each pane would receive if sent only what it reads
status: candidate
where: kernel/kernel.py (_FeedComposition, FEED_APP_FIELDS, FEED_PROJECTIONS, _feed_parts), docs/reference.md, tests/test_feed_composition.py
added: 2026-09-18
pr: 785
tier: feature
offered:
closed:
---
The feed frame (about 8.8 MB on a busy board) goes whole to the feed pane, the Outline and the Waiting-on-you pane, and nothing said what it was made of. memos.feedComposition now carries, per per-entry pass, the bytes by component (cards, ledgers, the remainder per field) as lifetime sums and the last pass, and per consuming app the bytes it receives today beside what it would receive if sent only the fields its bundle reads (a checked-in table pinned against the webview source). The remainder is encoded per field and joined into the same sort_keys string, byte for byte; no second encode, no frame change. Beside the readers' rows, a phoneFace projection row sizes a frame that does not exist yet, a phone client's feed slot carrying a face per active card (address, title, state, age) plus one summary row per session with a card, so the gap to the phone's cold-open goal is measured before the face frame is designed.
