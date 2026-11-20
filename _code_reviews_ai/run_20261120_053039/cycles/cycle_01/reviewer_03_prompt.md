# Reviewer 03 Prompt

Primary review objective (must follow):
{{REVIEW_QUERY}}

Audit checklist (must follow):
{{AUDIT_ITEMS}}

Project-level approved review rules (must follow):
{{PROJECT_RULES}}

Scope context (inputs + file-level signals):
{{SCOPE_CONTEXT}}

Scope rule: touched files are important, but not the only audit basis.
If git/diff context is missing, use user query + audit items + context notes to define scope.
Do not anchor to prior reviewer outputs or historical issue ids in this independent pass.
If you suspect a regression, provide fresh reproducible evidence; recurrence mapping is handled in consensus.
Classify findings into MUST_FIX, SHOULD_FIX_IMPORTANT, SHOULD_FIX_MINOR, or NEEDS_CONFIRMATION.
If no MUST_FIX and no SHOULD_FIX_IMPORTANT remain, output exact marker: NO_NEW_BLOCKING_ISSUES.
Write final report to reviewer_03.md.
