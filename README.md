# liminality-eclipse

Source of truth for `eclipse.shadow.black` and `liminality-eclipse.pages.dev`.

| Layer | Where it lives | Notes |
|---|---|---|
| Code + design | this repo, `src/index.html` | byte-identical to the live Pages origin |
| Edge transform | `edge/pbi-edge-transform.mjs` | the `pbi-edge` Worker, constants verbatim |
| Build | `build.py` | `src/index.html` -> `dist/index.html` via the Worker transform |
| Deploy | Cloudflare Pages project `liminality-eclipse` | behind a `pbi-edge` Worker route |
| Media | none | the page references no local media file |

## Verify

```
python verify.py
```

`verify.py` materialises every tracked blob out of git into a clean checkout, runs
`build.py` there, re-fetches both live surfaces (one cache-busted) and byte-compares
after removing Cloudflare's Web Analytics beacon. Exit 0 means the committed source
reproduces what production serves.

## What this repo is not

It does not deploy. The `estate-sot` lane is read-only against Cloudflare: no
deployment, no DNS change, no Worker edit from here.
