# PapyGreek–LiGre: the PapyGreek Treebanks linked to the LiGre Lemma Bank

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24089052.svg)](https://doi.org/10.5281/zenodo.24089052)
[![Data: CC BY-SA 4.0](https://img.shields.io/badge/data-CC%20BY--SA%204.0-lightgrey.svg)](LICENSE-DATA.md)
[![Code: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)

This repository contains the triples linking the [PapyGreek treebanks](https://github.com/papygreek/papygreek-treebanks) to the [LiGre Lemma Bank](https://github.com/ligre-lod/ligre_lemmabank) for Ancient Greek.

The PapyGreek treebanks consist of documentary papyri written in Postclassical Greek (ca. 300 BCE–700 CE), morphosyntactically annotated by the [Digital Grammar of Greek Documentary Papyri](https://papygreek.com/) project. Every word occurrence is published as a token and linked to its lemma in the LiGre Lemma Bank, following the model of the corpora in the [LiLa Knowledge Base](https://lila-erc.eu/) (for example [LASLA](https://github.com/CIRCSE/LASLA)).

## At a glance

| | |
|---|---|
| Corpus IRI | <https://w3id.org/ligre/data/corpora/PapyGreek/id/corpus> |
| Source | [PapyGreek Treebanks](https://github.com/papygreek/papygreek-treebanks) (Vierros et al.; the release pinned in `papygreek_to_ligre/settings.py`) |
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
- `review/` holds the two decision files used for linking, `decisions_ambiguous.tsv` and `decisions_wr_lv.tsv`, which every run keeps up to date (see *Linking workflow*)
- `ttl/paper_subset.ttl` is a subset of the corpus made with `queries/loanwords/paper_subset.rq`
- `queries/examples/` holds example SPARQL queries (see *Example queries*); the queries in `queries/loanwords/` combine the corpus with other resources (IGVLL, CLaSSES) and are run with `scripts/run_query.py`
- `LICENSE`, `LICENSE-DATA.md`, `CITATION.cff` and `.zenodo.json` hold the licences and the citation and archiving metadata; `CHANGELOG.md` and `RELEASING.md` the changes per release and the release procedure

## Data model

Each papyrus is a `powla:Document` in the corpus `https://w3id.org/ligre/data/corpora/PapyGreek/id/corpus`. It has two citation structures (`lila_corpus:CitationStructure`):

- `CiteStructure`, dividing the text into parts (`Pars`) and lines (`Linea`). PapyGreek does not record sides or columns, so a new part starts wherever the line numbering restarts.
- `SentenceLayer`, dividing the text into sentences (`Sentence`).

Each word is a `powla:Terminal` with its form as written on the papyrus (`powla:hasStringValue`, PapyGreek's `orig_form`) and, where possible, a link to its lemma (`lilaOntology:hasLemma`). The lemma is PapyGreek's regularized lemma, so a misspelled form still links to its standard lemma. Elliptic tokens added during syntactic annotation are not included.

A lemma is linked when its written form and part of speech match exactly one lemma in the LiGre Lemma Bank, or when a part-of-speech difference was resolved by hand (see *Linking workflow*).

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

- Not every token has a lemma link: lemmas missing from LiGre (mostly personal and place names and
  alphabetic numerals such as β or ιθ), matches that are not decided yet, and words that wait for a lemma
  LiGre will add. Every unlinked token stays in the corpus; `review/decisions_ambiguous.tsv` and
  `review/decisions_wr_lv.tsv` list the open cases.
- Homographs share one LiGre lemma. PapyGreek distinguishes homographs (`λέγω1`, `λέγω2`), as LiLa does
  for Latin (two lemmas *malum*, 'apple' and 'evil'), but LiGre has one lemma per spelling, part of speech
  and gender, so all of them link to it. PapyGreek's homograph numbers are not always reliable either
  (μῆλον1 and μῆλον2 are both 'apple'). Distinguishing homographs in LiGre, for example after LSJ's
  (A) and (B) entries, is left for a later release.
- Some frequent words are unlinked because their lemma is missing from LiGre, e.g. the personal
  pronoun σύ (`σοι`, `σε`); see `queries/examples/04_unlinked_forms.rq`.
- Token strings are PapyGreek's original forms, including editorial signs (`(ἀρταβῶν)`, `<ἀρτάβας>`).
- Elliptic tokens added during syntactic annotation are not included, and the syntactic annotation
  (heads, relations) and the morphological tags of PapyGreek are not (yet) published as RDF.
- The corpus is published as a data dump. Its corpus IRI resolves through the LiGre endpoint
  (dataset description only); the IRIs of the documents and tokens do not resolve yet.

## Linking workflow

Every token goes through these steps; the pipeline logs how many tokens end up in each. The pipeline writes only the two decision files in `review/`, `decisions_ambiguous.tsv` and `decisions_wr_lv.tsv`. Every run adds the cases that are still open, keeps everything you filled in, and drops undecided rows that are no longer open; undecided rows come first. The columns after the decision columns are information the pipeline fills in. A row you have not filled in is ignored; a row that is filled in but incomplete or wrong is skipped with a warning (the pipeline and the export name the row and what is missing), so you can decide part of the file and run again.

0. **Not a word.** Tokens that PapyGreek marks in the lemma field as no identifiable word are left unlinked: a lost or partly lost word (`|gap:…|` or `G` in the lemma, the placeholder lemma `γ` on an untagged token), a blank space (`|vac:…|`), an unresolved abbreviation (lemma ending in `…`) or a placeholder (`TO_ADD`, a part-of-speech tag in the lemma field). Each token is counted under the marker that excluded it. The rules are in `linking/not_a_word.py`.
1. **Strict match.** The PapyGreek lemma and part of speech match exactly one LiGre lemma. PapyGreek's AGDT tags are compared to LiGre's Universal Dependencies tags through `STRICT_UNIVERSAL_TAGS_BY_PAPYGREEK_POS` in `linking/pos_tags.py`. When a noun matches several LiGre lemmas, its gender picks the one with the same gender (LiGre has a masculine and a feminine λίψ).
2. **Ambiguous matches** (`decisions_ambiguous.tsv`). The lemma is in LiGre, but the match does not say which LiGre lemma the tokens belong to. Three kinds of matches end up here, each with its `status`:
   - **Part-of-speech clash** (`undecided`): LiGre has the spelling, but only with another part of speech (PapyGreek's adverb καλός, LiGre's adjective καλός). When the LiGre candidates have several parts of speech, `ligre_pos` lists them (`ADJ/NOUN`): keep the one you decide on.
   - **Several LiGre lemmas** (`ambiguous`): the spelling and part of speech match more than one LiGre lemma, and gender cannot tell them apart (θεῖος1: two nouns θεῖος).
   - **Homographs** (`check homograph`): PapyGreek numbers homographs (`λέγω1`, `λέγω2`); LiGre does not distinguish them (it has one lemma per spelling, part of speech and gender). A numbered lemma whose spelling matches only one LiGre lemma links to it without a decision and does not appear here; to link it elsewhere, add a row for the numbered lemma (εὐθύς2, always εὐθέως, to LiGre's adverb εὐθέως).

   The tokens stay unlinked until the row is decided. Every row also shows its `tokens` and its LiGre `candidates` (part of speech and id), the most frequent first.

   **How to decide.** Fill in `decision`, `ligre_lemma` and, if LiGre has to change, the LiGre change columns (see *Submitting the changes to LiGre*) (an empty `ligre_change` means `none`). Every decision links its tokens to a LiGre lemma; `decision` says why: `convention` (both tags are defensible), `ligre-pos-wrong`, `papygreek-pos-wrong`, `same-word` (PapyGreek's numbered homograph is LiGre's word), `papygreek-lemma-differs` (PapyGreek files the word under another lemma, such as an -ως adverb under its adjective), `papygreek-lemma-wrong`, `ligre-lemma-missing` (LiGre will add the lemma), `ligre-spelling-missing` (LiGre will add PapyGreek's spelling as a written representation of a lemma it has) or `crasis` (one token, several words). The tokens link to the LiGre lemma in `ligre_lemma`, or, if it is empty, to the lemma LiGre will add (`ligre_change` `add`) or the lemma that gets the spelling (`add-wr`), or else to the LiGre lemma with PapyGreek's spelling. A crasis gives several ids in `ligre_lemma`, separated by a space (κοὐκ: καί and οὐ), and its token gets a link to each. A lemma with a homograph number (`λίψ1`) applies to that homograph only, one without (`λίψ`) to all of them.
3. **Spelling variants** (`decisions_wr_lv.tsv`). The lemma is not in LiGre as it is spelled, but matches a LiGre lemma once its spelling is normalised. The row is then a PapyGreek spelling error, a spelling LiGre lacks (a written representation, WR), another inflected form of the same word that PapyGreek uses as lemma (a lemma variant, LV), an error in LiGre, or a different word. WR and LV follow Swaelens, Mambrini & Passarotti (2026): a WR differs only in spelling and leaves the inflection unchanged (θάλασσα, θάλαττα); an LV is another inflected form of the same word that can serve as lemma (γράφω, γράφομαι). The tokens stay unlinked until the row is decided.

   The pipeline tries these rules, in this order, and records the first that matches in `rule` (`linking/variants.py`; numerals are left out):

   | `rule` | Example |
   |---|---|
   | accents, breathings or editorial signs (diaeresis, dots under letters) | πρόσδιατρίβω, προσδιατρίβω |
   | iota subscript | χρήζω, χρῄζω |
   | capitalisation | Φίλων, φίλων |
   | spelling: σσ/ττ, ρσ/ρρ, γιν/γιγν, μιγ/μειγ, συν/ξυν | ἀπαλλάττω, ἀπαλλάσσω |
   | voice, for verbs: -ομαι/-ω, -ουμαι/-εω, -αω, -οω | ἀσφαλίζομαι, ἀσφαλίζω |

   Besides the `rule`, it fills in `papygreek_pos`, `tokens`, `candidates` (every matching LiGre lemma with its spelling, part of speech and id), and `lsj_papygreek` and `lsj_ligre`, the addresses of both spellings on [lsj.gr](https://lsj.gr) to check them (whether a page exists is for you to see).

   **How to decide.** The first six columns are yours:

   | Column | Content |
   |---|---|
   | `lemma` | PapyGreek's lemma |
   | `ligre_lemma` | the id of the LiGre lemma the decision is about; prefilled when there is one clear candidate |
   | `decision` | empty (not decided yet) or one of the values below |
   | `new_pos`, `new_gender` | for `new`: the part of speech (`PROPN` for a name) and, for `NOUN` and `PROPN`, the gender (`m`, `f`, `n`); for `lv` and `correct-ligre` only to deviate from the LiGre lemma's |
   | `note` | your note, e.g. the LSJ entry you checked |

   | `decision` | Meaning | What happens |
   |---|---|---|
   | `link` | PapyGreek's spelling is an error (πρόσδιατρίβω) | the tokens link to `ligre_lemma` |
   | `wr` | PapyGreek's spelling is a WR of `ligre_lemma` (ἀπαλλάττω, ἀπαλλάσσω) | LiGre gets the spelling (`add-wr`); the tokens link to `ligre_lemma` |
   | `lv` | PapyGreek's lemma is an LV of `ligre_lemma` (ἀσφαλίζομαι, ἀσφαλίζω) | LiGre gets PapyGreek's lemma as a new lemma, a lemma variant of `ligre_lemma` (`add` and `add-variant`); the tokens link to it once LiGre has it |
   | `correct-ligre` | LiGre's spelling is wrong, PapyGreek's is right | LiGre corrects the spelling of `ligre_lemma` (`correct`); the tokens link to it |
   | `new` | a different word that LiGre lacks, e.g. a name that only matches a common word (Φίλων, φίλων) | LiGre gets PapyGreek's lemma as a new lemma with `new_pos` and `new_gender` (`add`); leave `ligre_lemma` empty |

4. **Lemmas missing from LiGre.** The lemma does not match any LiGre lemma, not even after normalisation: mostly personal and place names and alphabetic numerals. Its tokens stay in the corpus without a lemma and are not listed in a decision file; they link once LiGre has the lemma. To get a lemma into LiGre, add it there with a correction.

A lemma can be decided in only one of the two decision files.

### Submitting the changes to LiGre

The two decision files are the only place where the review records changes to LiGre. In
`decisions_ambiguous.tsv` they are in the LiGre change columns; in `decisions_wr_lv.tsv` the `decision`
stands for them (see the table above).

| `ligre_change` | LiGre gets | Columns |
|---|---|---|
| `none` or empty | no change | – |
| `correct` | a new part of speech, gender or spelling for lemma `ligre_id` (same id and IRI) | `ligre_id`, `ligre_new_pos`, `ligre_new_gender` (`NOUN`, `PROPN`), optionally `ligre_new_lemma` |
| `add` | a new lemma; with `ligre_variant_of`, a lemma variant of that LiGre lemma | `ligre_new_lemma`, `ligre_new_pos`, `ligre_new_gender` (`NOUN`, `PROPN`), optionally `ligre_variant_of` |
| `add-wr` | the spelling `ligre_new_lemma` as an extra written representation of lemma `ligre_id` (decision `ligre-spelling-missing`) | `ligre_id`, `ligre_new_lemma` |

Rows about the same LiGre lemma must give the same change; two lemmas corrected to the same lemma are
merged. Once a LiGre release contains a change, the tokens link without a decision; the export leaves out the
changes the pinned LiGre release already has, so the decision files can stay as they are.

`scripts/export_ligre_corrections.py` writes the complete rows of both files as
`ligre_corrections/papygreek-review.tsv`, in the format of the lemma bank's `data/corrections/` (see its
`data/corrections/README.md`). Copy it into a branch of the lemma bank and run its check:

```bash
uv run python scripts/export_ligre_corrections.py
cp ligre_corrections/papygreek-review.tsv ../ligre-webinterface/ligre_lemmabank/data/corrections/YYYY-MM-DD_papygreek-review.tsv
cd ../ligre-webinterface/ligre_lemmabank && uv run --with rdflib --with pyshacl python scripts/check_corrections.py
```

## Project components

- `papygreek_to_ligre/` is the conversion pipeline: `sources/` downloads PapyGreek and LiGre and reads the treebanks, `linking/` links the lemmas to LiGre, `rdf/` builds and writes the Turtle files; `settings.py` pins the sources
- `scripts/` holds `generate_release.py` (see [RELEASING.md](RELEASING.md)), `run_query.py` (see *Example queries*) and `export_ligre_corrections.py` (see *Submitting the changes to LiGre*)

## Dataset description and statistics

The corpus IRI also describes the corpus as a dataset (`void:Dataset`, `dcat:Dataset`): Dublin Core
metadata, a DCAT distribution of `complete_papygreek.ttl.gz`, and the VoID statistics of the release
(triples, entities, class and property partitions, and a `void:Linkset` for the links to the LiGre Lemma
Bank), counted on every run. It is in [`ttl/PapyGreek_corpus.ttl`](ttl/PapyGreek_corpus.ttl), at the end of
the complete file, and in the description of the whole knowledge base at
<https://ligre-lod.github.io/.well-known/void>; [`05_dataset_description.rq`](queries/examples/05_dataset_description.rq)
reads the statistics. Its metadata is set in `papygreek_to_ligre/settings.py` (`CORPUS_*`). Every pipeline
run also logs how many tokens each linking step links.

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
The source is pinned to one release of the PapyGreek Treebanks (`settings.py`), so rebuilding the corpus gives the same IRIs.
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

The treebanks are created by the PapyGreek project and licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). This corpus is built from the release pinned in `papygreek_to_ligre/settings.py` (`PAPYGREEK_DOI`). The project received funding from the European Research Council (ERC) under the European Union's Horizon 2020 research and innovation programme (grant agreement No 758481).

## Citation

If you use this corpus, cite it with its Zenodo DOI. The concept DOI always resolves to the latest
release; to cite the exact version you used, take the DOI of that release from the Zenodo record.

Citation metadata is also in [CITATION.cff](CITATION.cff), which also gives the reference of the
PapyGreek Treebanks release the corpus is derived from: please cite it as well.

## Licence

The data (the RDF in `ttl/` and the decisions in `review/`) is derived from the
PapyGreek Treebanks and is licensed under [CC BY-SA 4.0](LICENSE-DATA.md); the code under the
[MIT License](LICENSE).
