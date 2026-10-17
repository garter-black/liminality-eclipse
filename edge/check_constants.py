
#!/usr/bin/env python3
# edge/check_constants.py - prove the committed edge transform and the committed build agree.
#
#     python edge/check_constants.py
#
# build.py carries its own copy of the pbi-edge constants so it can run without node.
# That duplication is a trap: if the two copies drift, the committed transform is a lie
# and every byte comparison still passes, because the comparison uses build.py's copy.
# This file parses BOTH committed files and compares them, so the drift cannot survive.
#
# Exit 0 = the .mjs and the .py declare identical constants, and the agent id those
# constants name is the one the live page actually carries.
import os
import re
import subprocess
import sys
import time
import urllib.request

# resolve the repo from this file's own location, not from the CWD: verify.py runs this
# from edge/, and a script that only works from the root is one that will not get run
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRAND_URL = "https://eclipse.shadow.black"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")

DQ = chr(34)
SQ = chr(39)

# Either quote style, built from chr() so neither delimiter has to be escaped inside this
# string. PLAYER_TAG is single-quoted in both files and LAYOUT is double-quoted in both: an
# extractor that reads only one style agrees with one constant by luck while being blind
# to its neighbour, which is worse than not checking at all.
QUOTED = re.compile(DQ + r"((?:[^" + DQ + r"\\]|\\.)*)" + DQ + "|"
                    + SQ + r"((?:[^" + SQ + r"\\]|\\.)*)" + SQ)

fails = []


def check(ok, label, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + label + (("   " + detail) if detail else ""))
    if not ok:
        fails.append(label)


def show(path):
    return subprocess.check_output(["git", "-C", REPO, "show", "HEAD:" + path]).decode("utf-8")


def literals(text):
    # only the string literals of an expression: a CSS brace or a tag inside quotes is
    # data, and anything outside quotes is not part of the constant
    return [m.group(1) if m.group(1) is not None else m.group(2)
            for m in QUOTED.finditer(text)]


def assignment(text, name):
    # Right-hand side of `name = ...`, following parentheses to their close.
    # (Python, not JavaScript: `;` is not a terminator here, and a value containing one
    # would be safe. The .mjs side needs the string-aware scanner above.)
    m = re.search(r"^" + name + r"\s*=\s*", text, re.M)
    if not m:
        return None
    rest = text[m.end():]
    if not rest.startswith("("):
        return rest.splitlines()[0]
    depth = 0
    for i, ch in enumerate(rest):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return rest[:i + 1]
    return rest


mjs = show("edge/pbi-edge-transform.mjs")
py = show("build.py")


def statement(text, start):
    # The text from `start` to the end of the enclosing JavaScript statement, respecting
    # string literals and line continuations.
    #
    # Two things this must not do, both learned by having them fail:
    #   - cut at the first `;`: a CSS value like `bottom:24px!important` contains a
    #     semicolon inside its own quoted string.
    #   - cut at the first newline: the .mjs writes a constant as
    #         "...}" +
    #         "@media(...)</style>";
    #     so a newline after a binary operator CONTINUES the expression.
    # A newline therefore ends the statement only when the last non-space token was not an
    # operator.
    i = start
    depth = 0
    quote = None
    last = ""            # last significant character seen outside a string
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == chr(92):        # backslash escape
                i += 2
                continue
            if ch == quote:
                quote = None
                last = "literal"
            i += 1
            continue
        if ch in (chr(34), chr(39)):
            quote = ch
            i += 1
            continue
        if ch.isspace():
            if ch == chr(10) and depth == 0 and last not in ("+", ",", "(", "=", "&", "|", ":"):
                return text[start:i]
            i += 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        elif ch == ";" and depth == 0:
            return text[start:i]
        last = ch
        i += 1
    return text[start:]


def mjs_lit(name):
    # \s* on BOTH sides of the = : the .mjs wraps some declarations onto the next line,
    # and a pattern that only matches the one-line form agrees with PLAYER_TAG by luck
    # while being blind to LAYOUT.
    m = re.search(r"export const " + name + r"\s*=\s*", mjs)
    if not m:
        return None
    return "".join(literals(statement(mjs, m.end())))


print("== pbi-edge constant cross-check ==")
for name in ("PLAYER_TAG", "LAYOUT"):
    rhs = assignment(py, name)
    a = mjs_lit(name)
    c = "".join(literals(rhs)) if rhs is not None else None
    check(bool(a) and a == c,
          "%s identical in edge/pbi-edge-transform.mjs and build.py" % name,
          "" if a == c else "mjs=%r py=%r" % ((a or "")[:48], (c or "")[:48]))

py_nd = assignment(py, "NETWORK_DEFAULT")
parts = [x.strip().strip(DQ).strip(SQ) for x in py_nd.strip("() ").split(",")] if py_nd else []
mid = re.search(r"id: " + DQ + "([^" + DQ + r"]+)" + DQ, mjs)
mc1 = re.search(r"c1: " + DQ + "([^" + DQ + r"]+)" + DQ, mjs)
mc2 = re.search(r"c2: " + DQ + "([^" + DQ + r"]+)" + DQ, mjs)
mjs_ag = [mid.group(1), mc1.group(1), mc2.group(1)] if (mid and mc1 and mc2) else None
check(mjs_ag is not None and mjs_ag == parts,
      "NETWORK_DEFAULT identical in edge/pbi-edge-transform.mjs and build.py",
      "" if mjs_ag == parts else "mjs=%r py=%r" % (mjs_ag, parts))

# The strongest form of the same claim: the agent id these two files agree on is the id
# the LIVE page carries. That is what proves no AGENTS entry matched this host.
# Back off and retry: a transient resolver blip on a host doing hundreds of fetches is not
# a finding about the site (Trap 3 / Trap 22).
live = ""
err = ""
for attempt, wait in enumerate((2, 4, 8, 8)):
    try:
        with urllib.request.urlopen(
                urllib.request.Request(BRAND_URL, headers={"User-Agent": UA}), timeout=45) as r:
            live = r.read().decode("utf-8", "replace")
        break
    except Exception as e:
        err = type(e).__name__ + ": " + str(e)[:80]
        if attempt < 3:
            time.sleep(wait)
if live:
    check(bool(parts) and parts[0] in live,
          "the agreed agent id is the one the live page carries",
          parts[0] if parts else "no id parsed")
    check(live.count("<elevenlabs-convai") == 1,
          "live carries exactly one voice widget",
          str(live.count("<elevenlabs-convai")))
else:
    check(False, "live fetch for the agent-id cross-check (4 attempts)", err)

print(chr(10) + "EDGE CONSTANTS %s" % ("PASS" if not fails else "FAIL - " + ", ".join(fails)))
sys.exit(0 if not fails else 1)
