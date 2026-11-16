---
name: nx-journal
description: Procedure for writing or changing an NX worker command or any NXOpen code under nx_worker/. Use whenever a task touches nx_worker/commands, nx_worker/nxutil, a journal, or an NXOpen call.
---

# Writing or changing a worker command

NX is not installed where Claude runs. You write the journal; a person runs it
on the NX seat. A call you guess wrong costs that person a round trip, so the
order below matters.

## 1. Find the evidence first

1. List `nx_worker/recorded/` and read every journal related to the command.
   These were recorded in the real NX release and always win.
2. Read HANDOFF.md section 13 for calls seen in published journals.
3. Read `docs/nx_api_assumptions.md` for what is already known to be unverified.

Write down, for each NXOpen call you need, which of the three sources backs it.

## 2. Write the code

- Put NXOpen code only in `nx_worker/commands/<name>.py` and `nx_worker/nxutil/`.
  A helper in `nxutil/` names the recorded journal it comes from in a comment.
- A call backed by a recording or by section 13 is used exactly as shown there:
  same arguments, same order, same enum names.
- Any other call gets the trailing comment `# UNVERIFIED-NXOPEN` on its line.
  Never present a guessed call as known.
- If the command cannot work without an unverified call, still write the rest,
  isolate the unverified part in one small function, and continue.
- Follow `.claude/rules/nx-worker.md`: Python 3.10, standard library only, no UI
  calls, never save a source part, `status.json` on every path.
- The command module exposes `run(inputs, options, log) -> dict` and returns a
  plain dict that conforms to the contract in `schemas/`.
- Register the command name in `nx_worker/main.py` if it is new.

## 3. Update docs/nx_api_assumptions.md

- Add every `# UNVERIFIED-NXOPEN` call to "Unverified calls in the code": the
  call, the file, why it is needed, and what recording would verify it.
- Add a numbered entry to "Recordings requested" that tells the person exactly
  what to do in the NX user interface while recording.
- Remove entries that a new recording has verified, and drop their tags.

## 4. Test what can be tested without NX

- Unit tests in `tests/unit/worker/` use a fake `NXOpen` module created in
  `tmp_path`, never one committed to the repository.
- Test the failure paths: the command must produce a useful `status.json`.
- Run `make check`. It includes the bare Python 3.10 run and the architecture tests.

## 5. Write the run instructions for the NX seat

Add a section to `nx_worker/README.md` with:

- a committed job file under `nx_worker/jobs/` with a relative `output_dir` under `runs/`;
- **one command** the person pastes, in the form
  `"%UGII_BASE_DIR%\NXBIN\run_journal.exe" "<repo>\nx_worker\main.py" -args "<repo>\nx_worker\jobs\<name>.json"`,
  or a `.bat` file that wraps it;
- which inputs to edit (part paths) and where;
- which files to send back or commit, and where they go (`fixtures/real/<name>/`);
- what a failure looks like and that `status.json` should be sent back as it is.

Then update `docs/progress.md` and stop for the `[HUMAN]` step.
