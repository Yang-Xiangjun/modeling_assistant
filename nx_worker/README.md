# NX worker

`main.py` is launched by NX's batch journal runner. It reads one `job.json`,
dispatches the command lazily, and writes an atomic `status.json` for every
job. Successful commands also write `result.json`; failed commands leave that
file absent. A relative `output_dir` is resolved from the directory containing
the job file.

From an NX seat, set `DRAWGEN_NX_RUN_JOURNAL` when the runner is not under
`UGII_BASE_DIR`, then run:

```bat
nx_worker\run_ping.bat
```

The ping job is `nx_worker/jobs/ping.json` and its status lands at
`runs/ping/status.json` (the path is relative to the job file).

For a plain Python smoke test without NX:

```text
python nx_worker/main.py --selftest
```
