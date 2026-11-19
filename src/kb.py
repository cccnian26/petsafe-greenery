"""A Horn-clause knowledge base with a forward-chaining inference engine.

This is the formal, teachable version of the filter that the agent uses.
The production filter (``src/db.py``) is written as ordinary Python; the
rules it implements are exactly the rules declared here, and
``scripts/test_kb_parity.py`` proves that the two agree on every species
and every scenario.

The knowledge base uses Horn clauses -- ``(premise_1 AND ... AND premise_n)
=> conclusion`` -- with at most one *stratified* negative literal
(``!forbidden(S)``), which is the usual way of writing "the rule did not
fire" without leaving Horn form.  Negation is stratified because the
negative literal always refers to a predicate that is derived earlier.

Forward chaining follows the classic agenda algorithm of the lecture:
repeatedly fire any rule whose premises are all present, add the
conclusion to the knowledge base, until nothing new can be derived.  The
engine records every firing, so the derivation can be shown and audited.

Example
-------
    facts:  pet_present(cat), toxic_to_cat(Lilium)
    rule:   pet_present(cat) AND toxic_to_cat(S) => forbidden(S)
    result: forbidden(Lilium) is derived, and Lilium is not a candidate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .config import LIGHT_COMPATIBILITY, MOISTURE_COMPATIBILITY

# --------------------------------------------------------------------------
# Syntax
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Clause:
    """One Horn clause.

    A predicate is written ``name`` or ``name(arg, arg)``; an argument that
    starts with ``?`` is a variable, everything else is a constant.
    """

    rule_id: str
    premises: tuple[str, ...]
    conclusion: str
    comment: str = ""

    def __str__(self) -> str:
        head = " AND ".join(self.premises) if self.premises else "TRUE"
        return f"{head} => {self.conclusion}"


def _parse(text: str) -> tuple[str, tuple[str, ...]]:
    """``"toxic_to_cat(S)"`` -> ``("toxic_to_cat", ("S",))``."""
    text = text.strip()
    if "(" not in text:
        return text, ()
    name, _, rest = text.partition("(")
    args = rest.rstrip(")").split(",")
    return name.strip(), tuple(a.strip() for a in args if a.strip())


@dataclass(frozen=True)
class Fact:
    predicate: str
    args: tuple[str, ...] = ()

    def __str__(self) -> str:
        if not self.args:
            return self.predicate
        return f"{self.predicate}({', '.join(self.args)})"


# --------------------------------------------------------------------------
# The knowledge base
# --------------------------------------------------------------------------

#: The rules of the domain, written once, in one place.
#:
#: They are ordinary Horn clauses over four kinds of facts:
#:   * toxicity   -- ``toxic_to_cat(S)``, ``toxic_to_dog(S)``
#:   * the site   -- ``site_light(L)``, ``site_moisture(M)``,
#:                   ``pet_present(cat)``
#:   * the plant  -- ``light_ok(S)``, ``moisture_ok(S)``
#:   * the verdict-- ``forbidden(S)``, ``candidate_l0(S)``, ...
CLAUSES: tuple[Clause, ...] = (
    Clause(
        "safety-cat",
        ("pet_present(cat)", "toxic_to_cat(?S)"),
        "forbidden(?S)",
        "A plant that is toxic to cats may not be recommended to a household "
        "with a cat.  This rule is never relaxed.",
    ),
    Clause(
        "safety-dog",
        ("pet_present(dog)", "toxic_to_dog(?S)"),
        "forbidden(?S)",
        "The same for dogs.",
    ),
    Clause(
        "light-compatibility",
        ("site_light(?L)", "light_ok_for(?L, ?S)"),
        "light_ok(?S)",
        "The light a plant tolerates must not exceed the light of the site: "
        "a full-sun plant cannot survive in full shade.  The fact "
        "light_ok_for(L, S) holds when the plant survives in a site of "
        "light class L.",
    ),
    Clause(
        "moisture-compatibility",
        ("site_moisture(?M)", "moisture_ok_for(?M, ?S)"),
        "moisture_ok(?S)",
        "The soil moisture band of the plant must match the band of the site.",
    ),
    Clause(
        "strict-candidate",
        ("light_ok(?S)", "moisture_ok(?S)", "!forbidden(?S)"),
        "candidate_l0(?S)",
        "Level 0: the plant satisfies every constraint at once.",
    ),
    Clause(
        "relaxed-moisture-candidate",
        ("light_ok(?S)", "!forbidden(?S)"),
        "candidate_l1(?S)",
        "Level 1: the moisture constraint has been relaxed.",
    ),
    Clause(
        "relaxed-all-candidate",
        ("!forbidden(?S)"),
        "candidate_l2(?S)",
        "Level 2: only the pet-safety constraint still applies.",
    ),
)


def _light_classes() -> list[str]:
    return list(LIGHT_COMPATIBILITY.keys())


def _moisture_classes() -> list[str]:
    return list(MOISTURE_COMPATIBILITY.keys())


@dataclass
class KnowledgeBase:
    """Facts + clauses, and the forward-chaining engine over them."""

    clauses: tuple[Clause, ...] = CLAUSES
    facts: set[Fact] = field(default_factory=set)
    derived: set[Fact] = field(default_factory=set)
    trace: list[dict[str, Any]] = field(default_factory=list)

    # -- facts -------------------------------------------------------------
    def add_fact(self, predicate: str, *args: str) -> None:
        self.facts.add(Fact(predicate, tuple(args)))

    # -- inference ---------------------------------------------------------
    def forward_chain(self) -> list[dict[str, Any]]:
        """Run forward chaining to a fixpoint; return the firing trace.

        Agenda algorithm: repeatedly pick a rule whose premises are all
        known, fire it, and add its conclusion.  A rule fires at most once
        per ground instance, so the whole run is linear in the number of
        derivations.
        """
        self.derived = set(self.facts)
        self.trace = []
        changed = True
        while changed:
            changed = False
            for clause in self.clauses:
                for binding in self._match(clause.premises, {}):
                    conclusion = self._ground(clause.conclusion, binding)
                    if conclusion in self.derived:
                        continue
                    self.derived.add(conclusion)
                    changed = True
                    self.trace.append({
                        "rule": clause.rule_id,
                        "comment": clause.comment,
                        "conclusion": str(conclusion),
                        "binding": {k: v for k, v in binding.items()},
                    })
        return self.trace

    # -- helpers -----------------------------------------------------------
    def _match(self, premises: Iterable[str],
               binding: dict[str, str]) -> list[dict[str, str]]:
        """All bindings that satisfy the premises (a simple unifier).

        A premise may be negated (``!forbidden(?S)``).  A negated premise
        holds when the corresponding fact is *absent* from the knowledge
        base -- negation as failure.  The negation is stratified: the
        predicate it refers to is derived by earlier rules, never later.
        """
        premises = list(premises)
        if not premises:
            return [dict(binding)]
        head, args = _parse(premises[0])
        negated = head.startswith("!")
        if negated:
            head = head[1:]

        # A negative premise whose variables are all bound already is just
        # a membership test.
        if negated and all(a[1:] in binding for a in args if a.startswith("?")):
            fact = self._ground_args(head, args, binding)
            if fact in self.derived:
                return []
            return self._match(premises[1:], binding)

        # Otherwise the candidates come from the facts of that predicate
        # (for a negative premise: from the domain of species).
        pool = (self.facts_of("species") if negated
                else [f for f in self.derived if f.predicate == head])
        results: list[dict[str, str]] = []
        for fact in pool:
            if not negated and fact.predicate != head:
                continue
            if len(fact.args) != len(args):
                continue
            local = dict(binding)
            ok = True
            for pattern, value in zip(args, fact.args):
                if pattern.startswith("?"):
                    name = pattern[1:]
                    if local.get(name, value) != value:
                        ok = False
                        break
                    local[name] = value
                elif pattern != value:
                    ok = False
                    break
            if not ok:
                continue
            if negated:
                if self._ground_args(head, args, local) in self.derived:
                    continue
            results.extend(self._match(premises[1:], local))
        return results

    def _ground(self, text: str, binding: dict[str, str]) -> Fact:
        name, args = _parse(text)
        return Fact(name, tuple(binding.get(a[1:], a) for a in args))

    def _ground_args(self, name: str, args: tuple[str, ...],
                     binding: dict[str, str]) -> Fact:
        return Fact(name, tuple(
            binding.get(a[1:], a) if a.startswith("?") else a for a in args))

    def facts_of(self, predicate: str) -> set[Fact]:
        return {f for f in self.derived if f.predicate == predicate}

    def species_of(self, predicate: str) -> set[str]:
        return {f.args[0] for f in self.facts_of(predicate) if f.args}


# --------------------------------------------------------------------------
# Building the knowledge base for one scenario
# --------------------------------------------------------------------------

def build_kb(records, pets: Iterable[str], light: str,
             moisture: str) -> KnowledgeBase:
    """Load the database and the site into a knowledge base.

    ``records`` are ``PlantRecord`` objects; the toxicity facts come from
    the verified database, the light/moisture compatibility facts from the
    same tables the production filter uses.
    """
    kb = KnowledgeBase()
    pets = [p.lower() for p in pets if p]
    for pet in pets:
        kb.add_fact("pet_present", pet)
    kb.add_fact("site_light", light)
    kb.add_fact("site_moisture", moisture)

    for rec in records:
        name = rec.common_name or rec.scientific_name
        kb.add_fact("species", name)
        kb.add_fact("light_class", name, rec.light)
        kb.add_fact("moisture_class", name, rec.moisture)
        if rec.toxic_to_cats:
            kb.add_fact("toxic_to_cat", name)
        if rec.toxic_to_dogs:
            kb.add_fact("toxic_to_dog", name)
        # The plant tolerates its own light class and every darker one.
        for site_light, allowed in LIGHT_COMPATIBILITY.items():
            if rec.light in allowed:
                kb.add_fact("light_ok_for", site_light, name)
        for site_moisture, allowed in MOISTURE_COMPATIBILITY.items():
            if rec.moisture in allowed:
                kb.add_fact("moisture_ok_for", site_moisture, name)
    return kb


def admissible_sets(kb: KnowledgeBase) -> dict[int, set[str]]:
    """The candidate sets of the three relaxation levels."""
    kb.forward_chain()
    return {level: kb.species_of(f"candidate_l{level}") for level in (0, 1, 2)}


def kb_decide(kb: KnowledgeBase) -> dict[str, Any]:
    """Run the knowledge base and apply the relaxation ladder.

    The ladder is a *policy*, not a rule of the knowledge base: it decides
    which of the three derived sets is used.  The pet-safety constraint is
    never relaxed -- it is encoded in the rules themselves, so no policy
    choice can remove it.
    """
    sets = admissible_sets(kb)
    level = 0
    for candidate_level in (0, 1, 2):
        if sets[candidate_level]:
            level = candidate_level
            break
    return {
        "level": level,
        "candidates": sets[level],
        "all_levels": sets,
        "forbidden": kb.species_of("forbidden"),
        "trace": kb.trace,
    }
