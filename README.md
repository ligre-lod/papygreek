# Linking PapyGreek corpus - LiGre Lemma Bank

This repository contains the triples linking the [PapyGreek treebanks](https://github.com/papygreek/papygreek-treebanks) to the [LiGre Lemma Bank](https://github.com/ligre-lod/ligre_lemmabank) for Ancient Greek.

The PapyGreek treebanks consist of 558 documentary papyri written in Postclassical Greek (ca. 300 BCE–700 CE), morphosyntactically annotated by the [Digital Grammar of Greek Documentary Papyri](https://papygreek.com/) project. Every word occurrence is published as a token and linked to its lemma in the LiGre Lemma Bank, following the model of the corpora in the [LiLa Knowledge Base](https://lila-erc.eu/) (for example [LASLA](https://github.com/CIRCSE/LASLA)).

### Repository description

- `ttl/texts/` gets one Turtle file for each papyrus when you run the pipeline (not in the repository; the same data is in `ttl/complete_papygreek.ttl.gz`)
- `ttl/PapyGreek_corpus.ttl` describes the corpus
- `ttl/complete_papygreek.ttl.gz` provides one Turtle file containing the whole corpus
- `pos_review/` holds the hand-made part-of-speech decisions used for linking (`decisions_*.tsv`) and the review files every run writes to make them (`review_*.tsv`; see *Linking workflow*)
- `papygreek_to_ligre/` contains the conversion pipeline: `sources/` downloads and reads the treebanks, `linking/` links the lemmas to LiGre, `rdf/` builds and writes the Turtle files

### Data model

Each papyrus is a `powla:Document` in the corpus `https://w3id.org/ligre/data/corpora/PapyGreek/id/corpus`. It has two citation structures (`lila_corpus:CitationStructure`):

- `CiteStructure`, dividing the text into parts (`Pars`) and lines (`Linea`). PapyGreek does not record sides or columns, so a new part starts wherever the line numbering restarts.
- `SentenceLayer`, dividing the text into sentences (`Sentence`).

Each word is a `powla:Terminal` with its regularized form (`powla:hasStringValue`) and, where possible, a link to its lemma (`lilaOntology:hasLemma`). Elliptic tokens added during syntactic annotation are not included.

A lemma is linked when its written form and part of speech match exactly one lemma in the LiGre Lemma Bank, or when a part-of-speech difference was resolved by hand (see *Linking workflow*).

### Linking workflow

Every token goes through these steps; `pos_review/review_summary.tsv` counts the tokens per step. All files are in `pos_review/`: the `review_*.tsv` files are rewritten by every run, the `decisions_*.tsv` files are edited by hand.

1. **Strict match.** The PapyGreek lemma and part of speech match exactly one LiGre lemma. PapyGreek's AGDT tags are compared to LiGre's Universal Dependencies tags through `STRICT_UNIVERSAL_TAGS_BY_PAPYGREEK_POS` in `linking/pos_tags.py`.
2. **Part-of-speech clashes.** The lemma exists in LiGre, but only with another part of speech. These tokens stay unlinked until they are decided by hand:
   - `review_lemmas.tsv` lists every clashing lemma with its LiGre lemma ids, undecided ones first and then the most frequent.
   - Decide each lemma in `decisions_lemmas.tsv` (`lemma`, `papygreek_pos`, `ligre_pos`, `decision`, `note`). A decision is one of `convention` (both tags are defensible), `ligre-pos-wrong`, `papygreek-pos-wrong` (all three link the token) or `reject` (keeps it unlinked).
   - Rerun the pipeline: decided lemmas get their status in the review files and link.
3. **Lemmas missing from LiGre** are not linked and not reviewed: their tokens stay in the corpus without a lemma. The same holds for the few tokens whose lemma and part of speech match more than one LiGre lemma (`ambiguous`).

### Running the conversion

```bash
pip install -r requirements.txt
python -m papygreek_to_ligre
```

Run it from the repository root; installing the package itself is not needed (`pip install .` also works, but leaves `build/` and `*.egg-info/` behind, which git ignores).

The pipeline downloads the PapyGreek treebanks and the LiGre Lemma Bank into `data/` and writes the Turtle files into `ttl/`. It reads the decisions from and writes the review files into `pos_review/`. Options: `--base-iri`, `--output-dir`, `--data-dir`, `--pos-review-dir`, `--refresh`, `--skip-complete-file`.

### Source

The treebanks are created by the PapyGreek project and licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The project received funding from the European Research Council (ERC) under the European Union's Horizon 2020 research and innovation programme (grant agreement No 758481).

## Copyright

The RDF data in `ttl/` is derived from the PapyGreek treebanks and is licensed under a [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/).
