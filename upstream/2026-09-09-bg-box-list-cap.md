---
title: Chat page: the background-wait box shows about six rows when open and scrolls beyond
status: candidate
where: ui/webview/styles.css (the .bg-list cap), ui/webview/render.ts (the fold-and-cap note), ui/webview/bg-tasks-layout.test.ts
added: 2026-09-09
pr:
tier: fix
offered:
closed:
---
The open list of the chat page background-wait box (#bg-tasks) is capped at about six rows (.bg-list:not(:has(.bg-task.open)) max-height 180px) with its own scroll; the cap lifts while a row has its details open, and the box keeps its min(50vh, 340px) cap. Before: seven agents in flight fit under the 340px cap without scrolling, so the open box took half a phone screen and left about three lines of transcript. The fold needed no change: bgFoldOpen is a page-lifetime Set of session ids, closed by default and written only by the header click and the Awaiting chip; the tests pin that so nobody assumes the box opens on its own.
