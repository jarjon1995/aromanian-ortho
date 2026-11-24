#!/usr/bin/env python3
"""Cross-standard search for Aromanian (ISO 639-3: rup) text.

Aromanian print is split between two Latin writing systems: the traditional /
DIARO one (a diacritic per extra sound: a-breve, s-comma, t-comma, l-apex,
n-apex, d-comma) and Cunia (no diacritics except a-tilde: sh ts lj nj z). A
dictionary, a corpus or a Wikipedia article written in one system cannot be
found by a query written in the other.

This tool folds BOTH Latin systems onto one key - the Cunia form, using the
rule table in rup_ortho.py - and searches a corpus with a query in either
standard. Fold first, then tokenise: the traditional system uses combining
marks, which Python's \\w drops, so tokenising first would silently lose them.

Offline after the first run: the parallel corpus of github.com/senisioi/aromanian
(Petrariu & Nisioi, LREC-COLING 2024; GPL-3.0) is cached in rup/data/.

Greek-script Aromanian is NOT folded and is reported as unsupported rather than
searched wrongly.
"""
import json
import os
import re
import sys
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from rup_ortho import to_cunia  # noqa: E402
import rup_greek as RG  # noqa: E402

DATA = os.path.join(HERE, "data")
ZIP = os.path.join(DATA, "dataset.zip")
API = "https://api.github.com/repos/senisioi/aromanian/contents/dataset.zip"
MEMBERS = {
    "std": "dataset/unsplit/corpus.rup_std",         # traditional / DIARO
    "cun": "dataset/unsplit/corpus.rup_cun",         # Cunia
    "ron": "dataset/unsplit/corpus.ro",              # Romanian (pivot language)
    "grk": "dataset/unsplit/corpus.rup.rup_greek",   # Greek-script Aromanian
    "cun2": "dataset/unsplit/corpus.rup.rup_cunia",  # aligned with grk/std2
    "std2": "dataset/unsplit/corpus.rup.rup_std",    # aligned with grk/cun2
}
# letters of the Latin standards INCLUDING combining marks, so a token keeps its
# s-comma / d-comma information instead of having it silently dropped
TOK = re.compile(r"[A-Za-z\u00C0-\u02FF\u0300-\u036f]+")
TRAD_MARKS = set("ăâîșțľńĽȘȚÎĂ̦")


def is_traditional(text):
    return any(c in TRAD_MARKS for c in text)


def fold(text):
    """Canonical search key: both Latin standards map to the Cunia spelling."""
    return to_cunia(text)


def tokens(text):
    """Raw surface tokens, diacritics and combining marks intact."""
    return [t.strip("'’-").lower() for t in TOK.findall(text) if t.strip("'’-")]


def words(text):
    """Folded tokens: the searchable key form."""
    return [fold(t) for t in tokens(text)]


def pkeys(text):
    """Phoneme keys: one key for all three scripts, Greek included.

    Coarser than `words` on purpose. b/v, the palatal affricate series and h are
    merged, so a cross-script query returns a wider hit list rather than a wrong hit.
    This is the only key under which Greek-script text is searchable at all.
    """
    if RG.is_greek(text):
        return [RG.gkey(t) for t in RG.GTOK.findall(text)]
    return [RG.lkey(t) for t in RG.LTOK.findall(text)]


def ensure_corpus():
    if not os.path.exists(ZIP):
        os.makedirs(DATA, exist_ok=True)
        req = urllib.request.Request(API, headers={"Accept": "application/vnd.github.raw"})
        with urllib.request.urlopen(req, timeout=180) as r, open(ZIP, "wb") as f:
            f.write(r.read())
    zf = zipfile.ZipFile(ZIP)
    out = {}
    for k, name in MEMBERS.items():
        try:
            out[k] = zf.read(name).decode("utf-8").splitlines()
        except KeyError:
            out[k] = []
    return out


class Index:
    def __init__(self, docs, key=words):
        self.docs = docs
        self.key = key
        self.post = {}
        for i, d in enumerate(docs):
            for w in set(key(d)):
                self.post.setdefault(w, set()).add(i)

    def search(self, query):
        qs = set(self.key(query))
        if not qs:
            return []
        ids = None
        for w in qs:
            p = self.post.get(w)
            if not p:
                return []
            ids = p if ids is None else (ids & p)
            if not ids:
                return []
        return sorted(ids)

    def rank(self, query, limit=10):
        """Score by key overlap. Used when query and corpus are in different scripts:
        the phoneme key agrees on about two thirds of words across scripts, so requiring
        every query word to match would return nothing. Returns [(score, line_no)]."""
        qs = set(self.key(query))
        if not qs:
            return []
        hits = {}
        for w in qs:
            for i in self.post.get(w, ()):
                hits[i] = hits.get(i, 0) + 1
        if not hits:
            return []
        # containment: share of the QUERY's keys present in the line, so a fragment of a
        # sentence still finds that sentence; jaccard only as a small tiebreak
        out = []
        for i, inter in hits.items():
            d = set(self.key(self.docs[i]))
            out.append((inter / len(qs) + 0.01 * inter / (len(qs) + len(d) - inter), i))
        out.sort(reverse=True)
        return [(round(s, 4), i + 1) for s, i in out[:limit]]


def selftest():
    c = ensure_corpus()
    std, cun = c["std"], c["cun"]
    pairs = list(zip(std, cun))
    idx_cun, idx_std = Index(cun), Index(std)

    # 1. whole-line search across standards: query in one standard, find the same
    #    sentence written in the other (query and index are different standards)
    hit_c = sum(1 for i, (a, _) in enumerate(pairs) if i in idx_cun.search(a))
    hit_s = sum(1 for i, (_, b) in enumerate(pairs) if i in idx_std.search(b))

    # 2. the value demonstration: a single surface word queried as written.
    #    naive = plain substring search, no folding; folded = this tool.
    def baseline(queries, corpus, idx):
        n = naive = good = 0
        widths = []
        for i, q in queries:
            if not q:
                continue
            n += 1
            if any(q in line for line in corpus):
                naive += 1
            hits = idx.search(q)
            if hits:
                good += 1
                widths.append(len(hits))
        return {"queries": n, "naive_substring_hits": naive,
                "folded_hits": good,
                "pct_naive": round(100.0 * naive / n, 2),
                "pct_folded": round(100.0 * good / n, 2),
                "mean_lines_per_hit": round(sum(widths) / len(widths), 2) if widths else None,
                "unique_hit_pct": round(100.0 * sum(1 for w in widths if w == 1) / len(widths), 2) if widths else None}

    q_trad = [(i, max((t for t in tokens(a) if len(t) >= 5), key=len, default=""))
              for i, (a, _) in enumerate(pairs)]
    q_cun = [(i, max((t for t in tokens(b) if len(t) >= 5), key=len, default=""))
             for i, (_, b) in enumerate(pairs)]

    # 3. how lossy the fold is: distinct SURFACE traditional forms per key
    key2trad = {}
    for a, _ in pairs:
        for t in tokens(a):
            key2trad.setdefault(fold(t), set()).add(t)
    amb = {k: v for k, v in key2trad.items() if len(v) > 1}

    return {
        "lines_aligned": len(pairs),
        "cross_std_line_trad_query_on_cunia_index": {"found": hit_c, "of": len(pairs),
                                                     "pct": round(100.0 * hit_c / len(pairs), 2)},
        "cross_std_line_cunia_query_on_trad_index": {"found": hit_s, "of": len(pairs),
                                                     "pct": round(100.0 * hit_s / len(pairs), 2)},
        "single_word_traditional_query_on_cunia_corpus": baseline(q_trad, cun, idx_cun),
        "single_word_cunia_query_on_traditional_corpus": baseline(q_cun, std, idx_std),
        "fold_ambiguity": {
            "distinct_folded_keys": len(key2trad),
            "keys_from_more_than_one_traditional_spelling": len(amb),
            "pct_ambiguous": round(100.0 * len(amb) / len(key2trad), 2),
            "max_spellings_per_key": max(len(v) for v in key2trad.values()),
            "examples": {k: sorted(amb[k]) for k, _ in sorted(
                ((k, len(v)) for k, v in amb.items()), key=lambda x: -x[1])[:5]},
            "note": "ă, î and â all fold to ã, so a Cunia key can come from several "
                    "traditional spellings; the reverse direction is not recoverable."},
        "greek_script": RG.selftest(c),
        "note_alignment": "the grk/cun2/std2 family is 2111 lines and line-aligned; the "
                          "std/cun/ron files are 2115 and NOT aligned with it, so Greek "
                          "is only ever scored against cun2/std2",
    }


def main(argv):
    raw = "\n".join(argv[1:]) if len(argv) > 1 else sys.stdin.read()
    try:
        arg = json.loads(raw)
    except ValueError:
        arg = {"query": raw.strip()}
    if arg.get("selftest"):
        sys.stdout.write(json.dumps(selftest(), ensure_ascii=False))
        return 0
    c = ensure_corpus()
    corpus = arg.get("corpus", "cun")
    docs = c.get(corpus, [])
    if not docs:
        sys.stdout.write(json.dumps({"error": "no_such_corpus", "known": sorted(MEMBERS)}))
        return 0
    limit = int(arg.get("limit", 10))
    q = arg.get("query", "")
    q_greek = RG.is_greek(q)
    c_greek = corpus == "grk"
    if q_greek != c_greek:
        # different scripts: rank on the phoneme key, report the score honestly
        ranked = Index(docs, pkeys).rank(q, limit)
        out = {
            "corpus": corpus, "query": q, "mode": "phoneme_ranked_cross_script",
            "query_script": "greek" if q_greek else "latin",
            "matches": len(ranked),
            "hits": [{"score": s, "line_no": ln, "text": docs[ln - 1]} for s, ln in ranked],
            "note": "Greek-script Aromanian is a phonetic rendering, so cross-script "
                    "search ranks by phoneme overlap; scores near 1.0 are the same sentence",
        }
    else:
        hits = Index(docs).search(q)
        out = {
            "corpus": corpus,
            "query": q,
            "query_standard": "traditional" if is_traditional(q) else "cunia-or-plain",
            "folded_query": fold(q),
            "matches": len(hits),
            "hits": [{"line_no": i + 1,
                      "standard": "traditional" if is_traditional(docs[i]) else "cunia",
                      "text": docs[i]} for i in hits[:limit]],
        }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
