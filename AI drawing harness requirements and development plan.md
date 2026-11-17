# AI drawing harness: requirements and development plan

Nov 16, 2026 · @Lucas Levis

The MVP now has two parts. Drawing generation produces a native NX drawing for a PCBA from a sibling PCBA's model and drawing, with every dimension measured from geometry and verified. A chat assistant docked beside NX answers questions about the live session and runs a fixed set of basic operations. P0 is built. The remaining drawing phases are estimated at 12 to 16 weeks, and the assistant adds 8 to 12 weeks of one engineer's time in parallel.

## Scope

The system reads a reference model and its drawing, learns the drawing conventions, and applies them to a similar target model. An AI harness plans; deterministic code and NX measure, draw and verify. The chat assistant works on the user's open NX session through a fixed list of tools.

|  | Content |
| --- | --- |
| In the MVP | One reference PCBA assembly and its drawing, both native NX. Three sibling PCBAs as targets. Output is a native NX drawing part, PDF, DXF and a review package. One sheet with top, bottom and side views. Dimensions for board outline, mounting holes, connector and pin-array location, and component heights. Title block filled from attributes. A chat assistant in a window docked beside NX: it reads the session and the current selection, answers inspection questions, and runs the model and drawing operations listed in FR-23 and FR-24. |
| Not in the MVP | Section and detail views, generated GD&T, parts list and balloons, references that exist only as PDF or DXF, Teamcenter-managed mode, a second CAD backend, 3D model generation. For the assistant: creating or editing geometry by chat, a panel inside the NX window, screenshot or voice input, more than one user per session. |
| After the MVP | Product packs for other actuator parts: housing and cover, gears, shafts, motor subassembly, connector, complete actuator outline. For the assistant: geometry tools and a panel inside NX. |

How a chat message reaches NX:

1. The chat panel sends the message to the assistant agent.
2. The agent picks a tool from the fixed list. It never writes NXOpen code.
3. The tool layer checks the arguments and, for a change, asks the user to confirm.
4. The live backend sends a JSON request to the bridge over the local loopback address.
5. The bridge add-in runs inside the user's NX session, executes the request on NX's main thread and returns JSON. For a selection it reads the selected objects themselves, so nothing is guessed from a description.

The batch worker built in P0 cannot do step 5: it starts its own NX process and never sees the user's session. The bridge is the one new component.

## Assumptions: A1 to A8 confirmed, A9 to A13 open

A1 to A8 are confirmed in the status column. A9 to A13 come with the chat assistant and need your answer in the same column; A9 to A11 decide how C0 is built. Two details stay open: whether each drawing is a separate part that references its model (the sheet reader reports this in P0), and which LLM provider and model P4 uses.

| ID | Assumption | If it is false | status confirm |
| --- | --- | --- | --- |
| A1 | One Windows NX seat with the Drafting license is available to the team. | Nothing in P1 to P4 can be validated. | I have license for all needed functions. |
| A2 | Siemens confirms which author license Python journals need. A Siemens employee [states on the community forum](https://community.sw.siemens.com/s/question/0D5Vb000004usczKAA/what-is-exactly-the-difference-between-nx-open-net-author-and-nx-open-toolkits-author) that NX30115 or NX30106 is legally required. | Budget and start date move. | Same as above. |
| A3 | The reference PCBA and its drawing are native NX files in master-model form: a drawing part that references the model part. | A vector-drawing parser is needed first, estimated at 4 to 6 weeks. | All the 3d models and drawings can be provided as native NX part files. |
| A4 | Two or three sibling PCBAs are available as targets. | Transfer quality cannot be measured. | I can gather 3 sibling PCBAs. |
| A5 | The MVP runs in native mode, not Teamcenter-managed mode. | A Teamcenter license and managed open and save handling are added. | Teamcenter is not included in MVP stage. |
| A6 | Feature summaries in JSON, without geometry files, may be sent to the chosen LLM provider. | Use an on-premise model, or run in rules-only mode. | Allow for MVP stage. If it is necessary, we will use locally deployed LLM. |
| A7 | Claude Code runs on a machine without NX. | Tasks marked for the NX seat can be automated further. | Yes, may be I can run claude code on a NX in the future, but not now. |
| A8 | The team is 2 to 3 engineers, one with NX drafting experience. | Phase durations scale. | Yes. |
| A9 | "Same screen" means a chat window docked beside the NX window on one monitor, not a panel inside the NX window. | A panel inside NX needs user-interface integration that has not been investigated. A spike is added before C1. |  |
| A10 | "Basic operations" means the lists in FR-23 and FR-24. Creating or editing geometry by chat is not in the MVP. | Each geometry command is one more tool with its own recorded journal and tests, and C2 grows. |  |
| A11 | The live bridge may be a compiled .NET add-in loaded into NX and built on the NX seat. | A Python journal runs on NX's main thread and blocks the interface while it runs, so the bridge approach has to be rethought in C0. |  |
| A12 | Tool results sent to the external LLM may include part names, attribute text and measured values. | The assistant needs the locally deployed model from C1. |  |
| A13 | The assistant runs on the same Windows machine as NX, for one user at a time. | Remote use needs authentication and a network transport. |  |

## Functional requirements

FR-01 to FR-18 cover drawing generation: reading, planning, drawing, checking and extending. FR-19 to FR-29, in the second table, cover the chat assistant. Each row reads "the system shall".

| ID | Requirement | Phase |
| --- | --- | --- |
| FR-01 | Accept a job naming a target model, a reference model and a reference drawing, and record it in a run manifest. | P1 |
| FR-02 | Extract raw geometry and assembly structure from an NX part into JSON without modifying the part. | P1 |
| FR-03 | Extract sheets, views, dimensions, notes, tables and title block from an NX drawing, including the geometry each dimension is attached to. | P1 |
| FR-04 | Build a feature graph with generic features, part class, part frame and geometric fingerprints. | P1 |
| FR-05 | Assign product roles to features through a product pack. The PCBA pack is the first. | P1 |
| FR-06 | Link each reference dimension to features, and list unlinked dimensions with a reason. | P1 |
| FR-07 | Derive a convention profile from the reference: template, views, datum origin, dimension rules per role, notes. | P2 |
| FR-08 | Compile a drawing plan into an execution job and create a native, associative NX drawing in a separate drawing part. | P2 |
| FR-09 | Match target features to reference features, recording method and confidence. | P3 |
| FR-10 | Generate dimension and view candidates by rule, each with an expected value computed from the model. | P3 |
| FR-11 | Produce a drawing plan that selects candidates by ID. Rules decide first; the LLM handles unmatched or ambiguous cases. | P3 rules, P4 LLM |
| FR-12 | Verify every generated drawing against the rule set and emit findings with suggested edits. | P3 |
| FR-13 | Repair by applying edits from a closed set, for at most three rounds, then escalate. | P4 |
| FR-14 | Stop at a review gate with a package: drawing, findings, unresolved items and provenance. | P4 |
| FR-15 | Export native NX, PDF and DXF. | P2 |
| FR-16 | Record a source for every annotation: measured, PMI, requirements document, reference convention or unresolved. | P2 |
| FR-17 | Load product packs through a registry, so a new pack needs no change to core, harness or worker. | P1 interface, P5 proof |
| FR-18 | Run the whole pipeline on recorded fixtures with a mock backend. | P1 |

| ID | Assistant requirement | Phase |
| --- | --- | --- |
| FR-19 | Run a bridge inside the user's interactive NX session that serves requests from a local process, with every NXOpen call on NX's main thread and NX staying usable. | C0 |
| FR-20 | Report the session context: work part, displayed part, application, active sheet and view. | C1 |
| FR-21 | Report the current selection. For each selected object give its type, owning component, fingerprint and measured properties, read from the selected object itself. | C0, C1 |
| FR-22 | Provide inspection tools: area, length, radius, diameter, distance and angle; attributes, expressions, features, components, sheets, views and dimensions; and the feature and role of a selected entity from the feature graph. | C1 |
| FR-23 | Provide model operation tools: open and switch parts, orient and fit the view, show, hide and isolate, highlight an entity, edit an attribute, edit an expression value and update. | C2 |
| FR-24 | Provide drawing operation tools: create a sheet from a template, add base and projected views, add a dimension on the selected entities, add a note, update views, export PDF and DXF. | C2 |
| FR-25 | Show a chat panel docked beside the NX window on the same screen, with messages, tool calls, results and confirmation prompts. | C1 |
| FR-26 | Turn a user message into calls to tools from the fixed list, and ask the user to select or clarify when the target is missing or ambiguous. | C1 |
| FR-27 | For every tool that changes a part: show what it will do, wait for confirmation, set an undo mark, and save only when asked. | C2 |
| FR-28 | Start the drawing pipeline for the work part from chat and show the review package in the panel. | C3 |
| FR-29 | Log every message, tool call and result per session. | C1 |

## Quality requirements

NFR-01 to NFR-10 set how well drawing generation must do its job, and NFR-11 to NFR-16 do the same for the assistant. The times in NFR-11 are proposed targets. NFR-10 is a proposed target, to be confirmed after the first baseline.

| ID | Requirement | Measure |
| --- | --- | --- |
| NFR-01 | Accuracy | A drawing value equals the model measurement within 0.001 mm, or 0.01 degrees for angles. |
| NFR-02 | No model-generated numbers | No dimension value originates from an LLM. The plan schema has no numeric value field, and a test enforces it. |
| NFR-03 | License confinement | Only the NX worker needs a seat. All other tests run in CI without NX. |
| NFR-04 | Reproducibility | The same inputs and plan give the same drawing. Model, prompt and plan version are logged per run. |
| NFR-05 | Extensibility | A second product pack runs end to end with no edits to core, harness or worker. |
| NFR-06 | Backend portability | Harness and services call a backend interface. Contracts carry no NX identifiers except optional hints. |
| NFR-07 | Safety of source data | Source parts are never saved. Output goes to a new drawing part and an output folder. |
| NFR-08 | Data governance | CAD files stay local. Only feature JSON reaches the LLM. A rules-only mode exists, and the provider can be swapped for a locally deployed model by configuration. |
| NFR-09 | Traceability | Every annotation links to a feature, a rule and a run. |
| NFR-10 | Performance | One MVP PCBA runs end to end in under 15 minutes on the seat. |

| ID | Assistant requirement | Measure |
| --- | --- | --- |
| NFR-11 | Responsiveness | NX accepts mouse and keyboard input while the assistant waits for the LLM. A read tool returns within 2 seconds. |
| NFR-12 | No invented numbers | Every number in an answer appears in a tool result of the same turn. A checker enforces this before the answer is shown. |
| NFR-13 | Closed tool set | The LLM can call only listed tools with typed arguments. No model-written NXOpen code is executed. |
| NFR-14 | Reversibility | One Undo in NX reverts each changing tool call. |
| NFR-15 | Local-only bridge | The bridge listens on the loopback address only and requires a per-session token. |
| NFR-16 | Testable without NX | Assistant and tools pass in CI against a mock live backend with scripted selections. |

## Rules that override everything

Eight rules take priority over any requirement or task when they conflict. Rules 7 and 8 come with the assistant.

1. Every measurement comes from the CAD model, never from an LLM or a reference drawing.
2. Tolerances, datums and GD&T are never copied from a reference without an authoritative source. Without one, they are flagged for human review.
3. The LLM only selects among IDs that deterministic code produced.
4. The harness and services never import a CAD API. Backends run as separate processes.
5. A failed check leaves the drawing unreleased and reported, never silently saved.
6. Core, harness and worker never name a product type. Product knowledge lives in packs.
7. The assistant acts on NX only through listed tools. It never runs NXOpen code written by a model.
8. A tool that changes a part runs only after the user confirms, sets an undo mark first, and never saves on its own.

## MVP acceptance criteria

The drawing part of the MVP is accepted when AC-1 to AC-6 pass on the golden set, and the assistant when AC-8 to AC-12 pass. AC-7 closes the extensibility work and AC-13 joins the two parts. The set sizes and the 90% in AC-8 and AC-9 are proposed thresholds.

| ID | Criterion | Checked at |
| --- | --- | --- |
| AC-1 | At least 90% of reference dimensions are linked to a feature. The rest are listed with reasons. | G1 |
| AC-2 | The reference drawing regenerated from its own extracted plan has the same views and dimension set, with equal values. | G2 |
| AC-3 | For each sibling target, every generated dimension passes the value check and all coverage rules pass. | G3 |
| AC-4 | Every tolerance, datum or note without a source appears in the review package. | G3 |
| AC-5 | An unattended run reaches the review gate on every target in at most three repair rounds. | G4 |
| AC-6 | All service and harness tests pass in CI without NX. | Every gate |
| AC-7 | A second product pack runs end to end with no edits outside its own folder. | G5 |

| ID | Assistant criterion | Checked at |
| --- | --- | --- |
| AC-8 | With a face selected in NX, "what is the area of this surface?" returns the value NX's own measure command shows, for every face in a 20-item selection set. | GC0 for one face, GC1 for the set |
| AC-9 | On the inspection question set, at least 90% of answers are correct, and no answer contains a number that is not in a tool result. | GC1 |
| AC-10 | Each listed operation completes from chat after confirmation, and one Undo in NX reverts it. | GC2 |
| AC-11 | The chat panel and NX are both fully visible on one 1920 by 1080 display, and NX stays usable while the assistant is working. | GC1 |
| AC-12 | All assistant tests pass in CI without NX. | Every assistant gate |
| AC-13 | "Generate the drawing for this part" in chat reaches the review gate and shows the review package in the panel. | GC3 |

Human edits needed to make each drawing release-ready are counted from G3 onward. The target is set after the first baseline.

## Development plan

The work now runs on two tracks. Drawing generation keeps its fixed order, P0 to P5: contracts first, deterministic code before AI, round-trip before transfer. P0's code is built; G0 closes once `ping` has run on the NX seat. The assistant adds C0 to C3: a bridge spike first, then inspection, then operations, then the link to the drawing pipeline.

&#91;embedded content: roadmap · two tracks, 10 phases, 10 gates\]

Each gate sits on the right edge of its phase. G4 closes the drawing part of the MVP and GC2 the assistant part. C3 needs both, and G5 freezes the contracts.

| Phase | Weeks | Builds | Exit gate |
| --- | --- | --- | --- |
| P0 Setup (built) | 1 to 2 | Repository, contracts v0, synthetic fixtures, recorded journals, golden set of one reference and three siblings exported from NX | G0: a journal runs in batch on the reference files |
| P1 Read | 3 to 4 | Model reader, sheet reader, generic features, PCBA pack, dimension linking, mock backend | G1: AC-1 |
| P2 Round-trip | 3 to 4 | Convention profile, plan compiler, plan executor, exporter, provenance | G2: AC-2 |
| P3 Transfer | 3 to 4 | Matcher, candidate generator, rule-based planner, verifier | G3: AC-3 and AC-4 |
| P4 Harness | 3 to 4 | State graph, LLM planner for unresolved cases, repair loop, review gate | G4: AC-5 |
| P5 Generalise | 3 to 4 | Second pack for a housing, contracts frozen at v1 | G5: AC-7 |

The assistant track is estimated at 8 to 12 weeks of one engineer's time:

| Phase | Weeks | Builds | Needs | Exit gate |
| --- | --- | --- | --- | --- |
| C0 Bridge spike | 1 to 2 | An add-in loaded into interactive NX that returns the selection to a local process. A bare chat window docked beside NX. Two decisions: the bridge language, and whether live tools can call the worker's existing commands. | P0 | GC0: with one face selected, an outside process gets its area, equal to NX's measure, while NX stays usable |
| C1 Inspect | 3 to 4 | Live backend interface and its mock, context and selection tools, inspection tools, chat panel, assistant agent, number checker, session log | GC0. P1 for feature roles | GC1: AC-8, AC-9 and AC-11 |
| C2 Operate | 3 to 4 | Model and drawing operation tools with confirmation and undo | GC1. P2 for views and dimensions | GC2: AC-10 |
| C3 Connect | 1 to 2 | Drawing pipeline started from chat, review package shown in the panel | GC2 and G4 | GC3: AC-13 |

With three engineers the two tracks run in parallel and the drawing dates hold. With two, my estimate is that the drawing track finishes 4 to 6 weeks later. C0 can start now, beside P1.

What each gate decides:

- G0: start P1 once a journal has run in batch on the real reference files.
- G1: below 90%, fix the sheet reader or the template's view type before going on.
- G2: on failure, revise the plan schema instead of adding executor workarounds.
- G3: the share of unmatched features sets how much LLM planning P4 needs.
- G5: contracts freeze at v1, and later packs must fit them.

What each assistant gate decides:

- GC0: if no bridge keeps NX usable, stop the assistant track and revisit the approach before C1.
- GC1: wrong answers are sorted by cause (tool missing, wrong tool chosen, wrong object). That fixes the C2 tool list.
- GC2: the assistant part of the MVP is done. Geometry tools are considered only after this.
- GC3: the two parts work as one product.

After P5 come STEP and IDX targets, PDF or DXF references, section views, parts lists, GD&T, an OCCT cross-check and a second backend.

## Who does what

Claude Code writes and tests everything that runs without NX. People run NX, supply real data and sign off drawings. If Claude Code later runs on the NX machine, it can run the journals itself; recording journals and sign-off stay with people.

| Work | Claude Code | Engineer on the NX seat | Domain expert |
| --- | --- | --- | --- |
| Contracts, services, harness, tests | Writes and tests | Reviews |  |
| NX journals | Writes them from recorded journals | Records journals, runs them, commits the output as fixtures |  |
| Golden set |  | Exports the files | Chooses parts and defines the expected drawing |
| Role and dimension rules | Implements |  | Specifies and reviews |
| Generated drawings |  | Opens and checks them in NX | Signs off |
| Live bridge add-in | Writes the code and its mock | Builds it against the installed NX, loads it into NX, runs the checks |  |
| Assistant test sets | Builds the test runner | Runs the sets on the seat | Writes the questions, the operations and the expected answers |

The handoff file gives Claude Code the task list for each phase and marks every step that needs a person.

## Risks

Eleven risks can distort the plan; the last five come with the assistant. Licensing is no longer one of them, and the LLM decision adds one. Dimension read-back is checked in P0.

| Risk | Effect | Mitigation |
| --- | --- | --- |
| An external LLM is ruled out later | The planner must move to a locally deployed model | Keep the provider behind one adapter chosen by configuration. Rules-only mode needs no LLM. |
| Dimension read-back differs by drawing view type | AC-1 is missed | Test the sheet reader on the real reference drawing in P0. |
| Fingerprints fail to find the same geometry again | Dimensions are created unattached | Reader and executor share one fingerprint module. Unresolved entities are reported, never guessed. |
| Large assemblies are slow in drafting | Run time exceeds NFR-10 | Filter vias at import or by role. Fix one view representation in the template. |
| NXOpen calls are guessed wrongly | Journals fail on the seat | Use only calls taken from recorded journals. Tag and list every unverified call. |
| Too few golden examples | Rules fit one board only | Add sibling boards before P3. The second pack in P5 tests generality. |
| The bridge freezes NX or stalls behind an open dialog | The assistant is unusable. One open-source bridge reports a 91-second stall behind a dialog. | Requests run in short slices on NX's main thread, time out, and are never replayed automatically. C0 tests this first. |
| Live bridge and batch worker become two command sets in two languages | Each operation is written and tested twice | One JSON command contract for both. C0 decides whether live tools can call the existing Python commands. |
| The LLM picks the wrong tool or the wrong object | A wrong change to a part | Closed tool list, highlight before acting, confirmation, undo mark, no automatic save. |
| The list of basic operations keeps growing | C2 never closes | A10 fixes the list. A new tool needs a recorded journal and a test first. |
| A panel inside NX is expected, not a docked window | The panel is rebuilt inside NX, which has not been investigated | A9 asks now. C0 shows the docked window early. |

## Sources for the assistant track

These pages back the bridge design. None of the open-source projects was tested here.

- [NXOpen Python reference, Selection class](https://docs.plm.automation.siemens.com/data_services/resources/nx/12/nx_api/custom/en_US/nxopen_python_ref/NXOpen.Selection.html): methods that return the objects currently selected, with no license listed.
- [NX Journaling, journal reading preselected objects](https://nxjournaling.com/node/252): a support journal that loops over the selection through the session's selection manager.
- [Siemens community, threading](https://community.plm.automation.siemens.com/t5/NX-Programming-Customization-Forum/Threading/td-p/296586): Siemens staff state that the NXOpen toolkits are not thread-safe and calls must come from the main thread.
- [NX\_MCP on GitHub](https://github.com/dreamending/nx_mcp): an MIT-licensed bridge with a sidecar, a token-protected loopback channel and a C# add-in for interactive sessions, validated by its authors on NX 2206 only. Its Python journal bridge is batch-only.
- [nx-agent on GitHub](https://github.com/LT60/nx-agent): an in-process journal bridge whose author reports that an open dialog blocked it for 91 seconds.
- [NX Journaling, remoting](https://nxjournaling.com/content/bi-directional-data-flow-using-nx-open-external-program): NX ships a remoting sample that lets another program control a session; it needs the author license.
- [inteliScience, Design Copilot compared with MCP](https://inteliscience.net/nxopen-mcp-vs-design-copilot/): describes Siemens' Design Copilot as documentation help that does not drive the NX interface.
