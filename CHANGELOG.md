# Changelog

All notable changes to PapyGreek–LiGre are listed here. Releases follow
[semantic versioning](https://semver.org/).

## [Unreleased]

### Changed
- `review/decisions_unmatched.tsv` is renamed `review/list_unmatched.tsv`: it is
  a list written by `scripts/list_unmatched.py`, not a decision file that the
  pipeline reads, as in the review folder of igvll.
- The last open part-of-speech conflicts in `review/decisions_ambiguous.tsv`
  are decided: μή, δεύτερος, ξένος1, οὔτε, ὅμως, ἐπίτιμος and Σεβαστός as
  `convention`, εἷς as `papygreek-pos-wrong`. Most of them only became
  conflicts when LiGre corrected the part of speech of these lemmas for their
  more frequent use.
- `linking/not_a_word.py` leaves out a token whose form is a full stop: in
  PapyGreek's regularised layer, the annotation of the word before it has
  slipped onto it (3 tokens, in O.Claud. 2.237 and UPZ 1.43).
- A `PROPN` decided as `new` (or added with `ligre_change` `add`) may be without
  a gender, for indeclinable names such as the Egyptian months, which LiGre
  now accepts; a `NOUN` still needs one.

### Fixed
- `queries/examples/06_loanword_coverage.rq` counted the IGVLL entries with a
  Greek word linked to LiGre in LiLa's copy of the IGVLL–LiGre links, which
  LiLa imported once (1,381 links). It now takes the links from the LiGre
  endpoint through `SERVICE`, like the other counts, so that it follows the
  released linkset (1,456 links in IGVLL–LiGre 0.2.0).

## [0.4.0] - 2026-11-17

### Added
- `review/manual_check.tsv`: the manual check of a random sample of 100
  automatic links (PapyGreek lemma and part of speech to LiGre lemma, 764
  tokens) against their context in the papyri; all 100 are correct.
- 83 decisions in `review/decisions_wr_lv.tsv`: 51 personal names that LiGre
  only has as an adjective (`new`, `PROPN`), 6 middle verbs that LSJ treats as
  the usual form of the verb (`lv`), 23 spelling errors in PapyGreek's lemmas
  (`link`) and 3 spelling variants (`wr`). Their LiGre changes are in
  `ligre_corrections/papygreek-review.tsv`, which now lists only the changes
  that LiGre 0.6.2 does not have yet.

### Changed
- The corpus links to LiGre 0.7.0, which has the lemmas of the 51 names and 6
  middle verbs and the 3 spellings decided in `review/decisions_wr_lv.tsv`, so
  their tokens are now linked. `ligre_corrections/papygreek-review.tsv` is
  empty again: LiGre 0.7.0 has every change of the decision files.

## [0.3.0] - 2026-11-16

### Added
- `scripts/list_unmatched.py` writes `review/decisions_unmatched.tsv`: every PapyGreek
  lemma whose tokens are not linked to LiGre and that is in neither decision file
  (lemmas absent from LiGre and tokens that are not a word), with its tokens,
  forms, example occurrences and LSJ address, so that the gaps can be inspected.

### Changed
- Numbered PapyGreek homographs that link to the only LiGre lemma with their
  spelling without a decision are counted as strict matches instead of as a
  separate step (`homograph linked to the only LiGre lemma`), since no decision
  is involved. The links themselves are unchanged; only the step counts are.
- The loanword queries are now federated queries for the LiLa SPARQL endpoint,
  `queries/examples/06_loanword_coverage.rq` and `07_shared_loanwords.rq`. They
  take the IGVLL–LiGre links and the PapyGreek tokens from the LiGre endpoint
  through `SERVICE`, so they run on the live data, including
  the parts of CLaSSES that are not in its GitHub release.
  `scripts/run_query.py` sends a query to an endpoint with `--endpoint` or runs it
  on Turtle files with `--data`; it no longer builds a local store of all resources.

### Removed
- `queries/loanwords/` and `ttl/paper_subset.ttl`, replaced by the federated
  queries above.

## [0.2.0] - 2026-11-12

### Added
- Columns in `review/decisions_ambiguous.tsv` that record what each decision
  changes in the LiGre Lemma Bank (`ligre_change`: `none`, `correct` or `add`,
  with `ligre_id`, `ligre_new_lemma`, `ligre_new_pos`, `ligre_new_gender`),
  filled in for all decisions. The pipeline checks them; the linking does not
  depend on them.
- Written representations and lemma variants for LiGre: `ligre_change`
  `add-wr` (decision `ligre-spelling-missing`) adds a spelling to a LiGre
  lemma, and the column `ligre_variant_of` makes a lemma to add a lemma
  variant of a LiGre lemma.
- Decisions apply to lemmas missing from LiGre too, and link their tokens.
- The tokens of a lemma that LiGre will add (`ligre_change` `add`) link to it
  as soon as a LiGre release contains it.
- Links to several LiGre lemmas for a crasis (κοὐκ: καί and οὐ).
- `review/decisions_wr_lv.tsv`: the lemmas missing from LiGre that match a
  LiGre lemma once their spelling is normalised (accents and breathings, iota
  subscript, capitalisation, spelling, voice), with the lsj.gr pages of both
  spellings. The pipeline keeps it up to date and keeps the decisions in it:
  `link`, `wr`, `lv`, `correct-ligre` or `new` (`linking/variants.py`,
  `linking/wr_lv_decisions.py`).
- The export leaves out the changes the pinned LiGre release already has
  (corrected, merged and added lemmas, written representations and lemma
  variants), so it can be run again after every LiGre release.
- Decisions keep working after a LiGre release that applies them: a decision
  whose LiGre part of speech LiGre no longer has for that spelling applies to
  the corrected lemma, and a merged lemma's id in an applied change is no
  longer an error.
- Incomplete decisions are skipped with a warning instead of stopping the
  pipeline or the export; an empty `ligre_change` means `none`.
- The export writes written representations (`add-wr`) and lemma variants
  (`add-variant`), the LiGre correction actions added in the lemma bank, and
  reads `decisions_wr_lv.tsv` as well.
- `scripts/export_ligre_corrections.py` writes the LiGre changes in
  `review/decisions_ambiguous.tsv` and `review/decisions_wr_lv.tsv` as a LiGre corrections file,
  `ligre_corrections/papygreek-review.tsv`, ready for a pull request on the
  lemma bank. The first export, 136 corrections, 3 merges and 71 lemmas to
  add, is in LiGre 0.4.0.

### Changed
- `review/decisions_ambiguous.tsv` has no `note` column any more: the
  decision and the LiGre change columns say what is decided.
- `review/decisions_lemmas.tsv` is renamed `review/decisions_ambiguous.tsv`
  and replaces `review/review_lemmas.tsv`: the pipeline adds the open
  ambiguous matches (part-of-speech clashes, several LiGre lemmas,
  homographs) to it, with their status, tokens and LiGre
  candidates. The pipeline writes only the two decision files:
  `review_lemmas.tsv`, `review_summary.tsv`, `review_no_ligre_lemma.tsv` and
  `review_not_a_word.tsv` are no longer written; it logs the linking summary.
- Numbered PapyGreek homographs (`λέγω1`, `λέγω2`) link to the only LiGre lemma
  with their spelling, since LiGre does not distinguish homographs; a decision
  is only needed to link one elsewhere.
- Every decision now links its tokens; the decision `reject` is replaced by
  the reasons `papygreek-lemma-differs`, `papygreek-lemma-wrong`,
  `ligre-lemma-missing` and `crasis`. The former rejects link to an existing
  LiGre lemma (καλῶς, οὕτως, the lemma PapyGreek should have, ...), to the
  LiGre lemma that stays after a merge (ἅμα, δίχα, ἐντός), or to a lemma LiGre
  added (61 -ως adverbs, the particle μήν and a NUM lemma for each letter
  numeral).
- The corpus links to LiGre 0.4.0, which contains the changes from this
  review: 45,869 of the 54,969 tokens considered for linking (83.4%) are
  linked, against 44,511 (81.0%) in 0.1.1.

## [0.1.1] - 2026-11-09

### Added
- The Zenodo concept DOI (10.5281/zenodo.24089052) in the README, `CITATION.cff` and, from this
  release on, as `dcterms:identifier` of the corpus in its dataset description.

## [0.1.0] - 2026-11-09

First release.

### Added
- The PapyGreek Treebanks v3.0 (558 documents) as linked data, modelled after
  the LiLa Knowledge Base corpora (POWLA, LiLa corpus ontology), with two
  citation structures (parts and lines, sentences) per document.
- Links from the tokens to the LiGre Lemma Bank v0.1.0 (`lilaOntology:hasLemma`):
  strict matches and part-of-speech clashes decided by hand
  (`review/decisions_lemmas.tsv`).
- The dataset description of the corpus in Dublin Core, DCAT and VoID, with
  statistics and a linkset to the LiGre Lemma Bank (`ttl/PapyGreek_corpus.ttl`).
- Example SPARQL queries in `queries/examples/`.
- Licences (data CC BY-SA 4.0, code MIT), `CITATION.cff` and `.zenodo.json`
  for archiving releases on Zenodo.
- Pinned sources: the PapyGreek Treebanks release v3.0 and the LiGre Lemma
  Bank release v0.1.0, so that the corpus and its IRIs can be rebuilt exactly.

[Unreleased]: https://github.com/ligre-lod/papygreek/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/ligre-lod/papygreek/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/ligre-lod/papygreek/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/ligre-lod/papygreek/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/ligre-lod/papygreek/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/ligre-lod/papygreek/releases/tag/v0.1.0
