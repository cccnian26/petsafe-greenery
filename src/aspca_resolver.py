"""
Species resolution -- the "ASPCA-aligned" lookup for species that are not in
the curated catalogue.

Why this module exists
----------------------
The curated catalogue (``data/plants.csv``, 150 species) is the agent's
candidate pool: every label in it comes from the ASPCA and every light and
moisture value was resolved from NC State.  It is deliberately small and
curated.

But the baselines are allowed to name *any* species.  When a zero-shot LLM
writes "Peace Lily" and that species is outside the 150, the evaluator used
to have no choice but to count it as unsafe -- which understates the
baseline.  The honest way to score it is to resolve the name against the
best available evidence and record where that evidence came from.

This module implements a three-tier resolution with explicit provenance:

    tier 1   data/plants.csv        curated, ASPCA + NC State   (primary)
    tier 2   data/aspca_snapshot.json  full ASPCA harvest       (authoritative)
    tier 3   data/plantfolio_catalog.json  plantfolio-common-plants
             (ASPCA-aligned secondary source) plus the alias map
             data/plant_aliases.json, which turns a free-text name into a
             canonical one

Tier 2 and tier 3 are *not* merged into the curated catalogue: they are
evidence used at evaluation time, and every verdict keeps its source and
source URL.  Nothing here touches the network -- the snapshots are committed
files, so evaluation stays deterministic and reproducible.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .bayes import fuse_verdict
from .config import ROOT

SNAPSHOT_PATH = ROOT / "data" / "aspca_snapshot.json"
CATALOG_PATH = ROOT / "data" / "plantfolio_catalog.json"
ALIAS_PATH = ROOT / "data" / "plant_aliases.json"

TIER_NAMES = {
    1: "curated DB (ASPCA + NC State)",
    2: "ASPCA full harvest",
    3: "plantfolio-common-plants (ASPCA-aligned)",
}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


@dataclass
class Verdict:
    """The outcome of resolving one free-text plant name."""
    name: str = ""
    canonical: str = ""
    resolved: bool = False
    tier: int = 0
    source: str = ""
    source_url: str | None = None
    toxic_to_cats: bool | None = None
    toxic_to_dogs: bool | None = None
    light: str | None = None
    moisture: str | None = None
    severity: str = ""          # tier 3 only: toxic / mildlyToxic / nonToxic
    note: str = ""
    belief: dict = field(default_factory=dict)   # Bayesian posterior

    @property
    def tier_name(self) -> str:
        return TIER_NAMES.get(self.tier, "unresolved")

    @property
    def certified_safe(self) -> bool:
        """True only when the evidence positively says 'non-toxic'."""
        if self.toxic_to_cats is None or self.toxic_to_dogs is None:
            return False
        return not self.toxic_to_cats and not self.toxic_to_dogs

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "canonical": self.canonical,
            "resolved": self.resolved,
            "tier": self.tier,
            "tier_name": self.tier_name,
            "source": self.source,
            "source_url": self.source_url,
            "toxic_to_cats": self.toxic_to_cats,
            "toxic_to_dogs": self.toxic_to_dogs,
            "light": self.light,
            "moisture": self.moisture,
            "severity": self.severity,
            "note": self.note,
            "belief": self.belief,
        }


class SpeciesResolver:
    """
    Resolve a plant name to a toxicity verdict, with provenance.

        resolver = SpeciesResolver()
        v = resolver.resolve("Peace Lily")
        v.resolved, v.tier_name, v.toxic_to_cats
    """

    def __init__(
        self,
        snapshot_path: Path | str = SNAPSHOT_PATH,
        catalog_path: Path | str = CATALOG_PATH,
        alias_path: Path | str = ALIAS_PATH,
        db: Any = None,
    ) -> None:
        self.snapshot = self._load(snapshot_path)
        self.catalog = self._load(catalog_path)
        self.aliases = self._load(alias_path)
        self._db = db

    # ------------------------------------------------------------ loading --
    @staticmethod
    def _load(path: Path | str) -> dict:
        p = Path(path)
        if not p.exists():
            return {}
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    @property
    def db(self):
        if self._db is None:
            from .db import get_database
            self._db = get_database()
        return self._db

    @property
    def available(self) -> bool:
        """True when at least one external source could be loaded."""
        return bool(self.snapshot or self.catalog)

    # ---------------------------------------------------------- resolution --
    def _canonical_name(self, name: str) -> str:
        """Use the alias map to turn a free-text name into a canonical one."""
        key = _slug(name)
        if key in self.aliases:
            return self.aliases[key]
        # "Peace Lily Sensation" -> "Peace Lily"
        for alias_key, canonical in self.aliases.items():
            if len(alias_key) >= 5 and (alias_key in key or key in alias_key):
                return canonical
        return name

    def _from_snapshot(self, name: str) -> dict | None:
        key = _slug(name)
        rec = self.snapshot.get(key)
        if rec:
            return rec
        for alias_key, rec in self.snapshot.items():
            if len(alias_key) >= 6 and (alias_key in key or key in alias_key):
                return rec
        return None

    def _from_catalog(self, name: str) -> dict | None:
        key = _slug(name)
        rec = self.catalog.get(key)
        if rec:
            return rec
        for alias_key, rec in self.catalog.items():
            if len(alias_key) >= 6 and (alias_key in key or key in alias_key):
                return rec
        return None

    def resolve(self, name: str) -> Verdict:
        """Resolve one name and attach the Bayesian belief to the verdict."""
        verdict = self._resolve(name)
        try:
            verdict.belief = fuse_verdict(verdict)
        except Exception:                                    # noqa: BLE001
            verdict.belief = {}
        return verdict

    def _resolve(self, name: str) -> Verdict:
        name = (name or "").strip()
        if not name:
            return Verdict(name=name, note="empty name")

        # ---- tier 1: the curated catalogue -------------------------- #
        try:
            rec = self.db.resolve(name)
        except Exception:                                    # noqa: BLE001
            rec = None
        if rec is not None:
            return Verdict(
                name=name,
                canonical=rec.scientific_name or rec.common_name,
                resolved=True,
                tier=1,
                source="data/plants.csv (ASPCA toxicity + NC State light)",
                source_url=rec.source_url or None,
                toxic_to_cats=bool(rec.toxic_to_cats),
                toxic_to_dogs=bool(rec.toxic_to_dogs),
                light=rec.light,
                moisture=rec.moisture,
                note="in the curated catalogue",
            )

        canonical = self._canonical_name(name)

        # ---- tier 2: the full ASPCA harvest ------------------------- #
        snap = self._from_snapshot(canonical) or self._from_snapshot(name)
        if snap is not None:
            cats = snap.get("toxic_to_cats")
            dogs = snap.get("toxic_to_dogs")
            if cats is not None and dogs is not None:
                return Verdict(
                    name=name,
                    canonical=snap.get("scientific_name") or snap.get("common_name") or canonical,
                    resolved=True,
                    tier=2,
                    source="ASPCA full harvest (authoritative)",
                    source_url=snap.get("source_url"),
                    toxic_to_cats=bool(cats),
                    toxic_to_dogs=bool(dogs),
                    note="resolved against the ASPCA index",
                )

        # ---- tier 3: ASPCA-aligned secondary source ------------------ #
        cat = self._from_catalog(canonical) or self._from_catalog(name)
        if cat is not None and cat.get("toxicity_verified"):
            return Verdict(
                name=name,
                canonical=cat.get("common_name") or canonical,
                resolved=True,
                tier=3,
                source="plantfolio-common-plants (ASPCA-aligned, secondary)",
                source_url=cat.get("source_url"),
                toxic_to_cats=bool(cat.get("toxic_to_cats")),
                toxic_to_dogs=bool(cat.get("toxic_to_dogs")),
                light=cat.get("light") or None,
                moisture=cat.get("moisture") or None,
                severity=cat.get("plant_toxicity") or "",
                note="resolved against the ASPCA-aligned secondary catalogue",
            )

        # a plantfolio entry whose toxicity is unknown is still a *known*
        # species, just not a certifiable one
        if cat is not None:
            return Verdict(
                name=name,
                canonical=cat.get("common_name") or canonical,
                resolved=False,
                tier=3,
                source="plantfolio-common-plants (ASPCA-aligned, secondary)",
                source_url=cat.get("source_url"),
                toxic_to_cats=None,
                toxic_to_dogs=None,
                light=cat.get("light") or None,
                moisture=cat.get("moisture") or None,
                severity=cat.get("plant_toxicity") or "unknown",
                note="species known, toxicity not stated by any source",
            )

        return Verdict(name=name, canonical=canonical, resolved=False,
                       note="not found in any source")

    def resolve_many(self, names: list[str]) -> list[Verdict]:
        return [self.resolve(n) for n in names]

    # ------------------------------------------------------ cross-checking --
    def agreement(self) -> dict[str, Any]:
        """
        Compare the two independent toxicity sources on their overlap.

        Tier 2 (ASPCA, authoritative) vs tier 3 (plantfolio, ASPCA-aligned).
        The result is reported in the paper as evidence that the secondary
        source does not distort the safety verdict.
        """
        overlap = agree = 0
        conflicts: list[dict[str, Any]] = []
        for key, snap in self.snapshot.items():
            cat = self.catalog.get(key)
            if not cat or not cat.get("toxicity_verified"):
                continue
            overlap += 1
            a_cats = bool(snap.get("toxic_to_cats"))
            a_dogs = bool(snap.get("toxic_to_dogs"))
            b_cats = bool(cat.get("toxic_to_cats"))
            b_dogs = bool(cat.get("toxic_to_dogs"))
            if a_cats == b_cats and a_dogs == b_dogs:
                agree += 1
            else:
                conflicts.append({
                    "name": snap.get("common_name") or key,
                    "aspca": {"cats": a_cats, "dogs": a_dogs},
                    "plantfolio": {"cats": b_cats, "dogs": b_dogs,
                                   "severity": cat.get("plant_toxicity")},
                })
        return {
            "overlap": overlap,
            "agree": agree,
            "agreement_rate": round(agree / overlap, 4) if overlap else None,
            "conflicts": conflicts,
        }


_RESOLVER: SpeciesResolver | None = None


def get_resolver() -> SpeciesResolver:
    """Shared resolver instance (loading the snapshots is cheap but not free)."""
    global _RESOLVER
    if _RESOLVER is None:
        _RESOLVER = SpeciesResolver()
    return _RESOLVER
