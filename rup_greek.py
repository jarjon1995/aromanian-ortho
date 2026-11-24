#!/usr/bin/env python3
"""Third script layer for Aromanian search: Greek-script rup, folded to a phoneme key.

Why not transliterate Greek to Cunia spelling: the Greek rendering is phonetic and its
conventions differ from Cunia's (Greek sigma for Cunia sh, Greek omicron-upsilon for Cunia
u, kappa where Cunia writes c before a back vowel). Spelling-level recovery plateaus around
0.5 word overlap. So both scripts are folded onto one COARSE phoneme key instead, and keys
are compared. A deliberate merge (b/v, the palatal affricate series, h dropped) widens the
hit list; it does not produce a wrong hit.

Ground truth is free: dataset/unsplit/corpus.rup.rup_greek, .rup_cunia and .rup_std are the
same 2111 sentences, line-aligned. Retrieval is scored by asking whether a query built from
one line finds that line's counterpart in the other script among all 2111.
"""
import re

GREEK = [
    ("ουι", "ui"), ("ου", "u"), ("δζ", "c"), ("αι", "ai"), ("ει", "i"), ("οι", "i"),
    ("γγ", "g"), ("γκ", "g"), ("τζ", "c"), ("τσ", "c"), ("ντ", "d"), ("μπ", "b"),
    ("γι", "i"), ("ξ", "ks"), ("ψ", "ps"), ("α", "a"), ("β", "b"), ("γ", "g"),
    ("δ", "d"), ("ε", "e"), ("ζ", "z"), ("η", "i"), ("θ", "t"), ("ι", "i"),
    ("κ", "c"), ("λ", "l"), ("μ", "m"), ("ν", "n"), ("ο", "o"), ("π", "p"),
    ("ρ", "r"), ("σ", "s"), ("ς", "s"), ("τ", "t"), ("υ", "u"), ("φ", "f"),
    ("χ", ""), ("ω", "o"), ("î", "i"), ("Ñ", "n"), ("x", "ks"), ("ò", "o"),
    ("à", "a"), ("ĭ", "i"),
]
# Latin (Cunia or traditional) onto the same key. Longest match first.
LAT = [
    ("sh", "s"), ("zh", "z"), ("ts", "c"), ("dz", "c"), ("dj", "c"), ("ț", "c"),
    ("ţ", "c"), ("lj", "l"), ("nj", "n"), ("ci", "c"), ("chi", "c"), ("ki", "c"),
    ("ch", "c"), ("gh", "g"), ("ã", "a"), ("â", "a"), ("ă", "a"), ("î", "i"),
    ("ș", "s"), ("ľ", "l"), ("ń", "n"), ("Ľ", "l"), ("Ń", "n"), ("Ș", "s"),
    ("Ț", "c"), ("Ă", "a"), ("Â", "a"), ("Î", "i"), ("γ", "g"), ("v", "b"),
    ("w", "b"), ("h", ""), ("j", "i"), ("y", "i"), ("k", "c"),
]
# naive letter-only Greek map, kept as the baseline to beat
GK_LETTER = [("ου", "u"), ("α", "a"), ("β", "v"), ("γ", "g"), ("δ", "d"), ("ε", "e"),
             ("ζ", "z"), ("η", "i"), ("θ", "t"), ("ι", "i"), ("κ", "k"), ("λ", "l"),
             ("μ", "m"), ("ν", "n"), ("ο", "o"), ("π", "p"), ("ρ", "r"), ("σ", "s"),
             ("ς", "s"), ("τ", "t"), ("υ", "u"), ("φ", "f"), ("χ", "h"), ("ω", "o")]

GTOK = re.compile(r"[Α-Ωα-ω\u0370-\u03FFîÑxòàĭ']+")
LTOK = re.compile(r"[A-Za-z\u00C0-\u02FF\u0300-\u036f']+")


def fold(s, table):
    s = s.lower()
    m = dict(table)
    keys = [t[0] for t in sorted(table, key=lambda t: -len(t[0]))]
    out, i = [], 0
    while i < len(s):
        for k in keys:
            if s.startswith(k, i):
                out.append(m[k])
                i += len(k)
                break
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


GRK_BLOCK = re.compile(r"[\u0370-\u03FF]")


def is_greek(text):
    """Greek letters only. The Latin standards use î, Ñ and x, which are NOT Greek,
    so a token pattern that includes them must not decide the script."""
    return bool(GRK_BLOCK.search(text))


def gkey(w):
    return fold(w, GREEK)


def lkey(w):
    return fold(w, LAT)


def gset(line):
    return {gkey(t) for t in GTOK.findall(line)}


def lset(line):
    return {lkey(t) for t in LTOK.findall(line)}


def jaccard(a, b):
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter) if inter else 0.0


def contain(q, d):
    """Share of the QUERY's keys found in the document. A query may be a fragment of a
    line, so dividing by the document length (jaccard) buries the right answer; this
    ranks by how much of the query is present, with jaccard as tiebreak."""
    inter = len(q & d)
    if not inter:
        return 0.0
    return inter / len(q) + 0.01 * jaccard(q, d)


def retrieve(qsets, tsets, idxs, topk=5):
    """How often the line a query came from is ranked first / in the top k."""
    h1 = h5 = n = 0
    for i in idxs:
        qs = qsets[i]
        if not qs:
            continue
        n += 1
        ranked = sorted(((contain(qs, cs), j) for j, cs in enumerate(tsets) if qs & cs),
                        reverse=True)
        if ranked and ranked[0][1] == i:
            h1 += 1
        if any(j == i for _, j in ranked[:topk]):
            h5 += 1
    return h1, h5, n


def selftest(corpus):
    """corpus: dict with 'grk', 'cun2', 'std2' = the line-aligned 2111-line family."""
    grk, cun, std = corpus["grk"], corpus["cun2"], corpus["std2"]
    gs = [gset(l) for l in grk]
    cs = [lset(l) for l in cun]
    ss = [lset(l) for l in std]
    # score on the second half only; the maps were written from the first half's evidence
    test = list(range(len(grk) // 2, len(grk)))
    out = {"aligned_lines": len(grk), "scored_lines": len(test), "directions": {}}
    for name, q, t in (("greek->cunia", gs, cs), ("cunia->greek", cs, gs),
                       ("greek->traditional", gs, ss), ("traditional->greek", ss, gs)):
        h1, h5, n = retrieve(q, t, test)
        out["directions"][name] = {"top1": h1, "top5": h5, "of": n,
                                   "pct_top1": round(100.0 * h1 / n, 2),
                                   "pct_top5": round(100.0 * h5 / n, 2)}
    # baseline: naive letter-only Greek map, no digraphs
    naive = [{fold(t, GK_LETTER) for t in GTOK.findall(l)} for l in grk]
    h1, h5, n = retrieve(naive, cs, test)
    out["baseline_letter_only_greek_to_cunia"] = {"top1": h1, "of": n,
                                                  "pct_top1": round(100.0 * h1 / n, 2)}
    # word-level agreement of the key between scripts, same aligned line
    ok = tot = 0
    for g, c in zip(grk, cun):
        ga = [gkey(t) for t in GTOK.findall(g)]
        ca = [lkey(t) for t in LTOK.findall(c)]
        if len(ga) != len(ca):
            continue
        for p, q in zip(ga, ca):
            tot += 1
            ok += (p == q)
    out["word_key_agreement_greek_cunia"] = {"same": ok, "of": tot,
                                             "pct": round(100.0 * ok / tot, 2)}
    out["note"] = ("phoneme key, not spelling: b/v, the palatal affricates and h are merged "
                   "on purpose, so cross-script hits are a wider list rather than a wrong one")
    return out
