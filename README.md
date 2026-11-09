# PapyGreek–LiGre: the PapyGreek Treebanks linked to the LiGre Lemma Bank

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24089052.svg)](https://doi.org/10.5281/zenodo.24089052)
[![Data: CC BY-SA 4.0](https://img.shields.io/badge/data-CC%20BY--SA%204.0-lightgrey.svg)](LICENSE-DATA.md)
[![Code: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)

This repository contains the triples linking the [PapyGreek treebanks](https://github.com/papygreek/papygreek-treebanks) to the [LiGre Lemma Bank](https://github.com/ligre-lod/ligre_lemmabank) for Ancient Greek.

The PapyGreek treebanks consist of 558 documentary papyri written in Postclassical Greek (ca. 300 BCE–700 CE), morphosyntactically annotated by the [Digital Grammar of Greek Documentary Papyri](https://papygreek.com/) project. Every word occurrence is published as a token and linked to its lemma in the LiGre Lemma Bank, following the model of the corpora in the [LiLa Knowledge Base](https://lila-erc.eu/) (for example [LASLA](https://github.com/CIRCSE/LASLA)).

## At a glance

| | |
|---|---|
| Corpus IRI | <https://w3id.org/ligre/data/corpora/PapyGreek/id/corpus> |
| Source | [PapyGreek Treebanks v3.0](https://doi.org/10.5281/zenodo.8428823) (Vierros et al. 2023) |
| Data dump | [`ttl/complete_papygreek.ttl.gz`](ttl/complete_papygreek.ttl.gz) (Turtle, gzip) |
| VoID/DCAT description | [`ttl/PapyGreek_corpus.ttl`](ttl/PapyGreek_corpus.ttl); whole knowledge base: <https://ligre-lod.github.io/.well-known/void> |
| Linked to | [LiGre Lemma Bank](https://github.com/ligre-lod/ligre_lemmabank) (`lilaOntology:hasLemma`; the release pinned in `papygreek_to_ligre/settings.py`) |
| Vocabularies | POWLA, LiLa ontology and LiLa corpus ontology, Dublin Core, RDFS |
| Licence | Data [CC BY-SA 4.0](LICENSE-DATA.md); code [MIT](LICENSE) |
| Archived releases | Zenodo: <https://doi.org/10.5281/zenodo.24089052> (all versions), with a DOI per release (see [Versioning and releases](#versioning-and-releases)) |

The corpus is part of the LiGre Knowledge Base
(<https://w3id.org/ligre/data/id/KnowledgeBase>), together with the
LiGre Lemma Bank.

## Data files

- `ttl/texts/` gets one Turtle file for each papyrus when you run the pipeline (not in the repository; the same data is in `ttl/complete_papygreek.ttl.gz`)
- `ttl/PapyGreek_corpus.ttl` describes the corpus
- `ttl/complete_papygreek.ttl.gz` provides one Turtle file containing the whole corpus
- `review/` holds the hand-made part-of-speech decisions used for linking (`decisions_*.tsv`) and the review files every run writes to make them (`review_*.tsv`; only `review_summary.tsv` is tracked; see *Linking workflow*)
- `ttl/paper_subset.ttl` is a subset of the corpus made with `queries/loanwords/paper_subset.rq`
- `queries/examples/` holds example SPARQL queries (see *Example queries*); the queries in `queries/loanwords/` combine the corpus with other resources (IGVLL, CLaSSES) and are run with `scripts/run_query.py`
- `LICENSE`, `LICENSE-DATA.md`, `CITATION.cff` and `.zenodo.json` hold the licences and the citation and archiving metadata; `CHANGELOG.md` and `RELEASING.md` the changes per release and the release procedure

## Data model

Each papyrus is a `powla:Document` in the corpus `https://w3id.org/ligre/data/corpora/PapyGreek/id/corpus`. It has two citation structures (`lila_corpus:CitationStructure`):

- `CiteStructure`, dividing the text into parts (`Pars`) and lines (`Linea`). PapyGreek does not record sides or columns, so a new part starts wherever the line numbering restarts.
- `SentenceLayer`, dividing the text into sentences (`Sentence`).

Each word is a `powla:Terminal` with its form as written on the papyrus (`powla:hasStringValue`, PapyGreek's `orig_form`) and, where possible, a link to its lemma (`lilaOntology:hasLemma`). The lemma is PapyGreek's regularized lemma, so a misspelled form still links to its standard lemma. Elliptic tokens added during syntactic annotation are not included.

A lemma is linked when its written form and part of speech match exactly one lemma in the LiGre Lemma Bank, or when a part-of-speech difference was resolved by hand (see *Linking workflow*).

## Statistics

From the VoID description and `review/review_summary.tsv`:

| | |
|---|---|
| Triples (VoID) | 779,125 |
| Documents (`powla:Document`) | 558 |
| Tokens (`powla:Terminal`) | 63,628, of which 6,905 punctuation marks |
| Parts / lines / sentences | 655 / 10,589 / 4,557 |
| Tokens considered for linking (Greek words with a PapyGreek lemma) | 54,969 |
| Tokens linked to a LiGre lemma | 44,511 (81.0% of the tokens considered) |
| Distinct LiGre lemmas linked | 3,173 |

| Linking step | Tokens | Linked |
|---|---|---|
| 0. Not a word (gaps, placeholders) | 40 | 0 |
| 1. Strict automatic match | 31,841 | 31,841 |
| 2. Part-of-speech clashes, decided by hand | 13,973 | 12,670 |
| 3. Lemma not in LiGre | 9,115 | 0 |

Tokens are linked only through steps 1 and 2; lemmas missing from LiGre are not linked. LiGre 0.1.0 publishes its
lemma list without corrections, so several frequent function words that it tags as nouns (the article
ὁ, ἐν, οὗτος, ὅς, ὡς) link through a `ligre-pos-wrong` decision in step 2 instead of a strict match.

## Example queries

The queries in [`queries/examples/`](queries/examples) run on the data dump (and, for the written form of
the lemmas, on the LiGre Lemma Bank dump as well) in any SPARQL store, or with `scripts/run_query.py`,
which needs [pyoxigraph](https://pypi.org/project/pyoxigraph/) (`pip install pyoxigraph`):

```bash
python scripts/run_query.py queries/examples/01_documents_and_coverage.rq --data ttl/complete_papygreek.ttl.gz
python scripts/run_query.py queries/examples/02_most_frequent_lemmas.rq --data ttl/complete_papygreek.ttl.gz data/ligre_lemmabank.ttl
```

| Query | What it returns |
|---|---|
| [`01_documents_and_coverage.rq`](queries/examples/01_documents_and_coverage.rq) | Documents with their Trismegistos number, number of tokens and share of linked tokens. |
| [`02_most_frequent_lemmas.rq`](queries/examples/02_most_frequent_lemmas.rq) | The most frequent LiGre lemmas in the corpus. |
| [`03_occurrences_of_a_lemma.rq`](queries/examples/03_occurrences_of_a_lemma.rq) | Every occurrence of a lemma (ἀρτάβη) with its form, document and line. |
| [`04_unlinked_forms.rq`](queries/examples/04_unlinked_forms.rq) | The most frequent forms of unlinked tokens. |
| [`05_dataset_description.rq`](queries/examples/05_dataset_description.rq) | The VoID statistics of the corpus and of its links to LiGre. |

## Quality and known limitations

- 19.0% of the tokens considered for linking have no lemma link: mostly lemmas missing from LiGre
  (9,115 tokens; about 70% of these lemmas are personal and place names, many others alphabetic numerals
  such as β or ιθ) and part-of-speech clashes
  that were rejected or are not decided yet (homographs). Every unlinked token stays in the corpus.
  `review/review_summary.tsv` and the `review_*.tsv` files list them.
- Some frequent words are unlinked because their lemma is missing from LiGre, e.g. the personal
  pronoun σύ (`σοι`, `σε`); see `queries/examples/04_unlinked_forms.rq`.
- Token strings are PapyGreek's original forms, including editorial signs (`(ἀρταβῶν)`, `<ἀρτάβας>`).
- Elliptic tokens added during syntactic annotation are not included, and the syntactic annotation
  (heads, relations) and the morphological tags of PapyGreek are not (yet) published as RDF.
- The corpus is published as a data dump. Its corpus IRI resolves through the LiGre endpoint
  (dataset description only); the IRIs of the documents and tokens do not resolve yet.

## Linking workflow

Every token goes through these steps; `review/review_summary.tsv` counts the tokens and the distinct lemmas per step. All files are in `review/`: the `review_*.tsv` files are rewritten by every run, the `decisions_*.tsv` files are edited by hand.

0. **Not a word.** Tokens that PapyGreek marks in the lemma field as no identifiable word are left unlinked: a lost or partly lost word (`|gap:…|` or `G` in the lemma, the placeholder lemma `γ` on an untagged token), a blank space (`|vac:…|`), an unresolved abbreviation (lemma ending in `…`) or a placeholder (`TO_ADD`, a part-of-speech tag in the lemma field). Each token is counted under the marker that excluded it: `review_summary.tsv` gives the tokens per marker and `review_not_a_word.tsv` lists every token with its marker. The rules are in `linking/not_a_word.py`.
1. **Strict match.** The PapyGreek lemma and part of speech match exactly one LiGre lemma. PapyGreek's AGDT tags are compared to LiGre's Universal Dependencies tags through `STRICT_UNIVERSAL_TAGS_BY_PAPYGREEK_POS` in `linking/pos_tags.py`. When a noun matches several LiGre lemmas, its gender picks the one with the same gender (LiGre has a masculine and a feminine λίψ).
2. **Part-of-speech clashes.** The lemma exists in LiGre, but only with another part of speech. These tokens stay unlinked until they are decided by hand:
   - `review_lemmas.tsv` lists every clashing lemma with its LiGre lemma ids, undecided ones first and then the most frequent.
   - Decide each lemma in `decisions_lemmas.tsv` (`lemma`, `papygreek_pos`, `ligre_pos`, `decision`, `ligre_lemma`, `note`). A decision is one of `convention` (both tags are defensible), `ligre-pos-wrong`, `papygreek-pos-wrong` (all three link the token) or `reject` (keeps it unlinked). To correct a link by hand, put the id of the right LiGre lemma in `ligre_lemma`, with or without a decision: the token then links to that lemma (for example when PapyGreek's lemma is another word than the LiGre lemma spelled the same way). A lemma with a homograph number (`λίψ1`) applies to that homograph only, one without (`λίψ`) to all of them.
   - **Several LiGre lemmas.** When a lemma matches several LiGre lemmas that gender cannot tell apart, it is listed as `ambiguous`; put the id of the right one in `ligre_lemma` or `reject` it.
   - **Homographs.** PapyGreek numbers homographs (`λέγω1`, `λέγω2`). A numbered lemma that is linked to the only LiGre lemma with its spelling may be another word than PapyGreek's, so it is listed as `check homograph`. It is only linked once it is decided: `same-word` links it, a `ligre_lemma` links it to another LiGre lemma, `reject` keeps it unlinked.
   - Rerun the pipeline: decided lemmas get their status in the review files and link.
3. **Lemmas missing from LiGre** are not linked: their tokens stay in the corpus without a lemma. `review_no_ligre_lemma.tsv` lists these lemmas, the most frequent first. The same holds for the few tokens whose lemma and part of speech match more than one LiGre lemma (`ambiguous`).

## Project components

- `papygreek_to_ligre/` is the conversion pipeline: `sources/` downloads PapyGreek and LiGre and reads the treebanks, `linking/` links the lemmas to LiGre, `rdf/` builds and writes the Turtle files; `settings.py` pins the sources
- `scripts/` holds `generate_release.py` (see [RELEASING.md](RELEASING.md)) and `run_query.py` (see *Example queries*)

## Dataset description

The corpus IRI also describes the corpus as a dataset (`void:Dataset`, `dcat:Dataset`): Dublin Core metadata (title, description, creators, publisher, licence, language, source, dates), a DCAT distribution of `complete_papygreek.ttl.gz`, and VoID statistics counted on every run (triples, entities, class and property partitions) with a `void:Linkset` for the `lilaOntology:hasLemma` links to the LiGre Lemma Bank. The description is in `ttl/PapyGreek_corpus.ttl` and at the end of the complete file; its metadata is set in `papygreek_to_ligre/settings.py` (`CORPUS_*`).

## Local setup

```bash
pip install -r requirements.txt
python -m papygreek_to_ligre
```

Run it from the repository root; installing the package itself is not needed (`pip install .` also works, but leaves `build/` and `*.egg-info/` behind, which git ignores).

The pipeline downloads the PapyGreek Treebanks and the LiGre Lemma Bank into `data/`, in the versions pinned in `papygreek_to_ligre/settings.py` (`PAPYGREEK_VERSION`, `LIGRE_LEMMA_BANK_VERSION`), and writes the Turtle files into `ttl/`. It reads the decisions from and writes the review files into `review/`. Options: `--base-iri`, `--output-dir`, `--data-dir`, `--review-dir`, `--refresh`, `--skip-complete-file`.

## IRIs

All IRIs are minted under `https://w3id.org/ligre/data/corpora/PapyGreek/id/corpus`: a document is
`…/corpus/{PapyGreek document id}`, its citation structures and units are below it
(`…/CiteStructure/Pars_1/Linea_3`, `…/SentenceLayer/Sentence_2`), and a token is
`…/{document id}/{document id}_t_{position}`, its position among the tokens of the document.
The source is pinned to the PapyGreek Treebanks v3.0, so rebuilding the corpus gives the same IRIs.
Linking decisions change only the `lilaOntology:hasLemma` links, never the IRIs.
Lemma IRIs are those of the LiGre Lemma Bank, which are persistent across its releases.

## Versioning and releases

Releases follow [semantic versioning](https://semver.org/) and are tagged `vMAJOR.MINOR.PATCH`. Each
GitHub release is archived on Zenodo through the GitHub integration, with a DOI for the release and a
concept DOI for all releases (metadata in `.zenodo.json`). Changes per release are listed in
[CHANGELOG.md](CHANGELOG.md); the release procedure is in [RELEASING.md](RELEASING.md).

## Sustainability

PapyGreek–LiGre is maintained by Paulien Lemay (Ghent Centre for Digital Humanities, Ghent University)
at least until the end of the maintainer's PhD, expected in 2030. Maintenance is then planned to pass
to the Ghent Centre for Digital Humanities; this plan is not yet final. The IRIs use the
[w3id.org](https://w3id.org/) persistent namespace, and every release is archived on Zenodo. Issues
can be reported through the [GitHub issue tracker](https://github.com/ligre-lod/papygreek/issues).

## Source

The treebanks are created by the PapyGreek project and licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). This corpus is built from the [PapyGreek Treebanks v3.0](https://doi.org/10.5281/zenodo.8428823). The project received funding from the European Research Council (ERC) under the European Union's Horizon 2020 research and innovation programme (grant agreement No 758481).

## Citation

If you use this corpus, cite it with its Zenodo DOI. The concept DOI always resolves to the latest
release; to cite the exact version you used, take the DOI of that release from the Zenodo record:

> Lemay, P. (2026). *PapyGreek–LiGre: the PapyGreek Treebanks as Linked Open Data, linked to the LiGre
> Lemma Bank* [Data set]. Zenodo. https://doi.org/10.5281/zenodo.24089052

| Version | DOI |
|---|---|
| All versions (concept DOI) | <https://doi.org/10.5281/zenodo.24089052> |
| 0.1.0 | <https://doi.org/10.5281/zenodo.24089053> |

Citation metadata is also in [CITATION.cff](CITATION.cff). Please also cite the PapyGreek Treebanks
the corpus is derived from:

> Vierros, M., Henriksson, E., Yordanova, P., Alaranta, A., Lahtinen, P., Vesterinen, J., Huitula, I., & Kock, S. (2023). *PapyGreek Treebanks v3.0*. Zenodo. https://doi.org/10.5281/zenodo.8428823

## Licence

The data (the RDF in `ttl/` and the decisions in `review/`) is derived from the
PapyGreek Treebanks and is licensed under [CC BY-SA 4.0](LICENSE-DATA.md); the code under the
[MIT License](LICENSE).
