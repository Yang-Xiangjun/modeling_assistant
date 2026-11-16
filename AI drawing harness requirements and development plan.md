# AI drawing harness: requirements and development plan

Nov 16, 2026 · @Lucas Levis

The MVP generates a native NX drawing for a PCBA from a sibling PCBA's model and drawing, with every dimension measured from geometry and verified. It needs one NX seat and about 13–18 weeks with 2–3 engineers; a second product pack follows in 3–4 more weeks.

## Scope

The system reads a reference model and its drawing, learns the drawing conventions, and applies them to a similar target model. An AI harness plans; deterministic code and NX measure, draw and verify.

|  | Content |
| --- | --- |
| In the MVP | One reference PCBA assembly and its drawing, both native NX. Three sibling PCBAs as targets. Output is a native NX drawing part, PDF, DXF and a review package. One sheet with top, bottom and side views. Dimensions for board outline, mounting holes, connector and pin-array location, and component heights. Title block filled from attributes. |
| Not in the MVP | Section and detail views, generated GD&T, parts list and balloons, references that exist only as PDF or DXF, Teamcenter-managed mode, a second CAD backend, 3D model generation. |
| After the MVP | Product packs for other actuator parts: housing and cover, gears, shafts, motor subassembly, connector, complete actuator outline. |

## Assumptions, all confirmed

All eight are confirmed in the status column. Two details stay open: whether each drawing is a separate part that references its model (the sheet reader reports this in P0), and which LLM provider and model P4 uses.

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

## Functional requirements

Eighteen requirements cover reading, planning, drawing, checking and extending. Each row reads "the system shall".

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

## Quality requirements

Ten requirements set how well the system must do its job. NFR-10 is a proposed target, to be confirmed after the first baseline.

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

## Rules that override everything

Six rules take priority over any requirement or task when they conflict.

1. Every measurement comes from the CAD model, never from an LLM or a reference drawing.
2. Tolerances, datums and GD&T are never copied from a reference without an authoritative source. Without one, they are flagged for human review.
3. The LLM only selects among IDs that deterministic code produced.
4. The harness and services never import a CAD API. Backends run as separate processes.
5. A failed check leaves the drawing unreleased and reported, never silently saved.
6. Core, harness and worker never name a product type. Product knowledge lives in packs.

## MVP acceptance criteria

The MVP is accepted when AC-1 to AC-6 pass on the golden set. AC-7 closes the extensibility work.

| ID | Criterion | Checked at |
| --- | --- | --- |
| AC-1 | At least 90% of reference dimensions are linked to a feature. The rest are listed with reasons. | G1 |
| AC-2 | The reference drawing regenerated from its own extracted plan has the same views and dimension set, with equal values. | G2 |
| AC-3 | For each sibling target, every generated dimension passes the value check and all coverage rules pass. | G3 |
| AC-4 | Every tolerance, datum or note without a source appears in the review package. | G3 |
| AC-5 | An unattended run reaches the review gate on every target in at most three repair rounds. | G4 |
| AC-6 | All service and harness tests pass in CI without NX. | Every gate |
| AC-7 | A second product pack runs end to end with no edits outside its own folder. | G5 |

Human edits needed to make each drawing release-ready are counted from G3 onward. The target is set after the first baseline.

## Development plan

Six phases run in a fixed order: contracts first, deterministic code before AI, round-trip before transfer. P0 to P4 take 13 to 18 weeks; P5 adds 3 to 4.

&#91;embedded content: roadmap · 6 phases, 6 gates\]

Each gate sits on the right edge of its phase. G4 closes the MVP; G5 freezes the contracts.

| Phase | Weeks | Builds | Exit gate |
| --- | --- | --- | --- |
| P0 Setup | 1 to 2 | Repository, contracts v0, synthetic fixtures, recorded journals, golden set of one reference and three siblings exported from NX | G0: a journal runs in batch on the reference files |
| P1 Read | 3 to 4 | Model reader, sheet reader, generic features, PCBA pack, dimension linking, mock backend | G1: AC-1 |
| P2 Round-trip | 3 to 4 | Convention profile, plan compiler, plan executor, exporter, provenance | G2: AC-2 |
| P3 Transfer | 3 to 4 | Matcher, candidate generator, rule-based planner, verifier | G3: AC-3 and AC-4 |
| P4 Harness | 3 to 4 | State graph, LLM planner for unresolved cases, repair loop, review gate | G4: AC-5 |
| P5 Generalise | 3 to 4 | Second pack for a housing, contracts frozen at v1 | G5: AC-7 |

What each gate decides:

- G0: start P1 once a journal has run in batch on the real reference files.
- G1: below 90%, fix the sheet reader or the template's view type before going on.
- G2: on failure, revise the plan schema instead of adding executor workarounds.
- G3: the share of unmatched features sets how much LLM planning P4 needs.
- G5: contracts freeze at v1, and later packs must fit them.

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

The handoff file gives Claude Code the task list for each phase and marks every step that needs a person.

## Risks

Six risks can distort the plan. Licensing is no longer one of them, and the LLM decision adds one. Dimension read-back is checked in P0.

| Risk | Effect | Mitigation |
| --- | --- | --- |
| An external LLM is ruled out later | The planner must move to a locally deployed model | Keep the provider behind one adapter chosen by configuration. Rules-only mode needs no LLM. |
| Dimension read-back differs by drawing view type | AC-1 is missed | Test the sheet reader on the real reference drawing in P0. |
| Fingerprints fail to find the same geometry again | Dimensions are created unattached | Reader and executor share one fingerprint module. Unresolved entities are reported, never guessed. |
| Large assemblies are slow in drafting | Run time exceeds NFR-10 | Filter vias at import or by role. Fix one view representation in the template. |
| NXOpen calls are guessed wrongly | Journals fail on the seat | Use only calls taken from recorded journals. Tag and list every unverified call. |
| Too few golden examples | Rules fit one board only | Add sibling boards before P3. The second pack in P5 tests generality. |
