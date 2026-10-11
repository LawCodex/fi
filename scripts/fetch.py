#!/usr/bin/env python3
"""Download the Finlex open-data bulk archive of consolidated legislation
(Ajantasainen lainsäädäntö / Uppdaterad lagstiftning) and extract the
Akoma Ntoso XML files.

Source: https://www.finlex.fi/fi/avoin-data/lataa-aineistoja
Archive: https://www.finlex.fi/files/open-data/archives/statute-consolidated.zip
(updated daily, ~4 GB, contains XML + PDF + media per statute and language).

Only the XML main documents are extracted (PDF / images are skipped), and
only the most recent consolidated version per statute and language.

Usage: fetch.py [--refresh] [RAW_DIR]   (default: ../../_raw/fi relative to this script)
"""
import os
import re
import subprocess
import sys
import time
import zipfile

URL = "https://www.finlex.fi/files/open-data/archives/statute-consolidated.zip"
UA = "LawCodex/1.0 (+https://github.com/LawCodex)"

HERE = os.path.dirname(os.path.abspath(__file__))
_ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
RAW = os.path.abspath(_ARGS[0] if _ARGS else os.path.join(HERE, "..", "..", "_raw", "fi"))


def download(dest):
    # curl with resume support; retried a few times because the archive is large
    for attempt in range(8):
        r = subprocess.run(["curl", "-sS", "-L", "-C", "-", "--retry", "5", "-A", UA, "-o", dest, URL])
        if r.returncode in (0, 33):  # 33 = range not supported / already complete
            try:
                with zipfile.ZipFile(dest) as z:
                    z.namelist()
                return
            except zipfile.BadZipFile:
                pass
        print(f"download attempt {attempt + 1} failed (rc={r.returncode}), retrying", file=sys.stderr)
        time.sleep(10 * (attempt + 1))
    sys.exit("download failed")


VERSION_RE = re.compile(r"akn/fi/act/statute-consolidated/(\d+)/([^/]+)/([a-z]{3})@([^/]*)/main\.xml$")


def _sort_key(data, version):
    m = re.search(rb'<FRBRdate date="([0-9-]+)" name="dateConsolidated"', data)
    has_content = b'name="contentAbsent"' not in data
    return (has_content, m.group(1).decode() if m else "", version)


def extract(zpath, outdir):
    """Write one XML per statute and language: the most recent temporal
    version that actually carries text (falls back to a stub if none does).
    Output: <outdir>/<year>/<number>/<lang>.xml"""
    cands = {}
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            m = VERSION_RE.match(info.filename)
            if m:
                cands.setdefault(m.groups()[:3], []).append((m.group(4), info))
        n = 0
        for (year, num, lang), lst in sorted(cands.items()):
            if not re.fullmatch(r"[0-9A-Za-z-]+", num):
                continue
            best = None
            for version, info in lst:
                data = z.read(info)
                key = _sort_key(data, version)
                if best is None or key > best[0]:
                    best = (key, data)
            d = os.path.join(outdir, year, num)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, lang + ".xml"), "wb") as f:
                f.write(best[1])
            n += 1
    print(f"extracted {n} XML files into {outdir}")


def main():
    os.makedirs(RAW, exist_ok=True)
    zpath = os.path.join(RAW, "statute-consolidated.zip")
    if not os.path.exists(zpath) or "--refresh" in sys.argv:
        download(zpath)
    extract(zpath, os.path.join(RAW, "xml"))


if __name__ == "__main__":
    main()
