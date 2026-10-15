---
name: measure-latency
description: Measure how long the timsen crate takes per key or per run, and compare two versions. Use when a change touches restore speed, when checking the "few milliseconds per key" target of restore-while-typing, or before claiming any timing in docs/EXPERIMENTS.md.
---

# Measuring latency

Timing is a measurement like any other here: the rules in `AGENTS.md` ("Measuring") apply. Write
the prediction into `docs/EXPERIMENTS.md` first, freeze the input, and show the instrument can see
a change. Partly adapted from the ECC skills `latency-critical-systems`, `benchmark` and
`rust-testing` (MIT).

## What to report

- **Percentiles, not the mean.** p50, p95, p99 and the maximum per key. Typing feels slow on the
  worst keys, which a mean hides. Say how many keys the figures come from.
- **Each part on its own.** Opening the table, the first key after opening (pages of the table are
  read from disk on first use), and a key in a warm table are different numbers. Do not add them.
- **Both tables.** The large table has longer candidate lists on some syllables and more pages to
  touch; report it separately from the small one.
- **The machine and its load.** CPU model, whether other jobs ran (`uptime` load average), and that
  the build was `--release`. A number from a busy machine is a ceiling, not a typical value.

## How to measure

1. Build the input once and keep it: unmarked runs from the test sets, written by
   `python -m research.crosscheck TABLE TESTFILE RUNS EXPECTED`. Copy the runs file before a series;
   comparisons are only valid on the same file.
2. Replay typing, not whole runs: feed each run one syllable at a time, as an input method would, and
   time each call. Timing whole runs measures something else.
3. Time with `std::time::Instant` around the call in a release example under `crates/timsen/examples/`,
   collect every sample, sort, and read the percentiles. Criterion is fine for a single hot function,
   but it reports a mean with an interval, not the tail across real inputs.
4. Check the output is still right in the same run (compare with the `EXPECTED` file): a faster
   version that restores differently is a different model, not an optimization.
5. Before and after a change: same runs file, same table, same machine, run alternately at least
   twice. Report both and the difference; a difference smaller than the run-to-run spread is no
   difference.

## Guardrails

- Never claim "under N ms" from one run, a debug build, or a warm cache alone.
- Do not speed restore up by changing what it returns (fewer candidates, a narrower search) without
  measuring accuracy too; record both in the same entry.
- Keep private text out of timing inputs and outputs, as for any test set.
