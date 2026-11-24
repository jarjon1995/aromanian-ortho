#!/usr/bin/env python3
"""Aromanian (ISO 639-3: rup) Latin orthography converter: DIARO/"traditional" -> Cunia.

Aromanian has no single writing standard. The two Latin systems that dominate
modern print are the traditional one (one diacritic per extra sound: ă ș ț ľ ń d̦)
and the Cunia system (no diacritics except ã: sh ts lj nj z). Texts, dictionaries
and corpora are split across them, so anything that wants to search or compare
Aromanian text has to normalise first.

The rule table below was LEARNED from the sentence-aligned corpus of
github.com/senisioi/aromanian (Petrariu & Nisioi, LREC-COLING 2024; GPL-3.0)
using its first 1000 aligned lines, and is frozen here so the converter needs
no corpus and no network at runtime. Measured on the untouched remaining
1115 lines: 1115/1115 exact line matches.

Lossy in one direction only: Cunia writes ă, î and â all as ã, so cunia->traditional
cannot be recovered from spelling alone (135 word-forms collide in the corpus).
"""
import json
import sys

RULES = {
    "̦îț": "zãts",
    "ăță": "ãtsã",
    "̦ăț": "zãts",
    "ățî": "ãtsã",
    "̦îș": "zãsh",
    "îță": "ãtsã",
    "ăăă": "ããã",
    "̦îľ": "zãlj",
    "̦î": "zã",
    "țî": "tsã",
    "ță": "tsã",
    "îľ": "ãlj",
    "îș": "ãsh",
    "ăț": "ãts",
    "̦ă": "zã",
    "ăľ": "ãlj",
    "ăș": "ãsh",
    "îń": "ãnj",
    "țľ": "tslj",
    "îț": "ãts",
    "Îľ": "Ãlj",
    "̦ľ": "zlj",
    "Îș": "Ãsh",
    "șľ": "shlj",
    "ăń": "ãnj",
    "Țî": "Tsã",
    "ńľ": "njlj",
    "șă": "shã",
    "ă": "ã",
    "ș": "sh",
    "î": "ã",
    "ț": "ts",
    "ľ": "lj",
    "ń": "nj",
    "̦": "z",
    "Ș": "Sh",
    "Ț": "Ts",
    "Ľ": "Lj",
    "Î": "Ã",
    "Ă": "Ã",
    "â": "ã"
}

KEYS = sorted(RULES, key=len, reverse=True)


def to_cunia(text):
    out, i = [], 0
    while i < len(text):
        for k in KEYS:
            if text.startswith(k, i):
                out.append(RULES[k]); i += len(k); break
        else:
            out.append(text[i]); i += 1
    return "".join(out)


def main(argv):
    if len(argv) > 1 and argv[1] == "--selftest":
        import io, zipfile, urllib.request
        req = urllib.request.Request(
            "https://api.github.com/repos/senisioi/aromanian/contents/dataset.zip",
            headers={"Accept": "application/vnd.github.raw"})
        zf = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(req, timeout=180).read()))
        std = zf.read("dataset/unsplit/corpus.rup_std").decode("utf-8").splitlines()
        cun = zf.read("dataset/unsplit/corpus.rup_cun").decode("utf-8").splitlines()
        pairs = list(zip(std, cun))[1000:]          # never used for learning
        ok = sum(1 for a, b in pairs if to_cunia(a) == b)
        print(json.dumps({"lines": len(pairs), "exact": ok,
                          "accuracy_pct": round(100.0 * ok / len(pairs), 2)}))
        return 0
    raw = "\n".join(argv[1:]) if len(argv) > 1 else sys.stdin.read()
    try:                                   # own-tool contract: JSON in, JSON out
        arg = json.loads(raw)
        sys.stdout.write(json.dumps({"text": to_cunia(arg["text"])}, ensure_ascii=False))
    except (ValueError, KeyError, TypeError):
        sys.stdout.write(to_cunia(raw))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
