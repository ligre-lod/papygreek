# Releasing

Each release is a `vMAJOR.MINOR.PATCH` tag on `main` with a GitHub release,
archived on Zenodo with a DOI.

## One-time setup

1. Sign in to <https://zenodo.org> with GitHub, open *Settings → GitHub*, and
   switch on `ligre-lod/papygreek`. This needs admin rights on the `ligre-lod`
   organisation.
2. Zenodo takes the metadata from `.zenodo.json` (title, creators, licence,
   keywords, related identifiers). The version is the tag name.

## Release steps

1. **LiGre first.** The corpus links to a released LiGre Lemma Bank. Release
   LiGre first if its lemmas changed, and set `LIGRE_LEMMA_BANK_VERSION` in
   `papygreek_to_ligre/settings.py` to that release.
2. **Version and date.** Set the new version and release date in
   - `papygreek_to_ligre/settings.py`: `CORPUS_VERSION` and `CORPUS_ISSUED`
     (and `CORPUS_DOI`, see below);
   - `CITATION.cff`: `version` and `date-released`;
   - `CHANGELOG.md`: move the changes under the new version and date.
3. **Rebuild the corpus** with the pinned sources:

   ```bash
   python -m papygreek_to_ligre --refresh
   ```

   `--refresh` downloads the pinned PapyGreek and LiGre releases again instead
   of using the copies in `data/`. Check the linking summary it prints and
   `review/review_summary.tsv`.
4. **Check** that the example queries in `queries/examples/` still run, and
   update the statistics in the README if they changed.
5. **Commit, tag and push:**

   ```bash
   git tag -a v1.0.0 -m "PapyGreek–LiGre 1.0.0"
   git push origin main v1.0.0
   ```

6. **GitHub release.** Create a release from the tag (web UI or
   `gh release create v1.0.0 --notes-file …`) with the changelog entry as
   notes. Zenodo archives it and mints the DOIs.
7. **Knowledge base description.** In the ligre_lemmabank repository,
   regenerate `ttl/ligre_void.ttl` with this release's `ttl/PapyGreek_corpus.ttl`
   (see its README), so that the knowledge base description and the endpoint
   show the new corpus description.

## After the first Zenodo release

Zenodo mints the DOIs only when the first release is archived, so release
1.0.0 cannot contain its own DOI. Afterwards:

1. Set the concept DOI (the one for all versions) as `CORPUS_DOI` in
   `papygreek_to_ligre/settings.py`, and add it to the README badge and to
   `CITATION.cff` as `doi`.
2. Rebuild the corpus and release these metadata changes as a patch release
   (1.0.1).
