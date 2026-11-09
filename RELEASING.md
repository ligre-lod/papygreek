# Releasing

Each release is a `vMAJOR.MINOR.PATCH` tag on `main`. Pushing the tag creates
the GitHub release, which is archived on Zenodo with a DOI.

The version, release date and DOI are set in one place, `CITATION.cff`, by
`scripts/generate_release.py`; `papygreek_to_ligre/settings.py` and the corpus
description take them from there.

## Release steps

1. **Changelog.** List the changes under `## [Unreleased]` in `CHANGELOG.md`.
2. **LiGre first.** The corpus links to a released LiGre Lemma Bank. Release
   LiGre first if its lemmas changed, and set `LIGRE_LEMMA_BANK_VERSION` in
   `papygreek_to_ligre/settings.py` and the LiGre version under `references`
   in `CITATION.cff` to that release.
3. **Prepare the release:**

   ```bash
   python scripts/generate_release.py prepare 0.1.0
   ```

   This moves the unreleased changes in `CHANGELOG.md` under the new version
   and today's date, sets both in `CITATION.cff`, and rebuilds the corpus
   (`python -m papygreek_to_ligre --refresh`, which downloads the pinned
   PapyGreek and LiGre releases again). Check the linking summary it prints
   and `review/review_summary.tsv`.
4. **Check** that the example queries in `queries/examples/` still run, and
   update the statistics in the README if they changed.
5. **Commit, tag and push:**

   ```bash
   git commit -am "Release 0.1.0"
   git tag -a v0.1.0 -m "PapyGreek–LiGre 0.1.0"
   git push origin main v0.1.0
   ```

   The release workflow (`.github/workflows/release.yaml`) checks that
   `CHANGELOG.md`, `CITATION.cff`, the corpus description and the pinned LiGre
   version agree with the tag, and creates the GitHub release with the
   changelog entry as notes. If they do not match, no release is made: fix the
   metadata, move the tag, and push again.
6. **Knowledge base description.** In the ligre_lemmabank repository,
   regenerate `ttl/ligre_void.ttl` with this release's `ttl/PapyGreek_corpus.ttl`
   (the `scripts/export_ttl.py` commands in its README), so that the knowledge base description and the
   endpoint show the new corpus description.
