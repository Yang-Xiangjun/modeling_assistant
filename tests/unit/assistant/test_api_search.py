from pathlib import Path

from drawgen.assistant.api_search import ApiCatalog, expand_synonyms, validate_candidate


def _catalog(tmp_path: Path) -> ApiCatalog:
    index = tmp_path / "index.tsv"
    index.write_text(
        "guid\tkind\tfull_name\tsummary\tasset_id\n"
        "g1\tmethod\tNXOpen.MeasureManager.NewMassProperties\t"
        "Creates a mass properties measurement object from bodies.\t"
        "M:NXOpen.MeasureManager.NewMassProperties\n"
        "g2\tproperty\tNXOpen.MeasureBodies.Volume\tReturns the volume.\t"
        "P:NXOpen.MeasureBodies.Volume\n"
        "g3\tmethod\tNXOpen.MeasureFaces.CreateFeature\t"
        "Creates a face area measurement.\tM:NXOpen.MeasureFaces.CreateFeature\n",
        encoding="utf-8",
    )
    return ApiCatalog(index)


def test_synonyms_expand_volume_terms() -> None:
    terms = expand_synonyms("volume")
    assert "mass properties" in terms
    assert "solid volume" in terms


def test_catalog_search_returns_volume_candidates_in_rank_order(tmp_path: Path) -> None:
    candidates = _catalog(tmp_path).search("volume", limit=3)

    names = [candidate.full_name for candidate in candidates]
    assert "NXOpen.MeasureBodies.Volume" in names
    assert "NXOpen.MeasureManager.NewMassProperties" in names
    assert candidates[0].source is not None


def test_catalog_search_supports_kind_and_namespace_filters(tmp_path: Path) -> None:
    candidates = _catalog(tmp_path).search(
        "volume", kind="property", namespace="NXOpen.MeasureBodies"
    )

    assert [candidate.full_name for candidate in candidates] == ["NXOpen.MeasureBodies.Volume"]


def test_validate_candidate_records_evidence_status(tmp_path: Path) -> None:
    candidate = _catalog(tmp_path).search(
        "volume", kind="property", namespace="NXOpen.MeasureBodies"
    )[0]

    validated = validate_candidate(candidate, required_terms=("volume",), nx_version="2506")
    rejected = validate_candidate(candidate, required_terms=("missing_api",))

    assert validated.status == "validated"
    assert validated.nx_version == "2506"
    assert rejected.status == "rejected"
