# Linking PapyGreek corpus - LiGre Lemma Bank

This repository contains the triples linking the [PapyGreek treebanks](https://github.com/papygreek/papygreek-treebanks) to the [LiGre Lemma Bank](https://github.com/ligre-lod/ligre_lemmabank) for Ancient Greek.

The PapyGreek treebanks consist of 558 documentary papyri written in Postclassical Greek (ca. 300 BCE–700 CE), morphosyntactically annotated by the [Digital Grammar of Greek Documentary Papyri](https://papygreek.com/) project. Every word occurrence is published as a token and linked to its lemma in the LiGre Lemma Bank, following the model of the corpora in the [LiLa Knowledge Base](https://lila-erc.eu/) (for example [LASLA](https://github.com/CIRCSE/LASLA)).

### Repository description

- `ttl/texts/` gets one Turtle file for each papyrus when you run the pipeline (not in the repository; the same data is in `ttl/complete_papygreek.ttl.gz`)
- `ttl/PapyGreek_corpus.ttl` describes the corpus
- `ttl/complete_papygreek.ttl.gz` provides one Turtle file containing the whole corpus
- `review/` holds the hand-made part-of-speech decisions used for linking (`decisions_*.tsv`) and the review files every run writes to make them (`review_*.tsv`, not tracked; see *Linking workflow*)
- `papygreek_to_ligre/` contains the conversion pipeline: `download_papygreek/` downloads and reads the treebanks, `linking/` links the lemmas to LiGre, `rdf/` builds and writes the Turtle files

### Data model

Each papyrus is a `powla:Document` in the corpus `https://w3id.org/ligre/data/corpora/PapyGreek/id/corpus`. It has two citation structures (`lila_corpus:CitationStructure`):

- `CiteStructure`, dividing the text into parts (`Pars`) and lines (`Linea`). PapyGreek does not record sides or columns, so a new part starts wherever the line numbering restarts.
- `SentenceLayer`, dividing the text into sentences (`Sentence`).

Each word is a `powla:Terminal` with its form as written on the papyrus (`powla:hasStringValue`, PapyGreek's `orig_form`) and, where possible, a link to its lemma (`lilaOntology:hasLemma`). The lemma is PapyGreek's regularized lemma, so a misspelled form still links to its standard lemma. Elliptic tokens added during syntactic annotation are not included.

A lemma is linked when its written form and part of speech match exactly one lemma in the LiGre Lemma Bank, or when a part-of-speech difference was resolved by hand (see *Linking workflow*).

### Linking workflow

Every token goes through these steps; `review/review_summary.tsv` counts the tokens and the distinct lemmas per step. All files are in `review/`: the `review_*.tsv` files are rewritten by every run, the `decisions_*.tsv` files are edited by hand.

0. **Not a word.** Tokens that PapyGreek marks in the lemma field as no identifiable word are left unlinked: a lost or partly lost word (`|gap:…|` or `G` in the lemma, the placeholder lemma `γ` on an untagged token), a blank space (`|vac:…|`), an unresolved abbreviation (lemma ending in `…`) or a placeholder (`TO_ADD`, a part-of-speech tag in the lemma field). Lemmas marked as not a word by hand in the annotation viewer (below) are left out in the same way. Each token is counted under the marker that excluded it: `review_summary.tsv` gives the tokens per marker and `review_not_a_word.tsv` lists every token with its marker. The rules are in `linking/not_a_word.py`.
1. **Strict match.** The PapyGreek lemma and part of speech match exactly one LiGre lemma. PapyGreek's AGDT tags are compared to LiGre's Universal Dependencies tags through `STRICT_UNIVERSAL_TAGS_BY_PAPYGREEK_POS` in `linking/pos_tags.py`. When a noun matches several LiGre lemmas, its gender picks the one with the same gender (LiGre has a masculine and a feminine λίψ).
2. **Part-of-speech clashes.** The lemma exists in LiGre, but only with another part of speech. These tokens stay unlinked until they are decided by hand:
   - `review_lemmas.tsv` lists every clashing lemma with its LiGre lemma ids, undecided ones first and then the most frequent.
   - Decide each lemma in `decisions_lemmas.tsv` (`lemma`, `papygreek_pos`, `ligre_pos`, `decision`, `ligre_lemma`, `note`). A decision is one of `convention` (both tags are defensible), `ligre-pos-wrong`, `papygreek-pos-wrong` (all three link the token) or `reject` (keeps it unlinked). To correct a link by hand, put the id of the right LiGre lemma in `ligre_lemma`, with or without a decision: the token then links to that lemma (for example when PapyGreek's lemma is another word than the LiGre lemma spelled the same way). A lemma with a homograph number (`λίψ1`) applies to that homograph only, one without (`λίψ`) to all of them.
   - **Several LiGre lemmas.** When a lemma matches several LiGre lemmas that gender cannot tell apart, it is listed as `ambiguous`; put the id of the right one in `ligre_lemma` or `reject` it.
   - **Homographs.** PapyGreek numbers homographs (`λέγω1`, `λέγω2`). A numbered lemma that is linked to the only LiGre lemma with its spelling may be another word than PapyGreek's, so it is listed as `check homograph`. It is only linked once it is decided: `same-word` links it, a `ligre_lemma` links it to another LiGre lemma, `reject` keeps it unlinked.
   - Rerun the pipeline: decided lemmas get their status in the review files and link.
3. **Lemmas missing from LiGre** are not linked: their tokens stay in the corpus without a lemma. `review_no_ligre_lemma.tsv` lists these lemmas, the most frequent first. The same holds for the few tokens whose lemma and part of speech match more than one LiGre lemma (`ambiguous`).

### Annotating the lemmas missing from LiGre

`annotation_viewer/` is a local web app for checking, in context, every token whose lemma is not in LiGre (step 3 above). It selects the tokens exactly as the pipeline does, so run the pipeline first.

```bash
python -m annotation_viewer                       # then open http://127.0.0.1:8765/
python -m annotation_viewer --fetch-translations  # once: downloads the papyri.info translations into data/translations/
```

You annotate per lemma: a PapyGreek lemma with its PapyGreek part of speech, as listed in `review_no_ligre_lemma.tsv`, the same level at which the other linking decisions are made. The token lemmatization is PapyGreek's. The list is sorted by frequency and can be filtered (not annotated, flagged, near LiGre match, unsure). A lemma is flagged (⚑) when:

- **near LiGre match**: LiGre has a lemma spelled the same apart from accents, breathings or capitals (Σαραπις, LiGre Σάραπις). These are shown above the decision and can be linked with one click; they are never linked automatically, as many are other words (the numeral ιη, LiGre ἰή).
- **PapyGreek variants**: another missing PapyGreek lemma is spelled the same apart from accents, breathings, capitals or part of speech (Σερῆνος / Σερηνος), so the two should get one consistent decision.
- **mixed gender**: a noun whose tokens have more than one gender, which can be a tagging error or two words with one spelling. Check its occurrences one by one.

For each lemma the viewer lists all occurrences with their line. Clicking one shows its papyrus line by line, as divided in the RDF (parts and lines), with the occurrence, the other occurrences of the lemma and its head word marked, and the papyri.info translation next to it when there is one (only a minority of texts have one). Hovering over any word shows its PapyGreek lemma and morphology. You give the lemma and the Universal Dependencies part of speech yourself; no part of speech is preselected, and each tag shows how many LiGre lemmas have it (LiGre has no PROPN lemmas). Choosing a LiGre lemma from the list also stores its id.

A lemma that is no word to link (a gap or placeholder the automatic markers of step 0 miss) is saved with "Not a word" (status `not-a-word`, no lemma or part of speech); the pipeline then leaves its tokens out under the marker `manual`. The top bar counts the tokens left out as not a word; hover over it for the count per marker.

Every save is written at once to `review/annotations_no_ligre_lemma.tsv`, one row per lemma (`papygreek_lemma`, `papygreek_pos`, `tokens`, `lemma`, `pos`, `ligre_lemma`, `status` `checked`, `unsure` or `not-a-word`, `note`, `annotated`). Stopping and restarting the app continues where you left off; the address (`#lemma|pos`) links to a lemma. A file in the earlier one-row-per-token format is converted on start, and the old file is kept as `annotations_no_ligre_lemma.token-level.tsv`. The pipeline only reads the `not-a-word` rows so far; the lemmas and parts of speech are not used for linking yet.

### Running the conversion

```bash
pip install -r requirements.txt
python -m papygreek_to_ligre
```

Run it from the repository root; installing the package itself is not needed (`pip install .` also works, but leaves `build/` and `*.egg-info/` behind, which git ignores).

The pipeline downloads the PapyGreek treebanks and the LiGre Lemma Bank into `data/` and writes the Turtle files into `ttl/`. It reads the decisions from and writes the review files into `review/`. Options: `--base-iri`, `--output-dir`, `--data-dir`, `--review-dir`, `--refresh`, `--skip-complete-file`.

### Source

The treebanks are created by the PapyGreek project and licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The project received funding from the European Research Council (ERC) under the European Union's Horizon 2020 research and innovation programme (grant agreement No 758481).

## Copyright

The RDF data in `ttl/` is derived from the PapyGreek treebanks and is licensed under a [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/).
