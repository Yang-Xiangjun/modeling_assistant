from drawgen.contracts.live import LiveMeasureRequest, LiveMeasureResult, LiveMeasureResults


def test_volume_measure_contract_accepts_mm3() -> None:
    request = LiveMeasureRequest(id="m0", kind="volume", a="tag:42")
    results = LiveMeasureResults(
        results=[LiveMeasureResult(id=request.id, value=123.0, unit="mm3")]
    )

    assert request.kind == "volume"
    assert results.results[0].value == 123.0
    assert results.results[0].unit == "mm3"
