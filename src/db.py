"""
The ground-truth botanical + toxicological database and the deterministic
query engine that sits behind the agent's tools.

Nothing in this module calls a language model.  Every answer is derived from
the curated CSV, which is exactly the point of the proposed method: the
safety-critical decisions are made by deterministic code, not by an LLM.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

from .config import (
    DATABASE_CSV,
    LIGHT_COMPATIBILITY,
    MOISTURE_COMPATIBILITY,
)

VALID_PETS = ("cat", "dog")
VALID_LIGHT = ("full_sun", "partial_shade", "bright_indirect", "full_shade")
VALID_MOISTURE = ("low", "moderate", "high")

# The model sometimes writes "bright indirect light" or "part sun" instead of
# our controlled vocabulary.  These helpers map free text onto the vocabulary
# so that the deterministic filter never silently returns an empty pool.
_LIGHT_ALIASES = {
    "full sun": "full_sun", "fullsun": "full_sun", "sun": "full_sun",
    "sunny": "full_sun", "direct sun": "full_sun", "6+ hours": "full_sun",
    "bright sun": "full_sun", "high light": "full_sun",
    "partial sun": "partial_shade", "part sun": "partial_shade",
    "partial shade": "partial_shade", "part shade": "partial_shade",
    "partly shady": "partial_shade", "semi shade": "partial_shade",
    "half sun": "partial_shade", "dappled": "partial_shade",
    "filtered light": "partial_shade", "indirect light": "bright_indirect",
    "bright indirect": "bright_indirect", "bright": "bright_indirect",
    "indoor light": "bright_indirect",
    "full shade": "full_shade", "deep shade": "full_shade",
    "shade": "full_shade", "no direct sun": "full_shade", "shaded": "full_shade",
}

_MOISTURE_ALIASES = {
    "dry": "low", "low": "low", "low moisture": "low", "arid": "low",
    "infrequent watering": "low", "well drained": "low",
    "moderate": "moderate", "medium": "moderate", "average": "moderate",
    "normal": "moderate", "regular": "moderate",
    "wet": "high", "high": "high", "high moisture": "high",
    "moist": "high", "humid": "high", "rainy": "high", "boggy": "high",
}


def normalize_light(value: str) -> str:
    """Map a free-text sunlight description onto the controlled vocabulary."""
    key = _slug(value).replace(" ", " ")
    if key in VALID_LIGHT:
        return key
    if key in _LIGHT_ALIASES:
        return _LIGHT_ALIASES[key]
    for alias, canonical in _LIGHT_ALIASES.items():
        if alias in key:
            return canonical
    return key


def normalize_moisture(value: str) -> str:
    """Map a free-text moisture description onto the controlled vocabulary."""
    key = _slug(value)
    if key in VALID_MOISTURE:
        return key
    if key in _MOISTURE_ALIASES:
        return _MOISTURE_ALIASES[key]
    for alias, canonical in _MOISTURE_ALIASES.items():
        if alias in key:
            return canonical
    return key


def normalize_pets(value) -> list[str]:
    """Normalise a pet list ("cats", "Cat", ["cat"]) into ["cat", "dog"]."""
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    out = []
    for v in value:
        if not isinstance(v, str):
            continue
        v = v.lower().strip()
        if "cat" in v:
            out.append("cat")
        elif "dog" in v:
            out.append("dog")
    # preserve order, no duplicates
    seen, uniq = set(), []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq



def _slug(text: str) -> str:
    """Lower-case, strip punctuation, collapse whitespace -> comparable key."""
    text = unicodedata.normalize("NFKD", str(text)).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class PlantRecord:
    """One row of the ground-truth database."""

    id: str
    scientific_name: str
    common_name: str
    plant_type: str
    light: str
    moisture: str
    toxic_to_cats: bool
    toxic_to_dogs: bool
    source_url: str
    notes: str

    @property
    def is_safe_for(self) -> str:  # placeholder to keep dataclass simple
        return ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "scientific_name": self.scientific_name,
            "common_name": self.common_name,
            "plant_type": self.plant_type,
            "light": self.light,
            "moisture": self.moisture,
            "toxic_to_cats": self.toxic_to_cats,
            "toxic_to_dogs": self.toxic_to_dogs,
            "source_url": self.source_url,
            "notes": self.notes,
        }

    def public_dict(self) -> dict:
        """The subset handed to the LLM (toxicity flags are shown as warnings)."""
        d = self.to_dict()
        d["toxic_to_cats"] = bool(self.toxic_to_cats)
        d["toxic_to_dogs"] = bool(self.toxic_to_dogs)
        return d


class PlantDatabase:
    """Loads the CSV and answers every deterministic question about it."""

    def __init__(self, csv_path: Path | str = DATABASE_CSV):
        self.csv_path = Path(csv_path)
        self.df = self._load(self.csv_path)
        self._index = self._build_index(self.df)

    # ------------------------------------------------------------ loading --
    @staticmethod
    def _load(csv_path: Path) -> pd.DataFrame:
        if not csv_path.exists():
            raise FileNotFoundError(
                f"Ground-truth database not found at {csv_path}. "
                "It is shipped with this project; restore it from the repository."
            )
        df = pd.read_csv(csv_path).fillna("")
        required = {
            "id", "scientific_name", "common_name", "plant_type", "light",
            "moisture", "toxic_to_cats", "toxic_to_dogs", "source_url", "notes",
        }
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"{csv_path} is missing columns: {sorted(missing)}")
        df["toxic_to_cats"] = df["toxic_to_cats"].astype(int).astype(bool)
        df["toxic_to_dogs"] = df["toxic_to_dogs"].astype(int).astype(bool)
        for col in ("light", "moisture"):
            df[col] = df[col].str.strip().str.lower()
        return df

    @staticmethod
    def _build_index(df: pd.DataFrame) -> dict[str, str]:
        """Map every alias (scientific name, common name, synonyms) -> plant id."""
        index: dict[str, str] = {}
        for _, row in df.iterrows():
            pid = str(row["id"])
            names = [row["scientific_name"], row["common_name"]]
            names += str(row["common_name"]).split(";")
            for name in names:
                key = _slug(name)
                if key:
                    index.setdefault(key, pid)
        return index

    # -------------------------------------------------------------- access --
    def __len__(self) -> int:
        return len(self.df)

    @property
    def records(self) -> list[PlantRecord]:
        out = []
        for _, row in self.df.iterrows():
            out.append(
                PlantRecord(
                    id=str(row["id"]),
                    scientific_name=str(row["scientific_name"]),
                    common_name=str(row["common_name"]),
                    plant_type=str(row["plant_type"]),
                    light=str(row["light"]),
                    moisture=str(row["moisture"]),
                    toxic_to_cats=bool(row["toxic_to_cats"]),
                    toxic_to_dogs=bool(row["toxic_to_dogs"]),
                    source_url=str(row["source_url"]),
                    notes=str(row["notes"]),
                )
            )
        return out

    def get(self, plant_id: str) -> PlantRecord | None:
        row = self.df[self.df["id"] == plant_id]
        if row.empty:
            return None
        r = row.iloc[0]
        return PlantRecord(
            id=str(r["id"]),
            scientific_name=str(r["scientific_name"]),
            common_name=str(r["common_name"]),
            plant_type=str(r["plant_type"]),
            light=str(r["light"]),
            moisture=str(r["moisture"]),
            toxic_to_cats=bool(r["toxic_to_cats"]),
            toxic_to_dogs=bool(r["toxic_to_dogs"]),
            source_url=str(r["source_url"]),
            notes=str(r["notes"]),
        )

    def resolve(self, name: str) -> PlantRecord | None:
        """Resolve a free-text plant name (as written by an LLM) to a record."""
        if not name:
            return None
        key = _slug(name)
        pid = self._index.get(key)
        if pid:
            return self.get(pid)
        # fall back to a containment match on the scientific name
        for alias, cand_id in self._index.items():
            if len(alias) >= 5 and (alias in key or key in alias):
                return self.get(cand_id)
        return None

    # --------------------------------------------------------- constraints --
    def is_toxic_for(self, record: PlantRecord, pets: Sequence[str]) -> bool:
        """True if the record is toxic to ANY of the given pets."""
        for pet in pets:
            if pet == "cat" and record.toxic_to_cats:
                return True
            if pet == "dog" and record.toxic_to_dogs:
                return True
        return False

    def is_viable_for(
        self, record: PlantRecord, light: str, moisture: str
    ) -> bool:
        """True if the plant survives the site's light and moisture conditions."""
        light_ok = record.light in LIGHT_COMPATIBILITY.get(light, set())
        moisture_ok = record.moisture in MOISTURE_COMPATIBILITY.get(moisture, set())
        return light_ok and moisture_ok

    def query(
        self,
        pets: Iterable[str] = (),
        light: str | None = None,
        moisture: str | None = None,
        plant_type: str | None = None,
        limit: int | None = None,
        only_safe: bool = True,
    ) -> list[PlantRecord]:
        """
        The single deterministic filter used by the agent's tool.

        only_safe=True  -> drop everything toxic to any of `pets`.
        only_safe=False -> keep toxic species (used by the naive-RAG baseline
                           and by the audit step to demonstrate what the LLM
                           would have wrongly proposed).
        """
        pets = [p.lower() for p in pets if p]
        rows = self.df
        if only_safe and pets:
            mask = pd.Series(True, index=rows.index)
            if "cat" in pets:
                mask &= ~rows["toxic_to_cats"]
            if "dog" in pets:
                mask &= ~rows["toxic_to_dogs"]
            rows = rows[mask]
        if light:
            allowed = LIGHT_COMPATIBILITY.get(normalize_light(light), set())
            rows = rows[rows["light"].isin(allowed)]
        if moisture:
            allowed = MOISTURE_COMPATIBILITY.get(normalize_moisture(moisture), set())
            rows = rows[rows["moisture"].isin(allowed)]
        if plant_type:
            rows = rows[rows["plant_type"].str.lower() == plant_type.lower()]

        records = [
            PlantRecord(
                id=str(r["id"]),
                scientific_name=str(r["scientific_name"]),
                common_name=str(r["common_name"]),
                plant_type=str(r["plant_type"]),
                light=str(r["light"]),
                moisture=str(r["moisture"]),
                toxic_to_cats=bool(r["toxic_to_cats"]),
                toxic_to_dogs=bool(r["toxic_to_dogs"]),
                source_url=str(r["source_url"]),
                notes=str(r["notes"]),
            )
            for _, r in rows.iterrows()
        ]
        if limit:
            records = records[:limit]
        return records

    # -------------------------------------------------------------- stats ---
    def stats(self) -> dict:
        df = self.df
        return {
            "total": int(len(df)),
            "safe_for_both": int((~df["toxic_to_cats"] & ~df["toxic_to_dogs"]).sum()),
            "toxic_to_cats": int(df["toxic_to_cats"].sum()),
            "toxic_to_dogs": int(df["toxic_to_dogs"].sum()),
            "by_light": df["light"].value_counts().to_dict(),
            "by_moisture": df["moisture"].value_counts().to_dict(),
            "by_type": df["plant_type"].value_counts().to_dict(),
        }


_DB_SINGLETON: PlantDatabase | None = None


def get_database(csv_path: Path | str = DATABASE_CSV) -> PlantDatabase:
    """Process-wide singleton so the CSV is parsed only once."""
    global _DB_SINGLETON
    if _DB_SINGLETON is None:
        _DB_SINGLETON = PlantDatabase(csv_path)
    return _DB_SINGLETON
