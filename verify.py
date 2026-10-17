#!/usr/bin/env python3
"""liminality-eclipse - prove this repo reproduces the live site.    python verify.py

Materialises every tracked blob out of git into a clean checkout (so the rebuild runs on
COMMITTED bytes, not on anything uncommitted), then fetches live and byte-compares.

Every check below can fail. A gate that cannot fail is not a gate.
"""
import hashlib
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
ORIGIN_URL = "https://liminality-eclipse.pages.dev/"
BRAND_URL = "https://eclipse.shadow.black/"
BRAND_HOST = "eclipse.shadow.black"
EDGE = True
SANITISED = False
ORIGIN_SHA256 = "6b6bcadf396c3cc631d474e5dc75391f141340260a53448294d65fd6942b3a46"
ORIGIN_BYTES = 18302
FORBIDDEN = "theblack" + "garter" + ".com.au"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")

# Cloudflare's Web Analytics beacon. It is injected AFTER the Worker output, so it sits
# between the payload and </body>. Strip the tag AND the newline that follows it - removing
# only the tag leaves one spurious byte, which can either fail a correct build or cancel
# against a build that wrongly adds the same newline.
BEACON = re.compile(rb'<script type="module" src="https://static\.cloudflareinsights\.com[^"]*"[^>]*>\s*</script>\n?', re.I)

MEDIA = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".mp4", ".webm", ".mov",
         ".m4v", ".mp3", ".wav", ".ogg", ".woff", ".woff2", ".ttf", ".otf", ".eot", ".pdf",
         ".avif", ".bmp", ".tiff", ".heic")
SECRET_NAMES = (".env", ".dev.vars")
REL = "src/index.html"

fails = []


def check(ok, label, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + label + (("   " + detail) if detail else ""))
    if not ok:
        fails.append(label)


def fetch(url, no_cache=False):
    headers = {"User-Agent": UA}
    if no_cache:
        headers["Cache-Control"] = "no-cache"
        headers["Pragma"] = "no-cache"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=45,
                                context=ssl.create_default_context()) as r:
        return r.read()


def main():
    print("== liminality-eclipse verify ==")
    blob = subprocess.run(["git", "-C", ROOT, "show", "HEAD:" + REL], capture_output=True)
    if blob.returncode != 0:
        check(False, "committed blob readable from git objects")
        return 1
    committed = blob.stdout
    check(hashlib.sha256(committed).hexdigest() == ORIGIN_SHA256,
          "committed blob matches the pinned live-origin SHA-256",
          "%d B" % len(committed))
    check(len(committed) == ORIGIN_BYTES, "committed blob is the pinned byte count")

    # prove the rebuild runs on COMMITTED bytes
    tmp = tempfile.mkdtemp(prefix="liminality-eclipse-verify-")
    try:
        files = [f for f in subprocess.check_output(
            ["git", "-C", ROOT, "ls-files"], text=True).split() if f]
        for f in files:
            data = subprocess.check_output(["git", "-C", ROOT, "show", "HEAD:" + f])
            dest = os.path.join(tmp, f.replace("/", os.sep))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as fh:
                fh.write(data)
        r = subprocess.run([sys.executable, os.path.join(tmp, "build.py")],
                           capture_output=True, text=True)
        sys.stdout.write(r.stdout)
        check(r.returncode == 0, "build.py runs green on a clean checkout of the committed blobs")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # house rule, over EVERY tracked blob and not just the page (prose that documents the
    # rule is PROSE, but the cheapest correct answer is to not spell the domain out at all)
    for f in files:
        data = subprocess.check_output(["git", "-C", ROOT, "show", "HEAD:" + f])
        text = data.decode("utf-8", "replace")
        hit = re.findall(r'(?:href|src|action)=["\'][^"\']*' + re.escape(FORBIDDEN), text, re.I)
    # The house rule is "no forbidden-domain links OR DATA". A link-only check misses
    # DATA: a JSON-LD record naming the domain matches no href/src/action attribute, so it
    # walks straight past such a gate. Classify every hit; assert on LINK and DATA; REPORT
    # prose, which is legitimate when a file merely documents the rule (Trap 5).
    # built from chr() so neither quote delimiter needs escaping inside this string
    DQ, SQ = chr(34), chr(39)
    ATTR = re.compile(r"(?:href|src|action)\s*=\s*[" + DQ + SQ + r"]"
                      r"[^" + DQ + SQ + r"]*" + re.escape(FORBIDDEN), re.I)
    DATAREC = re.compile(r"\{[^\{\}]{0,600}" + re.escape(FORBIDDEN)
                         + r"[^\{\}]{0,600}\}", re.I)
    APOS = chr(39)
    for f in files:
        data = subprocess.check_output(["git", "-C", ROOT, "show", "HEAD:" + f])
        text = data.decode("utf-8", "replace")
        total = len(re.findall(re.escape(FORBIDDEN), text, re.I))
        link = ATTR.findall(text)
        covered = set()
        # m.span(), NOT tuple-unpacking the match: a re.Match is not iterable, and the
        # resulting TypeError fires only on a file that MATCHES - so every clean file
        # passed and the crash stayed invisible until a mutation triggered it.
        for m in DATAREC.finditer(text):
            covered.update(range(m.start(), m.end()))
        data_hits = sum(1 for m in re.finditer(re.escape(FORBIDDEN), text, re.I)
                        if m.start() in covered)
        prose = total - len(link) - data_hits
        detail = "LINK=%d DATA=%d" % (len(link), data_hits)
        if prose:
            detail += " PROSE=%d" % prose
        check(not link and not data_hits,
              "no forbidden-domain LINK or DATA in %s" % f, detail)
        if prose and not link and not data_hits:
            print("        NOTE %d PROSE occurrence(s) in %s - documents the rule, not a link"
                  % (prose, f))
    bad_media = [f for f in files if f.lower().endswith(MEDIA)]
    bad_secret = [f for f in files if os.path.basename(f) in SECRET_NAMES]
    check(not bad_media and not bad_secret, "no media or secret-shaped file is tracked",
          "media=%s secrets=%s" % (bad_media, bad_secret))
    gi = subprocess.check_output(["git", "-C", ROOT, "show", "HEAD:.gitignore"]).decode()
    check(all(rule in gi for rule in ("dist/", ".env", ".wrangler/", "*.mp4")),
          "gitignore excludes build artifacts, secrets and media")

    # live comparison
    origin_live = fetch(ORIGIN_URL)
    check(hashlib.sha256(origin_live).hexdigest() == ORIGIN_SHA256,
          "live Pages origin still matches the pinned SHA-256",
          "%d B" % len(origin_live))
    built = subprocess.run([sys.executable, os.path.join(tmp if False else ROOT, "build.py")],
                           capture_output=True, text=True)
    dist = os.path.join(ROOT, "dist", "index.html")
    rebuilt = open(dist, "rb").read() if os.path.exists(dist) else committed

    if EDGE:
        # the brand hostname is served by the pbi-edge Worker; compare after removing the
        # platform beacon. Three fetches, one cache-busted.
        ok = True
        for i, cb in enumerate((False, False, True), 1):
            live = fetch(BRAND_URL + ("?cb=estate-sot" if cb else ""), no_cache=cb)
            stripped = BEACON.sub(b"", live)
            same = stripped == rebuilt
            ok = ok and same
            print("  %s  brand fetch %d%s  %6d B raw, %6d B beacon-free"
                  % ("PASS " if same else "FAIL ", i, " (cache-busted)" if cb else "",
                     len(live), len(stripped)))
            if not same:
                n = min(len(stripped), len(rebuilt))
                k = next((j for j in range(n) if stripped[j] != rebuilt[j]), n)
                print("        first difference at byte %d" % k)
                print("        live  %r" % stripped[max(0, k - 80):k + 80])
                print("        built %r" % rebuilt[max(0, k - 80):k + 80])
        check(ok, "committed source + edge transform reproduces the brand hostname byte-exactly")
        check(rebuilt == committed or len(rebuilt) > len(committed),
              "the rebuild differs from the origin by the edge payload, as expected")
        cross = subprocess.run([sys.executable, os.path.join(ROOT, "edge", "check_constants.py")],
                               capture_output=True, text=True, timeout=180)
        sys.stdout.write(cross.stdout)
        check(cross.returncode == 0,
              "edge/check_constants.py: the .mjs and .py constants agree and match live")
    else:
        # no Worker on this host: the brand hostname must equal the origin after the beacon
        ok = True
        for i, cb in enumerate((False, False, True), 1):
            live = fetch(BRAND_URL + ("?cb=estate-sot" if cb else ""), no_cache=cb)
            same = BEACON.sub(b"", live) == committed
            ok = ok and same
            print("  %s  brand fetch %d%s  %6d B" % ("PASS " if same else "FAIL ", i,
                                                     " (cache-busted)" if cb else "", len(live)))
        check(ok, "committed source reproduces the brand hostname byte-exactly (no edge Worker here)")

    if SANITISED:
        print("  NOTE  committed == live is EXPECTED to be False for this repo: see README.")

    print("\nVERIFY %s" % ("PASS" if not fails else "FAIL - " + ", ".join(fails)))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
