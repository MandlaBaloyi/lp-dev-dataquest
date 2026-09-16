"""Download every NSC School Performance Report DBE has published (2012-2024).

Source: https://www.education.gov.za/Resources/Reports.aspx
No registration. These are national - all nine provinces in one document.

Each report carries three years of results per school, so the 2012 and 2024
editions together span 2010-2024. Per school the tables give: EMIS number,
centre number, name, district, quintile, and for each year the number
progressed, the number who wrote, the number who achieved, and the pass rate.

Files land in datasets/raw/nsc_reports/ and are gitignored - re-downloadable.
"""

import os
import re
import html
import time
import urllib.request

PAGE = "https://www.education.gov.za/Resources/Reports.aspx"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "datasets", "raw", "nsc_reports")


def get(url, tries=3):
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=300).read()
        except Exception:
            if n == tries - 1:
                raise
            time.sleep(3 * (n + 1))


def discover():
    src = get(PAGE).decode("utf-8", "replace")
    found = {}
    for href, txt in re.findall(r'href="([^"]+)"[^>]*>(.*?)</a>', src, re.S):
        label = html.unescape(re.sub(r"<[^>]+>", "", txt)).strip()
        m = re.match(r"NSC Examinations (\d{4}):\s*School Performance Report", label, re.I)
        if m and m.group(1) not in found:
            found[m.group(1)] = "https://www.education.gov.za" + html.unescape(href)
    return sorted(found.items())


def main():
    os.makedirs(OUT, exist_ok=True)
    reports = discover()
    print(f"discovered {len(reports)} reports: {', '.join(y for y, _ in reports)}\n")

    ok, skipped, failed = 0, 0, []
    for year, url in reports:
        path = os.path.join(OUT, f"NSC_School_Performance_{year}.pdf")
        if os.path.exists(path) and os.path.getsize(path) > 100_000:
            skipped += 1
            continue
        try:
            data = get(url + "&forcedownload=true")
            if data[:4] != b"%PDF":
                failed.append((year, "not a PDF"))
                continue
            with open(path, "wb") as fh:
                fh.write(data)
            ok += 1
            print(f"  {year}  {len(data)//1024//1024} MB")
        except Exception as exc:
            failed.append((year, str(exc)[:60]))

    print(f"\ndownloaded {ok}, already present {skipped}, failed {len(failed)}")
    for year, why in failed:
        print(f"  FAILED {year}: {why}")


if __name__ == "__main__":
    main()
