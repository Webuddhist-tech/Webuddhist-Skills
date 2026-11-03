#!/usr/bin/env python3
"""Download every original (non-commentary, non-translation) text from the
OpenPecha backend API v2 into 0-INBOX/raw-data/, verbatim.

The API is the old production backend (openpecha-backend `main` branch,
Firebase project `pecha-backend`). Every API response is written to disk
exactly as received so the intake converter works from a frozen copy and
the vault can always show what the backend said.

    python3 <skill>/tools/openpecha-api-download.py
    python3 <skill>/tools/openpecha-api-download.py --types root,none,translation_source --workers 10

Output layout (one folder per text, one file per API response):

    0-INBOX/raw-data/openpecha-api/
      manifest.json                      run metadata: base URL, API version, counts, failures
      texts.json                         GET /v2/texts (every page, every type)
      categories.json                    GET /v2/categories?application=webuddhist (bo + en titles)
      texts/<text_id>/
        text.json                        GET /v2/texts/<text_id>
        instances.json                   GET /v2/texts/<text_id>/instances
        instances/<instance_id>.json     GET /v2/instances/<id>?content=true&annotation=true
        annotations/<annotation_id>.json GET /v2/annotations/<id>

The text `type` is inferred by the backend from relations: `commentary` and
`translation` point at another text; `translation_source` has translations;
`root` has commentaries; `none` stands alone. The default selection is every
text that is not itself a commentary or translation.

Re-running skips files that already exist, so an interrupted run resumes.
Pass --force to re-download everything.
"""
import argparse, json, os, sys, threading, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

# Vault root: $VAULT_ROOT, else the current directory (run from the vault root).
VAULT = os.path.abspath(os.environ.get("VAULT_ROOT") or os.getcwd())
DEFAULT_BASE = "https://api-aq25662yyq-uc.a.run.app"   # prod, pecha-backend project
DEFAULT_OUT = os.path.join(VAULT, "0-INBOX", "raw-data", "openpecha-api")
# Annotation types fetched per instance: "all" fetches every type the instance
# endpoint lists (segmentation, search_segmentation, durchen, bibliography,
# pagination, table_of_contents, …). The endpoint never lists alignment
# annotations — those belong to translation pairs, not to a root text.
DEFAULT_ANNOTATIONS = "all"

_print_lock = threading.Lock()


def log(msg):
    with _print_lock:
        print(msg, flush=True)


def fetch(base, path, retries=5):
    url = base + path
    delay = 2
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=300) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                raise
            err = e
        except Exception as e:  # network, timeout, bad JSON
            err = e
        if attempt == retries:
            raise err
        time.sleep(delay)
        delay *= 2


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def get_or_load(base, path, dest, force):
    if not force and os.path.exists(dest):
        with open(dest, encoding="utf-8") as f:
            return json.load(f)
    data = fetch(base, path)
    save(dest, data)
    return data


def download_text(base, out, text, ann_types, force):
    tid = text["id"]
    tdir = os.path.join(out, "texts", tid)
    q = urllib.parse.quote
    get_or_load(base, f"/v2/texts/{q(tid)}", os.path.join(tdir, "text.json"), force)
    instances = get_or_load(base, f"/v2/texts/{q(tid)}/instances",
                            os.path.join(tdir, "instances.json"), force)
    n_ann = 0
    for inst in instances:
        iid = inst["id"]
        detail = get_or_load(base, f"/v2/instances/{q(iid)}?content=true&annotation=true",
                             os.path.join(tdir, "instances", f"{iid}.json"), force)
        for ann in detail.get("annotations") or []:
            if "all" not in ann_types and ann.get("type") not in ann_types:
                continue
            aid = ann["annotation_id"]
            get_or_load(base, f"/v2/annotations/{q(aid)}",
                        os.path.join(tdir, "annotations", f"{aid}.json"), force)
            n_ann += 1
    return tid, len(instances), n_ann


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--types", default="root,none,translation_source",
                    help="comma-separated text types to download (default: every non-derived text)")
    ap.add_argument("--annotations", default=DEFAULT_ANNOTATIONS)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    types = set(a.types.split(","))
    ann_types = set(a.annotations.split(","))
    os.makedirs(a.out, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")

    version = fetch(a.base, "/api/version")
    log(f"API {a.base} version={version}")

    texts, offset = [], 0
    while True:
        page = fetch(a.base, f"/v2/texts?limit=100&offset={offset}")
        texts += page
        if len(page) < 100:
            break
        offset += 100
    save(os.path.join(a.out, "texts.json"), texts)
    log(f"{len(texts)} texts listed")

    cats = {}
    for lang in ("bo", "en"):
        for c in fetch(a.base, f"/v2/categories?application=webuddhist&language={lang}"):
            cats.setdefault(c["id"], {"id": c["id"], "parent": c.get("parent"),
                                      "has_child": c.get("has_child")})["title_" + lang] = c.get("title")
    save(os.path.join(a.out, "categories.json"), list(cats.values()))

    selected = [t for t in texts if t.get("type") in types]
    log(f"{len(selected)} texts selected (types: {', '.join(sorted(types))})")

    done, failures = 0, []
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        futs = {pool.submit(download_text, a.base, a.out, t, ann_types, a.force): t["id"] for t in selected}
        for fut in as_completed(futs):
            tid = futs[fut]
            try:
                fut.result()
            except Exception as e:
                failures.append({"text_id": tid, "error": repr(e)})
                log(f"FAIL {tid}: {e!r}")
            done += 1
            if done % 25 == 0 or done == len(selected):
                log(f"{done}/{len(selected)} texts ({len(failures)} failed)")

    # A resumed run only adds files, so keep the first run's dates at the top
    # level (they date the content) and append this run to the history.
    mpath = os.path.join(a.out, "manifest.json")
    old = json.load(open(mpath, encoding="utf-8")) if os.path.exists(mpath) else {}
    finished = datetime.now(timezone.utc).isoformat(timespec="seconds")
    runs = old.get("runs") or ([{k: old[k] for k in ("started", "finished", "annotation_types") if k in old}] if old else [])
    runs.append({"started": started, "finished": finished, "annotation_types": sorted(ann_types),
                 "force": a.force, "failures": len(failures)})
    save(mpath, {
        "api_base": a.base,
        "api_version": version,
        "backend": "openpecha-backend main branch (Firebase project pecha-backend, prod)",
        "started": started if a.force or not old else old.get("started", started),
        "finished": finished if a.force or not old else old.get("finished", finished),
        "types": sorted(types),
        "annotation_types": sorted(ann_types),
        "texts_listed": len(texts),
        "texts_selected": len(selected),
        "failures": failures,
        "runs": runs,
    })
    if failures:
        sys.exit(f"{len(failures)} text(s) failed — re-run to resume")


if __name__ == "__main__":
    main()
