# 012 Worker skeleton and backends

Status: decided 2026-11-16 (P0-T5).

- **`ping` and the NX version.** `ping` calls only `NXOpen.Session.GetSession()`
  (HANDOFF.md section 13). The NX version comes from the `UGII_VERSION`
  environment variable and is null when unset. If the seat does not set it,
  P0-H1 must supply a recorded call for the version.
- **Finding `run_journal`.** Argument, then `DRAWGEN_NX_RUN_JOURNAL`, then
  `%UGII_BASE_DIR%\NXBIN\run_journal.exe`.
- **Timeout.** 600 s per command by default. On timeout the backend kills
  `run_journal` only. An NX process it started may survive. Known limit; handle
  it in P2 when long commands exist.
- **Exit codes.** A job run never calls `sys.exit`, because its effect inside the
  journal runner is unverified. `status.json` is the only result channel.
- **Relative `output_dir`** in `job.json` resolves against the job file's folder.
  The committed ping job writes to `runs/ping/`, which git ignores. The person
  on the seat copies `status.json` from there to commit it.
- **Commands not implemented yet** write a failing `status.json` naming the task
  that adds them.
- **`MockBackend`** serves fixtures only. Simulated execution comes in P2-T5.
