# NXOpen API assumptions

Every NXOpen call in `nx_worker/` that is not backed by a journal in
`nx_worker/recorded/` or by HANDOFF.md section 13 is listed here, tagged
`# UNVERIFIED-NXOPEN` in the code, with the recording that would verify it.

## Unverified calls in the code

None. No NXOpen code exists yet.

## Recordings requested

From P0-H1 (HANDOFF.md section 14):

1. Open a part.
2. List sheets and views.
3. Read one dimension and its attached objects.
4. Create a base view and a projected view.
5. Create one linear dimension between two edges and one diameter dimension on a hole.
6. Fill a title-block attribute.
7. Export a sheet to PDF and to DXF.
