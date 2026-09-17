"""Download every provincial EMIS ordinary-school masterlist published by DBE.

Source: https://www.education.gov.za/Programmes/EMIS/EMISDownloads.aspx
No registration or API key. The page lists one file per province per quarter;
each file holds one row per school with that year's learner and educator counts.

Files land in datasets/raw/emis_masterlists/ and are gitignored - they are
re-downloadable source data. Run this to reproduce them.
"""

import os
import re
import html
import json
import time
import urllib.request

PAGE = "https://www.education.gov.za/Programmes/EMIS/EMISDownloads.aspx"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

from src.common.paths import EMIS_RAW as OUT

PROVINCES = {
    "eastern cape": "EC", "free state": "FS", "gauteng": "GP",
    "kwazulu-natal": "KZN", "kwazulu natal": "KZN", "limpopo": "LP",
    "mpumalanga": "MP", "north west": "NW", "northern cape": "NC",
    "western cape": "WC",
}


def get(url, tries=3):
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=240).read()
        except Exception:
            if n == tries - 1:
                raise
            time.sleep(3 * (n + 1))


def discover():
    """Return [(filename, url)] for every provincial file on the EMIS page."""
    src = get(PAGE).decode("utf-8", "replace")

    titles = {
        mid: html.unescape(re.sub(r"<[^>]+>", "", t)).strip()
        for mid, t in re.findall(
            r'<span id="dnn_ctr(\d+)_dnnTITLE_titleLabel"[^>]*>(.*?)</span>', src, re.S)
    }

    found = []
    for mid, href, name in re.findall(
            r'<a id="dnn_ctr(\d+)_Document_grdDocuments_ctlTitle_\d+" '
            r'href="(/LinkClick\.aspx\?fileticket=[^"]+)">(.*?)</a>', src, re.S):
        name = html.unescape(re.sub(r"<[^>]+>", "", name)).strip()
        code = PROVINCES.get(name.lower())
        if not code:
            continue
        section = titles.get(mid, "")
        q = re.search(r"Quarter (\d) of (\d{4})", section)
        tag = f"{q.group(2)}Q{q.group(1)}" if q else re.sub(r"\W+", "", section)[:10]
        url = "https://www.education.gov.za" + html.unescape(href) + "&forcedownload=true"
        found.append((f"{code}_{tag}.xlsx", url))
    return found


def main():
    os.makedirs(OUT, exist_ok=True)
    targets = discover()
    print(f"discovered {len(targets)} provincial files")

    seen, ok, skipped, failed = set(), 0, 0, []
    for fname, url in targets:
        if fname in seen:
            continue
        seen.add(fname)
        path = os.path.join(OUT, fname)
        if os.path.exists(path) and os.path.getsize(path) > 10_000:
            skipped += 1
            continue
        try:
            data = get(url)
            if data[:2] != b"PK":          # xlsx is a zip; anything else is an error page
                failed.append((fname, "not an xlsx"))
                continue
            with open(path, "wb") as fh:
                fh.write(data)
            ok += 1
            print(f"  {fname}  {len(data)//1024} KB")
        except Exception as exc:
            failed.append((fname, str(exc)[:60]))

    print(f"\ndownloaded {ok}, already present {skipped}, failed {len(failed)}")
    for fname, why in failed:
        print(f"  FAILED {fname}: {why}")


if __name__ == "__main__":
    main()
