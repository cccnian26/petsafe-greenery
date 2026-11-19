# Ground-truth database -- provenance and coverage

`data/plants.csv` is the deterministic substrate of the whole project:
the agent's tool filters it, and the evaluator scores every generated
design against it. It is built by three scripts, none of which hand-writes
a label:

| step | script | source | what it provides |
|------|--------|--------|------------------|
| 1 | `scripts/fetch_aspca.py` | ASPCA Animal Poison Control, *Toxic and Non-Toxic Plants* | veterinary toxicity labels for cats and dogs, toxic principles, clinical signs |
| 2 | `scripts/fetch_ncstate.py` | NC State Extension Plant Toolbox | light requirements (and independent `#non-toxic for cats` tags used as a cross-check) |
| 3 | `scripts/build_database.py` | merges 1 + 2 + curated fallbacks | `data/plants.csv` |

## How a row is built

* **Toxicity** comes only from the ASPCA page of that species. A species
  whose ASPCA page carried no explicit `Toxicity:` statement was
  *dropped*, because an unverified label is worse than no label.
* Entries sharing a scientific name are merged into one species and the
  labels are combined conservatively (toxic if any source entry says so).
* **Light** is the most demanding condition NC State lists for the plant
  (`full sun` > `partial shade` > `dappled sunlight` > `deep shade`).
  NC State does not list every species; for those, the curated fallback in
  `data/species_targets.csv` is used and `light_source` says so.
* **Moisture** is a curated horticultural value in all cases -- NC State
  does not publish soil moisture in a machine-readable form.

## Coverage

* total species: **150**
* non-toxic to both cats and dogs: **60**
* toxic to cats: **90**
* toxic to dogs: **82**
* light requirement taken from NC State: **87**

### Light x moisture coverage

```
moisture         high  low  moderate
light                               
bright_indirect     5    4        21
full_shade          7    0        20
full_sun            1    9         5
partial_shade       7   20        51
```

An empty cell means that no species in the database satisfies that
combination strictly. The agent's tool handles this with a documented
constraint-relaxation ladder (the pet-safety filter is never relaxed).

### Species dropped during curation

* not found on the ASPCA list (7): Blue Mist, Fountain Grass, Gladiolus, Ivy Geranium, Money Plant, Papyrus, Sneezeweed

## Cross-check against NC State tags

NC State tags its own pages with `#non-toxic for cats` / `#toxic for cats`.
Where both sources speak about the same species they can be compared;
`scripts/check_database.py` reports the agreement rate.

