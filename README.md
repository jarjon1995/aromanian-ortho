# Aromanian across its writing systems (rup)

Aromanian (ISO 639-3 `rup`, ~200,000 speakers) has no single way of writing itself. Its
printed heritage is split between the traditional/DIARO orthography (a diacritic per extra
sound: ă ș ț ľ ń d̦), Cunia (no diacritics except ã: sh ts lj nj z) and a phonetic rendering
in Greek letters. Nothing written in one can be found by a query written in another.

Three dependency-free Python modules:

- `rup_ortho.py` — traditional → Cunia conversion. A 41-rule longest-match table learned from
  the first 1000 aligned corpus lines scores 1115/1115 exact line matches on the untouched
  1115. One-way and lossy: Cunia writes ă, î and â all as ã.
- `rup_greek.py` — a coarse **phoneme key** for all three scripts. Spelling-level
  transliteration of the Greek rendering plateaus around 0.5 word overlap, so it is not the
  right target for search; instead each script folds onto one key and keys are compared.
  Merging b/v, the palatal affricate series and h is deliberate: it widens the hit list
  rather than producing a wrong hit.
- `rup_search.py` — search a corpus with a query in any script. Latin↔Latin is exact
  (inverted index on the Cunia key); anything involving Greek is ranked by how much of the
  query's phoneme key is present in a line.

## Measured, on the line-aligned corpus

Retrieval = does a query built from one line find that line's counterpart among all 2111
lines, scored on the second half only:

| direction | top-1 | top-5 |
|---|---|---|
| Greek → Cunia | 98.0% | 99.0% |
| Cunia → Greek | 97.9% | 99.2% |
| Greek → traditional | 98.5% | 99.3% |
| traditional → Greek | 98.8% | 99.4% |
| baseline: letter-only Greek map, no digraphs | 95.6% | — |

Word-level key agreement between the Greek and Cunia renderings of the same sentence:
85.1% (61,067 aligned words). Latin cross-standard whole-sentence search: 2115/2115. A single
word queried exactly as written is found 100% of the time folded, against 24.7% / 18.7% for a
plain substring search in the other standard. Cost of the lossy fold: 244 of 7837 distinct
keys (3.11%) come from more than one traditional spelling.

## Data

Corpus: `github.com/senisioi/aromanian` (Petrariu & Nisioi, LREC-COLING 2024), **GPL-3.0**.
The `grk` / `rup_cunia` / `rup_std` family is 2111 lines and line-aligned; the `corpus.ro` /
`corpus.rup_std` / `corpus.rup_cun` family is 2115 and is **not** aligned with it, so Greek is
only ever scored against the 2111-line family. `rup_search.py` fetches `dataset.zip` on first
run and caches it in `data/`.
