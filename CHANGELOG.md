# Changelog

All notable changes to PapyGreek–LiGre are listed here. Releases follow
[semantic versioning](https://semver.org/).

## [1.0.0] - unreleased

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

### Changed
- The sources are pinned: the PapyGreek Treebanks to release v3.0 (identical to
  its `main` branch at the time) and the LiGre Lemma Bank to release v0.1.0, so
  that the corpus and its IRIs can be rebuilt exactly.

[1.0.0]: https://github.com/ligre-lod/papygreek/releases/tag/v1.0.0
