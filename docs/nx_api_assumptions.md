# NXOpen API assumptions

Every NXOpen call in `nx_worker/` that is not backed by a journal in
`nx_worker/recorded/` or by HANDOFF.md section 13 is listed here, tagged
`# UNVERIFIED-NXOPEN` in the code, with the recording that would verify it.

## Unverified calls in the code

| Call | Evidence | Confirmation |
|---|---|---|
| `NXOpen.Session.GetSession()` in `nx_worker/commands/ping.py` | HANDOFF.md section 13 | Backed by the published-journal list, not by a recording yet. |

## Runtime assumptions about `run_journal`

The following runtime behaviours are assumptions to confirm in P0-H2:

| Assumption | Confirmation task |
|---|---|
| `__file__` is set in the journal process. | P0-H2 |
| Arguments after `-args` arrive in `sys.argv[1:]` (HANDOFF.md section 13). | P0-H2 |
| `__name__` is `"__main__"`. | P0-H2 |
| The effect of `SystemExit` is safe in the journal runner. | P0-H2 |
| `UGII_VERSION` and `UGII_BASE_DIR` are set on the seat. | P0-H2 |

## Recordings requested

From P0-H1 (HANDOFF.md section 14):

1. Open a part.
2. List sheets and views.
3. Read one dimension and its attached objects.
4. Create a base view and a projected view.
5. Create one linear dimension between two edges and one diameter dimension on a hole.
6. Fill a title-block attribute.
7. Export a sheet to PDF and to DXF.
