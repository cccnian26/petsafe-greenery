"""K-means clustering of the candidate pool (unsupervised learning).

The agent may pick six plants that all belong to the same family, which
looks careless to a gardener.  Clustering the candidates first and asking
for one plant per cluster spreads the palette across the space of
possible plants without changing the safety filter -- the clusters are
built from the *already verified* candidates, so the pet-safety
constraint is untouched.

The implementation is written from scratch (no scikit-learn): the
algorithm is the standard Lloyd iteration of the lecture --

    1. assign every point to the nearest cluster centre,
    2. move every centre to the mean of its points,
    3. repeat until the centres stop moving.

The features are the ones that matter for a planting palette: the light
the plant tolerates, the moisture it needs and its growth habit (the
plant type).  They are scaled first, because the three features have
different units.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Sequence

from .config import LIGHT_COMPATIBILITY, MOISTURE_COMPATIBILITY

#: The light classes, ordered from darkest to brightest.
LIGHT_ORDER = ["full_shade", "bright_indirect", "partial_shade", "full_sun"]
MOISTURE_ORDER = ["low", "moderate", "high"]

#: One-hot encoding of the growth habits used by the catalogue.
PLANT_TYPES = ["herb", "shrub", "tree", "grass", "groundcover", "succulent",
               "vine", "hanging", "flower", "bulb", "fern", "palm"]


@dataclass
class Cluster:
    """One cluster of the candidate pool."""

    index: int
    centre: list[float]
    members: list[str] = field(default_factory=list)

    @property
    def size(self) -> int:
        return len(self.members)


@dataclass
class Plant:
    """One candidate, with its feature vector."""

    name: str
    plant_type: str
    light: str
    moisture: str
    vector: list[float]


def _one_hot(value: str, options: Sequence[str]) -> list[float]:
    if value in options:
        return [1.0 if value == o else 0.0 for o in options]
    return [0.0] * len(options)


def features(record: Any) -> list[float]:
    """The feature vector of one plant record."""
    vec: list[float] = []
    vec.append(float(LIGHT_ORDER.index(record.light))
               if record.light in LIGHT_ORDER else 0.0)
    vec.append(float(MOISTURE_ORDER.index(record.moisture))
               if record.moisture in MOISTURE_ORDER else 0.0)
    vec.extend(_one_hot(str(record.plant_type).lower(), PLANT_TYPES))
    return vec


def scale(vectors: list[list[float]]) -> list[list[float]]:
    """Scale every feature to the unit interval (min-max)."""
    if not vectors:
        return []
    n = len(vectors[0])
    mins = [min(v[i] for v in vectors) for i in range(n)]
    maxs = [max(v[i] for v in vectors) for i in range(n)]
    out = []
    for v in vectors:
        row = []
        for i in range(n):
            span = maxs[i] - mins[i]
            row.append((v[i] - mins[i]) / span if span > 0 else 0.0)
        out.append(row)
    return out


def distance(a: Sequence[float], b: Sequence[float]) -> float:
    """Euclidean distance."""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def kmeans(vectors: list[list[float]], k: int,
           max_iter: int = 50, seed: int = 7) -> list[Cluster]:
    """Lloyd's algorithm: assign, update, repeat.

    The initial centres are spread evenly over the (sorted) points, which
    makes the result deterministic -- the same input always gives the same
    clustering, which matters because the evaluation must be reproducible.
    """
    if not vectors:
        return []
    k = max(1, min(int(k), len(vectors)))
    points = scale(vectors)
    order = sorted(range(len(points)), key=lambda i: tuple(points[i]))
    centres = [list(points[order[int(i * len(order) / k)]]) for i in range(k)]

    assignment = [-1] * len(points)
    for _ in range(max_iter):
        changed = False
        for idx, point in enumerate(points):
            best, best_d = 0, float("inf")
            for c_idx, centre in enumerate(centres):
                d = distance(point, centre)
                if d < best_d:
                    best, best_d = c_idx, d
            if assignment[idx] != best:
                assignment[idx] = best
                changed = True
        for c_idx in range(k):
            members = [points[i] for i, a in enumerate(assignment) if a == c_idx]
            if members:
                centres[c_idx] = [sum(m[i] for m in members) / len(members)
                                  for i in range(len(points[0]))]
        if not changed:
            break

    clusters = [Cluster(index=i, centre=centres[i]) for i in range(k)]
    for idx, point in enumerate(points):
        clusters[assignment[idx]].members.append(str(idx))
    return clusters


def cluster_candidates(records: Sequence[Any], k: int = 4) -> dict[str, Any]:
    """Cluster a candidate pool and return one representative per cluster.

    The representative of a cluster is the member closest to the centre,
    i.e. the most typical plant of that group -- the same rule a gardener
    would use to pick a representative for a group of similar plants.
    """
    if not records:
        return {"clusters": [], "representatives": [], "k": 0}
    vectors = [features(r) for r in records]
    points = scale(vectors)
    clusters = kmeans(vectors, k)
    representatives: list[str] = []
    details = []
    for cluster in clusters:
        names = []
        best_name, best_d = "", float("inf")
        for idx in cluster.members:
            name = records[int(idx)].common_name or records[int(idx)].scientific_name
            names.append(name)
            d = distance(points[int(idx)], cluster.centre)
            if d < best_d:
                best_name, best_d = name, d
        if best_name:
            representatives.append(best_name)
        details.append({
            "index": cluster.index,
            "size": cluster.size,
            "members": names,
            "representative": best_name,
            "centre": [round(c, 4) for c in cluster.centre],
        })
    return {
        "k": len(clusters),
        "clusters": details,
        "representatives": representatives,
    }


def diversity_index(records: Sequence[Any]) -> dict[str, Any]:
    """How varied is a palette?

    ``n_families``      number of different plant families
    ``n_types``         number of different growth habits
    ``n_clusters``      number of K-means clusters the palette covers
    ``cluster_coverage`` fraction of the clusters of the whole candidate
                        pool that the palette touches
    """
    if not records:
        return {"n_plants": 0, "n_families": 0, "n_types": 0,
                "n_clusters": 0, "cluster_coverage": 0.0}
    # The family is not part of the record dataclass, so it is read from
    # the database frame when it is available.
    families: set[str] = set()
    try:
        from .db import get_database
        frame = get_database().df
        by_name = dict(zip(frame["common_name"], frame["family"]))
        for r in records:
            families.add(str(by_name.get(r.common_name, "")))
    except Exception:                                       # noqa: BLE001
        families = {""}
    types = {str(r.plant_type).lower() for r in records}
    vectors = [features(r) for r in records]
    clusters = kmeans(vectors, min(4, len(records)))
    labels = set()
    points = scale(vectors)
    for cluster in clusters:
        for idx in cluster.members:
            best, best_d = 0, float("inf")
            for c_idx, centre in enumerate(clusters):
                d = distance(points[int(idx)], centre.centre)
                if d < best_d:
                    best, best_d = c_idx, d
            labels.add(best)
    return {
        "n_plants": len(records),
        "n_families": len(families - {""}),
        "n_types": len(types),
        "n_clusters": len(labels),
        "cluster_coverage": (len(labels) / len(clusters)) if clusters else 0.0,
    }
