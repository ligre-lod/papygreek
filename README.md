# Linking PapyGreek corpus - LiGre Lemma Bank

This repository contains the triples linking the [PapyGreek treebanks](https://github.com/papygreek/papygreek-treebanks) to the [LiGre Lemma Bank](https://github.com/ligre-lod/ligre_lemmabank) for Ancient Greek.

The PapyGreek treebanks consist of 558 documentary papyri written in Postclassical Greek (ca. 300 BCE–700 CE), morphosyntactically annotated by the [Digital Grammar of Greek Documentary Papyri](https://papygreek.com/) project. Every word occurrence is published as a token and linked to its lemma in the LiGre Lemma Bank, following the model of the corpora in the [LiLa Knowledge Base](https://lila-erc.eu/) (for example [LASLA](https://github.com/CIRCSE/LASLA)).

### Repository description

- `ttl/texts/` provides one Turtle file for each papyrus
- `ttl/PapyGreek_corpus.ttl` describes the corpus
- `ttl/complete_papygreek.ttl.gz` provides one Turtle file containing the whole corpus
- `ttl/unlinked_lemmas.tsv` lists the lemmas that could not be linked to the LiGre Lemma Bank, with their frequency
- `papygreek_to_ligre/` contains the conversion pipeline

### Data model

Each papyrus is a `powla:Document` in the corpus `https://ligre.ugent.be/data/corpora/PapyGreek/id/corpus`. It has two citation structures (`lila_corpus:CitationStructure`):

- `CiteStructure`, dividing the text into parts (`Pars`) and lines (`Linea`). PapyGreek does not record sides or columns, so a new part starts wherever the line numbering restarts.
- `SentenceLayer`, dividing the text into sentences (`Sentence`).

Each word is a `powla:Terminal` with its regularized form (`powla:hasStringValue`) and, where possible, a link to its lemma (`lilaOntology:hasLemma`). Elliptic tokens added during syntactic annotation are not included.

A lemma is linked when its written form matches exactly one lemma in the LiGre Lemma Bank, or exactly one lemma with a compatible part of speech.

### Running the conversion

```bash
pip install .
python -m papygreek_to_ligre
```

The pipeline downloads the PapyGreek treebanks and the LiGre Lemma Bank into `data/` and writes the Turtle files into `ttl/`. Options: `--base-iri`, `--output-dir`, `--data-dir`, `--refresh`, `--skip-complete-file`.

### Source

The treebanks are created by the PapyGreek project and licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The project received funding from the European Research Council (ERC) under the European Union's Horizon 2020 research and innovation programme (grant agreement No 758481).

## Copyright

The RDF data in `ttl/` is derived from the PapyGreek treebanks and is licensed under a [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/).
