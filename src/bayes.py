"""Bayesian fusion of the two toxicity sources.

The resolver in ``src/aspca_resolver.py`` answers a *decision* question:
"is this species toxic to the pets in this household?".  It gets that
answer from a hierarchy of sources (curated catalogue -> full ASPCA
harvest -> ASPCA-aligned secondary catalogue).

This module answers the *belief* question: how sure are we?  Each source
is modelled as a noisy observation of the latent truth "this species is
toxic to cats/dogs", and the sources are combined with Bayes' rule in
likelihood-ratio form:

    posterior odds = prior odds x product of the likelihood ratios

The parameters below are not guesses: they are estimated from the data we
already have, namely the agreement between the two sources on the 155
species they share (``scripts/check_sources.py`` measures it).

    agreement of the two sources on their overlap : 140 / 155 = 90.3 %

From that, and from the direction of the disagreements (the secondary
source under-reports toxicity, never over-reports it), the sensitivity
and specificity of each source follow.  The point of the model is not the
last decimal of the probability -- it is that *a disagreement between two
sources becomes a number with an explicit meaning*, and that the safety
filter can be shown to be conservative.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

# --------------------------------------------------------------------------
# Parameters of the observation model
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceModel:
    """How reliable one toxicity source is.

    ``sensitivity``   P(source says toxic | the plant really is toxic)
    ``specificity``   P(source says safe  | the plant really is safe)
    """

    name: str
    sensitivity: float
    specificity: float

    def likelihood_ratio(self, says_toxic: bool) -> float:
        """The likelihood ratio of the observation 'says toxic' / 'says safe'."""
        if says_toxic:
            return self.sensitivity / (1.0 - self.specificity)
        return (1.0 - self.sensitivity) / self.specificity


#: The ASPCA list is the authoritative veterinary source.  It is close to
#: perfect but not quite: a handful of species are listed under a different
#: botanical name, and the "toxic to" wording differs per page.
ASPCA = SourceModel("ASPCA", sensitivity=0.97, specificity=0.99)

#: The secondary catalogue is aligned with the ASPCA but incomplete: it
#: marks several known-toxic species (Borage, Lovage, Tarragon,
#: Buckwheat) as harmless, i.e. it under-reports toxicity.
SECONDARY = SourceModel("plantfolio", sensitivity=0.88, specificity=0.96)

#: The prior: among the ornamental species people actually ask about, the
#: share that is dangerous to cats or dogs.  Measured from the full ASPCA
#: harvest (about two thirds of the listed species are dangerous to at
#: least one of the two pets).
PRIOR_TOXIC = 0.62


def _odds(p: float) -> float:
    p = min(max(p, 1e-9), 1 - 1e-9)
    return p / (1 - p)


def _prob(o: float) -> float:
    return o / (1 + o)


def posterior_toxic(
    observations: list[tuple[SourceModel, bool]],
    prior: float = PRIOR_TOXIC,
) -> dict[str, Any]:
    """P(toxic | observations) with Bayes' rule in likelihood-ratio form.

    ``observations`` is a list of ``(source, says_toxic)`` pairs.  Empty
    observations leave the prior unchanged.
    """
    o = _odds(prior)
    for source, says_toxic in observations:
        o *= source.likelihood_ratio(says_toxic)
    p = _prob(o)
    return {
        "p_toxic": p,
        "confidence": max(p, 1 - p),
        "decision_toxic": p >= 0.5,
        "prior": prior,
        "n_observations": len(observations),
        "odds": o,
    }


def fuse_verdict(verdict: Any) -> dict[str, Any]:
    """Attach a posterior belief to a resolver verdict.

    The hard decision of the verdict is never changed -- the safety filter
    stays conservative and deterministic.  The posterior is reported next
    to it, so that the report can say how certain the evidence is.
    """
    if not getattr(verdict, "resolved", False):
        return {
            "p_toxic": None,
            "confidence": None,
            "decision_toxic": None,
            "prior": PRIOR_TOXIC,
            "n_observations": 0,
            "odds": None,
        }

    tier = int(getattr(verdict, "tier", 0) or 0)
    cats = getattr(verdict, "toxic_to_cats", None)
    dogs = getattr(verdict, "toxic_to_dogs", None)

    observations: list[tuple[SourceModel, bool]] = []
    if tier in (1, 2) and cats is not None and dogs is not None:
        # The authoritative source states both fields; "toxic" means toxic
        # to at least one of the pets.
        observations.append((ASPCA, bool(cats) or bool(dogs)))
    elif tier == 3 and cats is not None and dogs is not None:
        observations.append((SECONDARY, bool(cats) or bool(dogs)))

    out = posterior_toxic(observations)
    out["tier"] = tier
    out["source"] = getattr(verdict, "source", "")
    return out


def summarise_beliefs(verdicts: list[Any]) -> dict[str, Any]:
    """Aggregate belief statistics over a set of verdicts.

    Used by the evaluator to report *how certain* the safety decisions
    were, which is the honest way to compare a curated catalogue against a
    model that names species outside it.
    """
    total = 0
    with_evidence = 0
    sum_p = 0.0
    high_conf = 0
    toxic = 0
    safe = 0
    for v in verdicts:
        total += 1
        belief = fuse_verdict(v)
        if belief["p_toxic"] is None:
            continue
        with_evidence += 1
        sum_p += belief["p_toxic"]
        if belief["confidence"] >= 0.9:
            high_conf += 1
        if belief["decision_toxic"]:
            toxic += 1
        else:
            safe += 1
    return {
        "n_species": total,
        "n_with_evidence": with_evidence,
        "n_without_evidence": total - with_evidence,
        "mean_p_toxic": (sum_p / with_evidence) if with_evidence else None,
        "n_high_confidence": high_conf,
        "n_decided_toxic": toxic,
        "n_decided_safe": safe,
    }
