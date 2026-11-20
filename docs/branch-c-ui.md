# Branch C chat assistant UI

The MVP UI is a local browser page that connects the chat box to the existing Branch C assistant CLI. The launcher starts NX, starts the UI server, opens the assistant page, and tiles the native windows on the primary display.

## Start

From the repository root in PowerShell:

```powershell
.\tools\start_branch_c_manual_test.ps1
```

This command builds the NX2506 bridge, starts NX and the browser assistant,
and enables the deterministic smoke part. After NX opens, load the journal
shown in the PowerShell window through **Tools > Journal > Play**. The browser
health card becomes ready when the journal has started.

The lower-level UI launcher remains available when the bridge has already been
built or when a custom backend is needed.

Use the mock backend while validating the UI wiring:

```powershell
.\tools\start_branch_c_ui.ps1 -Backend mock
```

The lower-level launcher creates the smoke fixture by default. Pass
`-NoFixture` when an already-open NX part should be used.

Use the NX bridge after the interactive NX journal has created `%LOCALAPPDATA%\drawgen\bridge.json`:

```powershell
.\tools\start_branch_c_ui.ps1 -Backend bridge
```

Pi must be installed and authenticated for the chat box:

```powershell
npm install -g @mariozechner/pi-coding-agent
pi
```

Inside Pi, run `/login` and choose the ChatGPT Plus/Pro Codex provider. The launcher passes `--print --mode json` to the existing Branch C Pi adapter.

The browser route passes `--yes` for the explicit local chat request so change
tools can run without a terminal prompt. Direct CLI use keeps its confirmation
prompt unless `--yes` is supplied.

The Pi harness loads `.pi-agent/skills/nxopen-cad/SKILL.md` for every chat turn.
That skill maps selection and measurement requests to the typed NXOpen bridge.
For example, a request for the total surface area of a selected Block reads the
selection and measures the summed live face areas returned by NX.

The current geometry MVP command is `create_box_with_hole`. For example, send
`Create a 100 x 60 x 20 box with a 10 mm through-hole`. NX opens a new active
part, creates the requested through-hole on the main NX thread, and leaves the
part unsaved so the existing `save` tool remains explicit.

## Files

- `web/branch_c_chat.html` contains the split assistant interface.
- `tools/branch_c_ui_server.py` serves the page and forwards chat requests to `drawgen assistant chat`.
- `tools/start_branch_c_ui.ps1` starts NX and the UI, then tiles both windows.
