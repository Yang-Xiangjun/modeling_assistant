"""Read-only NXOpen API catalog search for Branch C planning."""

from __future__ import annotations

import csv
import hashlib
import os
import re
from collections.abc import Iterable
from pathlib import Path
from typing import get_args

from drawgen.contracts.operation_plan import ApiCandidate, CandidateKind

_DEFAULT_INDEX = Path(r"C:\Users\young\.agents\skills\nxopen-api\data\index.tsv")
_INDEX_CACHE: dict[Path, list[dict[str, str]]] = {}
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "current",
    "for",
    "from",
    "give",
    "is",
    "me",
    "of",
    "please",
    "selected",
    "tell",
    "the",
    "this",
    "that",
    "what",
    "with",
}
_SYNONYMS: dict[str, tuple[str, ...]] = {
    "volume": ("volume", "solid volume", "body volume", "mass properties", "centroid"),
    "mass": ("mass", "mass properties", "density", "weight"),
    "area": ("area", "surface area", "face properties", "measure faces"),
    "surface": ("surface", "face", "surface area", "face properties"),
    "length": ("length", "curve length", "edge length", "measure length"),
    "distance": ("distance", "minimum distance", "clearance", "measure distance"),
    "radius": ("radius", "circular radius", "measure radius"),
    "diameter": ("diameter", "circular diameter", "measure diameter"),
    "centroid": ("centroid", "center of gravity", "mass properties"),
    "bounding": ("bounding box", "bounding volume", "ask bounding box"),
    "box": ("block", "box", "block feature", "create block"),
    "hole": ("hole", "hole feature", "simple hole", "cylindrical cut"),
}


def _tokens(value: str) -> list[str]:
    """Tokenize prose and CamelCase API names for deterministic matching."""

    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return [token for token in re.findall(r"[a-z0-9]+", expanded.lower()) if len(token) > 1]


def expand_synonyms(query: str) -> list[str]:
    """Expand user terminology into stable API-search phrases."""

    terms: list[str] = []
    for token in _tokens(query):
        if token in _STOPWORDS:
            continue
        for synonym in _SYNONYMS.get(token, (token,)):
            if synonym not in terms:
                terms.append(synonym)
    if not terms and query.strip():
        terms.append(query.strip())
    return terms


class ApiCatalog:
    """Search the local NXOpen index without reading or executing NX code."""

    def __init__(self, index_path: Path | None = None) -> None:
        configured = os.environ.get("DRAWGEN_NX_API_INDEX")
        if index_path is not None:
            resolved_index = index_path
        elif configured:
            resolved_index = Path(configured)
        else:
            resolved_index = _DEFAULT_INDEX
        self.index_path = resolved_index.expanduser()
        self._rows: list[dict[str, str]] | None = None

    def _load(self) -> list[dict[str, str]]:
        if self._rows is not None:
            return self._rows
        cached = _INDEX_CACHE.get(self.index_path)
        if cached is not None:
            self._rows = cached
            return cached
        if not self.index_path.is_file():
            self._rows = []
            return self._rows
        with self.index_path.open("r", encoding="utf-8", newline="") as stream:
            self._rows = [
                row for row in csv.DictReader(stream, delimiter="\t") if row.get("full_name")
            ]
        _INDEX_CACHE[self.index_path] = self._rows
        return self._rows

    def search(
        self,
        query: str,
        *,
        kind: CandidateKind | None = None,
        namespace: str | None = None,
        limit: int = 8,
    ) -> list[ApiCandidate]:
        """Return best matching API candidates with source evidence."""

        if limit <= 0:
            return []
        phrases = expand_synonyms(query)
        query_tokens = set(_tokens(" ".join(phrases)))
        scored: list[tuple[float, dict[str, str]]] = []
        for row in self._load():
            full_name = row.get("full_name", "")
            row_kind = row.get("kind", "")
            if kind is not None and row_kind != kind:
                continue
            if namespace and not full_name.startswith(namespace + "."):
                continue
            haystack = " ".join(
                (full_name, row.get("summary", ""), row.get("asset_id", ""))
            ).lower()
            score = sum(1.0 for token in query_tokens if token in haystack)
            score += sum(2.0 for phrase in phrases if phrase.lower() in haystack)
            if query.strip().lower() == full_name.lower():
                score += 10.0
            if score:
                scored.append((score, row))
        scored.sort(key=lambda item: (-item[0], item[1].get("full_name", "")))
        return [self._candidate(query, row) for _, row in scored[:limit]]

    def _candidate(self, query: str, row: dict[str, str]) -> ApiCandidate:
        full_name = row.get("full_name", "")
        asset_id = row.get("asset_id", "")
        stable = hashlib.sha1(f"{row.get('guid', '')}:{asset_id}".encode()).hexdigest()[:16]
        kind = row.get("kind", "method")
        allowed = set(get_args(CandidateKind))
        if kind not in allowed:
            kind = "method"
        return ApiCandidate(
            id=f"api-{stable}",
            query=query,
            kind=kind,
            full_name=full_name,
            summary=row.get("summary", ""),
            signature=asset_id or None,
            guid=row.get("guid") or None,
            assembly="NXOpen" if full_name.startswith("NXOpen.") else None,
            source=str(self.index_path),
        )


def search_nx_api(
    query: str,
    *,
    kind: CandidateKind | None = None,
    namespace: str | None = None,
    limit: int = 8,
    catalog: ApiCatalog | None = None,
) -> list[ApiCandidate]:
    """Convenience function used by planning and future typed tools."""

    return (catalog or ApiCatalog()).search(query, kind=kind, namespace=namespace, limit=limit)


def validate_candidate(
    candidate: ApiCandidate,
    *,
    required_terms: Iterable[str] = (),
    nx_version: str | None = None,
) -> ApiCandidate:
    """Apply deterministic evidence checks without invoking NXOpen."""

    haystack = " ".join((candidate.full_name, candidate.summary, candidate.signature or "")).lower()
    missing = [term for term in required_terms if term.lower() not in haystack]
    if missing:
        return candidate.model_copy(
            update={
                "status": "rejected",
                "validation_message": f"candidate lacks required terms: {', '.join(missing)}",
            }
        )
    return candidate.model_copy(
        update={
            "status": "validated",
            "nx_version": nx_version,
            "validation_message": "catalog evidence is sufficient for bridge probe",
        }
    )
