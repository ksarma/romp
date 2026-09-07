# Latency report

## Findings

The api session cut p95 latency by 40% after enabling the response cache.
Cold starts remain slow on the first request of the day.

## Recommendation

We recommend shipping the cache in v1.2.

## Checks

- retry on timeout
- retry on timeout
- retry on timeout
- retry on timeout

## Day 1

The tests pass on every supported platform. Ship it.
No regressions were seen in the nightly run.

## Day 2

The tests pass on every supported platform. Ship it.
No regressions were seen in the nightly run.
