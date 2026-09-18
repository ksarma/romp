---
title: GET /perf keys carry no session id, term, host op or client text
status: candidate
where: kernel/kernel.py (_PerfStats.snapshot for bySession and parses.perSession, _perf_http_key, _PERF_HTTP_ROUTES, _PerfStats.connect_push, _PERF_IDENT); tests/test_perf_stats.py test_per_session_rows_are_served_by_rank_and_parsed_sessions_as_a_count, test_http_key_is_method_plus_normalized_path, test_http_keys_outside_the_route_table_fold_to_other, test_the_http_cap_clears_the_kernels_own_route_table, test_connect_push_keys_only_identifier_app_names_and_caps_them, ServedSnapshotIsPasteSafe
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
Keys are the leak vectors of the served snapshot: builds.chat.bySession named its sid in every row, parses.bySid keyed the cold-parse table by sid prefix, the http table keyed GET /glossary/<term> per term and every requester-typed path (a scanners probe, a home path, an attached hosts op) until its cap, and connectPush.byApp keyed a clients declared app name verbatim. The rows are served by rank in max order; parses.perSession is {sessions, max}; /glossary/* is a collapsed family; every http key outside the checked-in route register _PERF_HTTP_ROUTES (one tuple per do_* method, held equal to the dispatch source by a test) folds to other; an app name is a key only when it fits an identifier grammar and while under a cap. One invariant test walks a whole snapshot built from planted synthetic state (a fake home path, the placeholder sid, TESTHOST, a glossary term, an exception message, a scanner path, a client app string) and asserts no absolute path, no uuid or 32-hex token, no planted text and no key outside an identifier grammar except in the http table and the four function-name byte tables; it found 36 leaks on the tree before the fixes and the byApp one no review had named. Shape changes: rank replaces sid in bySession rows; perSession replaces bySid; HEAD /version and other non-routes count under other. First half: perf-served-paths-and-text.
