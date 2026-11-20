# Requirements

Authoritative sources in the repository (read the cited sections only):

- HANDOFF.md section 17 (17.1 parts, 17.2 bridge protocol, 17.3 live contracts, 17.4 tools, 17.5 agent turn / number checker / log, 17.6 change path, 17.7 panel)
- HANDOFF.md section 4.5 (assumptions A9-A13, unconfirmed)
- HANDOFF.md section 4, requirement rows FR-19 to FR-29 and AC-8 to AC-13
- CLAUDE.md "Rules that override everything", especially rules 4, 7 and 8
- docs/branch-c-implementation-plan.md (MVP priorities: plan-first, API discovery, typed pipeline composition, replanning)
- docs/decisions/014-branch-c-interface-and-harness.md (C# bridge, harness portability)

Owner clarification in this session: "flexibility" means pi plans the operation, looks up NXOpen APIs, and forms an NXOpen C# pipeline for what the user asked. This goal is in tension with rule 7 as written; reviewers should treat rule 7 as binding for defects in existing code and analyse the goal as a design question.
