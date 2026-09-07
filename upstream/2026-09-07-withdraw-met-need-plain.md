---
title: withdraw_user_todo answers a met need plainly: POST /usertodo/withdraw adds `state` / `at` / `owner` to its ok:false answer, and the postal tool flags an error only for an id that is unknown or another session's (a note the person answered or dismissed, or one the session already withdrew, gets a plain answer with the time and no error flag)
status: waiting
where: fork branch `withdrawcalm` (kernel/kernel.py `_withdraw_user_todo` and the `/usertodo/withdraw` route; postal/postal_service.py the `withdraw_user_todo` branch of `_mcp_call` and `_when_words`; tests/test_user_todos.py WithdrawAccount, tests/test_postal_user_todos.py Account and WhenWords, tests/test_injected_voice.py; docs/reference.md, plans/user-todos.md)
added: 2026-09-07
pr:
tier: fix
offered:
closed:
---
A fix inside the user-todos feature, which upstream does not ship yet: the user-todos RFC (2026-08-22-user-todos-slice-1, approved as an RFC) is in flight, so this waits on it and travels with the slices or lands after them. Two sessions read the tool's one-size ok:false error as a failure and folded a met need into an error path; the kernel's answer now says which kind of nothing-to-do it was, and the tool flags an error only when the id is not the asker's or unknown. Contracts kept: `ok` still means this call stamped the row, the 409 while the switch is off is unchanged, and a remote kernel that predates the fields answers `ok` alone.
