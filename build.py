#!/usr/bin/env python3
"""liminality-eclipse - rebuild the brand-hostname document from source.

    python build.py            src/index.html -> dist/index.html
    python build.py --verify   build and print both SHA-256 values and the byte delta

src/index.html is byte-identical to the live Cloudflare Pages origin. The document a
visitor to eclipse.shadow.black actually receives is that origin after the `pbi-edge` Worker has
run; edge/pbi-edge-transform.mjs holds the Worker's constants verbatim.

This lane is read-only against Cloudflare: it never deploys and never changes DNS.
"""
import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src", "index.html")
DIST = os.path.join(ROOT, "dist")
OUT = os.path.join(DIST, "index.html")

# --- verbatim from edge/pbi-edge-transform.mjs, which is verbatim from worker.js ---
PLAYER_TAG = '<script src="/_pbi/player.js" defer></script>'

# Both style constants end in TWO closing braces: one closes the element selector, one
# closes the @media rule. Do not "tidy" that back into one, and do not build these by
# str.format() - format() eats one brace from each and the build loses 2 bytes.
LAYOUT = ("<style>elevenlabs-convai{right:16px!important;bottom:24px!important}"
          "@media(max-width:640px){elevenlabs-convai{right:10px!important;bottom:76px!important}}</style>")

NETWORK_DEFAULT = ("agent_7601kv76b5cgfq9thvb5mxsdqsw0", "#c9c5bb", "#0a0a0a")


def convai_tag(a):
    aid, c1, c2 = a
    return ("<style>elevenlabs-convai{position:fixed;right:16px;bottom:24px;z-index:2147482000}"
            "@media(max-width:640px){elevenlabs-convai{bottom:76px;right:10px}}</style>"
            '<elevenlabs-convai agent-id="' + aid +
            '" avatar-orb-color-1="' + c1 + '" avatar-orb-color-2="' + c2 +
            '"></elevenlabs-convai>'
            '<script src="https://unpkg.com/@elevenlabs/convai-widget-embed" async type="text/javascript"></script>')


def transform(html):
    out = html
    if "/_pbi/player.js" not in out:
        out = re.sub(r"</head\s*>", PLAYER_TAG + "</head>", out, count=1, flags=re.I)
    payload = LAYOUT + convai_tag(NETWORK_DEFAULT)
    return re.sub(r"</body\s*>", payload + "</body>", out, count=1, flags=re.I)


# The edge delta is derived from the builder above, never from a number measured earlier:
# if the constants ever drift, this is where the drift shows up.
EXPECTED_DELTA = len(PLAYER_TAG.encode()) + len(LAYOUT.encode()) + len(convai_tag(NETWORK_DEFAULT).encode())


def main():
    with open(SRC, "rb") as fh:
        origin = fh.read()
    built = transform(origin.decode("utf-8")).encode("utf-8")
    os.makedirs(DIST, exist_ok=True)
    with open(OUT, "wb") as fh:      # binary write: newline conversion is not a thing here
        fh.write(built)
    print("origin %6d B  sha %s" % (len(origin), hashlib.sha256(origin).hexdigest()))
    print("built  %6d B  sha %s" % (len(built), hashlib.sha256(built).hexdigest()))
    print("edge delta %d B (expected %d)" % (len(built) - len(origin), EXPECTED_DELTA))
    return 0 if len(built) - len(origin) == EXPECTED_DELTA else 1


if __name__ == "__main__":
    sys.exit(main())
