# Changelog

All notable changes to PapyGreek–LiGre are listed here. Releases follow
[semantic versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/ligre-lod/papygreek/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/ligre-lod/papygreek/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/ligre-lod/papygreek/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/ligre-lod/papygreek/releases/tag/v0.1.0
