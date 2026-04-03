#!/usr/bin/env python3
"""
VOID RECON - Advanced Web Security Toolkit
For authorized penetration testing only. By ALONE BEAST
"""

import sys
import re
import time
import threading
import argparse
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, quote

import requests
import urllib3
from colorama import Fore, Style, init

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
init(autoreset=True)

C  = Fore.CYAN
G  = Fore.GREEN
R  = Fore.RED
Y  = Fore.YELLOW
M  = Fore.MAGENTA
W  = Fore.WHITE
DM = Style.DIM
B  = Style.BRIGHT
RS = Style.RESET_ALL

LOCK  = threading.Lock()
STATS = defaultdict(int)

UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
]

def banner():
    print(f"""
{M}{B}
  ██╗   ██╗ ██████╗ ██╗██████╗     ██████╗ ███████╗ ██████╗ ██████╗ ███╗   ██╗
  ██║   ██║██╔═══██╗██║██╔══██╗    ██╔══██╗██╔════╝██╔════╝██╔═══██╗████╗  ██║
  ██║   ██║██║   ██║██║██║  ██║    ██████╔╝█████╗  ██║     ██║   ██║██╔██╗ ██║
  ╚██╗ ██╔╝██║   ██║██║██║  ██║    ██╔══██╗██╔══╝  ██║     ██║   ██║██║╚██╗██║
   ╚████╔╝ ╚██████╔╝██║██████╔╝    ██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚████║
    ╚═══╝   ╚═════╝ ╚═╝╚═════╝     ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝
{RS}{DM}  Advanced Web Security Toolkit  |  v2.1  |  Authorized Testing Only{RS}
""")

def usage():
    print(f"""  {B}USAGE:{RS}
    void-recon {Y}-m{RS} <module> {Y}[options]{RS}

  {B}MODULES:{RS}
    {C}fuzz{RS}       Directory brute-force with a wordlist
    {C}pattern{RS}    FUZZ keyword replacement in URL
    {C}check{RS}      Bulk HTTP status checker
    {C}bypass{RS}     403 Forbidden bypass techniques

  {B}OPTIONS:{RS}
    {Y}-u{RS}  --url        Target URL
    {Y}-w{RS}  --wordlist   Path to wordlist file
    {Y}-t{RS}  --threads    Number of threads  (default: 30)
    {Y}-T{RS}  --timeout    Request timeout     (default: 10)
    {Y}-x{RS}  --ext        Extensions          (e.g. .php,.html)
    {Y}-fc{RS} --filter     Filter status codes (e.g. 200,301)
    {Y}-o{RS}  --output     Output file path
    {Y}-p{RS}  --payloads   Payload file for bypass custom mode

  {B}EXAMPLES:{RS}
    void-recon {Y}-m{RS} fuzz    {Y}-u{RS} https://example.com {Y}-w{RS} wordlist.txt {Y}-fc{RS} 200,301
    void-recon {Y}-m{RS} bypass  {Y}-u{RS} https://example.com/admin
    void-recon {Y}-m{RS} bypass  {Y}-u{RS} https://example.com/admin {Y}-p{RS} payloads.txt
    void-recon {Y}-m{RS} pattern {Y}-u{RS} https://example.com/api/FUZZ {Y}-w{RS} words.txt
    void-recon {Y}-m{RS} check   {Y}-w{RS} urls.txt {Y}-fc{RS} 200,403 {Y}-o{RS} results.txt
""")

def divider():
    print(f"  {DM}{'─' * 76}{RS}")

def ok(m):   print(f"  {G}[+]{RS} {m}")
def warn(m): print(f"  {Y}[!]{RS} {m}")
def err(m):  print(f"  {R}[-]{RS} {m}")
def info(m): print(f"  {C}[*]{RS} {m}")

def status_color(code):
    if code == 200:                  return G
    if code in (301, 302, 303, 307): return C
    if code == 403:                  return Y
    if code == 404:                  return DM
    if code >= 500:                  return R
    return W

def fmt_status(code):
    return f"{status_color(code)}{B}{code}{RS}"

def progress(curr, total, label="", extra=""):
    if total == 0: return
    pct  = curr / total
    w    = 28
    done = int(w * pct)
    bar  = G + "█" * done + DM + "░" * (w - done) + RS
    print(f"\r  [{C}{label}{RS}][{bar}] {Y}{curr}/{total}{RS} {DM}{extra}{RS}  ",
          end="", flush=True)

def get_headers(extra=None):
    import random
    h = {
        "User-Agent": random.choice(UAS),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "close",
    }
    if extra:
        h.update(extra)
    return h

def read_wordlist(path):
    try:
        lines = Path(path).read_text(errors="ignore").splitlines()
        words = [l.strip() for l in lines if l.strip() and not l.startswith("#")]
        ok(f"Wordlist: {G}{len(words):,}{RS} entries")
        return words
    except Exception as e:
        err(f"Cannot read wordlist: {e}")
        return []

def save_results(lines, output_file):
    try:
        Path(output_file).write_text("\n".join(lines))
        ok(f"Saved → {Y}{output_file}{RS}  ({len(lines)} lines)")
    except Exception as e:
        err(f"Save failed: {e}")

def extract_title(html):
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return m.group(1).strip()[:50] if m else "-"

def parse_filter(fc_str):
    if not fc_str:
        return []
    codes = []
    for x in str(fc_str).split(","):
        x = x.strip()
        if x.isdigit():
            codes.append(int(x))
    return codes


def _dir_worker(base_url, word, timeout, filters):
    url = base_url.rstrip("/") + "/" + word.lstrip("/")
    try:
        r = requests.get(url, timeout=timeout, headers=get_headers(),
                         verify=False, allow_redirects=False)
        with LOCK: STATS["tried"] += 1
        code = r.status_code

        if filters and code not in filters:
            return None
        if not filters and code == 404:
            return None

        redirect_loc = r.headers.get("Location", "")
        if code in (301, 302, 303, 307, 308) and redirect_loc:
            try:
                r2 = requests.get(redirect_loc, timeout=timeout,
                                  headers=get_headers(), verify=False,
                                  allow_redirects=True)
                if r2.status_code != 200:
                    return None
                return {
                    "url": url, "status": code,
                    "size": len(r2.content), "words": len(r2.text.split()),
                    "redirect": redirect_loc,
                }
            except Exception:
                return None

        return {
            "url": url, "status": code,
            "size": len(r.content), "words": len(r.text.split()),
            "redirect": "",
        }
    except Exception:
        with LOCK: STATS["err"] += 1
    return None

def run_dir_fuzzer(args):
    if not args.url:
        err("--url required"); return
    if not args.wordlist:
        err("--wordlist required"); return

    filters = parse_filter(args.filter)
    exts    = [e.strip() for e in args.ext.split(",")] if args.ext else [""]
    words   = read_wordlist(args.wordlist)
    if not words: return

    tasks = [w + ext for w in words for ext in exts]

    info(f"Target   : {Y}{args.url}{RS}")
    info(f"Tasks    : {Y}{len(tasks):,}{RS}")
    info(f"Threads  : {Y}{args.threads}{RS}")
    info(f"Filter   : {Y}{filters if filters else 'all (hide 404)'}{RS}")
    divider()
    print(f"  {DM}{'STATUS':<8} {'SIZE':>9}  {'WORDS':>6}  URL{RS}")
    divider()

    hits = []; done = 0; start = time.time()

    with ThreadPoolExecutor(max_workers=args.threads) as ex:
        futs = {ex.submit(_dir_worker, args.url, t, args.timeout, filters): t for t in tasks}
        for fut in as_completed(futs):
            done += 1
            res = fut.result()
            if res:
                hits.append(res)
                redir = f"  {M}-> {DM}{res['redirect'][:50]}{RS}" if res["redirect"] else ""
                print(f"\r  {fmt_status(res['status'])}     "
                      f"{res['size']:>9,}b  {res['words']:>6}  "
                      f"{Y}{res['url']}{RS}{redir}")
            elapsed = time.time() - start
            eta = ((len(tasks) - done) * elapsed / done) if done > 0 else 0
            progress(done, len(tasks), "FUZZ", f"hits:{len(hits)} eta:{eta:.0f}s")

    print(); divider()
    ok(f"Requests : {Y}{STATS['tried']:,}{RS} in {Y}{time.time()-start:.1f}s{RS}")
    ok(f"Found    : {G}{B}{len(hits)}{RS}")
    ok(f"Errors   : {R}{STATS['err']}{RS}")

    if hits and args.output:
        lines = [f"[{r['status']}]  {r['size']:>9,}b  {r['words']:>5}  {r['url']}"
                 + (f"  -> {r['redirect']}" if r["redirect"] else "")
                 for r in hits]
        save_results(lines, args.output)


def _pattern_worker(template, value, timeout, filters):
    target = template.replace("FUZZ", quote(str(value), safe=""))
    try:
        r = requests.get(target, timeout=timeout, headers=get_headers(),
                         verify=False, allow_redirects=False)
        with LOCK: STATS["tried"] += 1
        code = r.status_code
        if filters and code not in filters:
            return None
        if not filters and code == 404:
            return None
        return {
            "url": target, "value": value,
            "status": code, "size": len(r.content),
            "words": len(r.text.split()),
        }
    except Exception:
        with LOCK: STATS["err"] += 1
    return None

def run_pattern_fuzzer(args):
    if not args.url:
        err("--url required"); return
    if "FUZZ" not in (args.url or ""):
        err("URL must contain the FUZZ keyword"); return
    if not args.wordlist:
        err("--wordlist required"); return

    filters = parse_filter(args.filter)
    words   = read_wordlist(args.wordlist)
    if not words: return

    info(f"Template : {Y}{args.url}{RS}")
    info(f"Tasks    : {Y}{len(words):,}{RS}")
    info(f"Filter   : {Y}{filters if filters else 'all (hide 404)'}{RS}")
    divider()
    print(f"  {DM}{'STATUS':<8} {'SIZE':>9}  {'FUZZ VALUE':<28}  URL{RS}")
    divider()

    hits = []; done = 0; start = time.time()

    with ThreadPoolExecutor(max_workers=args.threads) as ex:
        futs = {ex.submit(_pattern_worker, args.url, w, args.timeout, filters): w for w in words}
        for fut in as_completed(futs):
            done += 1
            res = fut.result()
            if res:
                hits.append(res)
                print(f"\r  {fmt_status(res['status'])}     "
                      f"{res['size']:>9,}b  "
                      f"{C}{str(res['value']):<28}{RS}  {res['url'][:55]}")
            elapsed = time.time() - start
            eta = ((len(words) - done) * elapsed / done) if done > 0 else 0
            progress(done, len(words), "FUZZ", f"hits:{len(hits)} eta:{eta:.0f}s")

    print(); divider()
    ok(f"Requests : {Y}{STATS['tried']:,}{RS} in {Y}{time.time()-start:.1f}s{RS}")
    ok(f"Hits     : {G}{B}{len(hits)}{RS}")
    ok(f"Errors   : {R}{STATS['err']}{RS}")

    if hits and args.output:
        lines = [f"[{r['status']}]  {r['size']:>9,}b  FUZZ={str(r['value']):<22}  {r['url']}"
                 for r in hits]
        save_results(lines, args.output)


def _status_worker(url, timeout):
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    try:
        r = requests.get(url, timeout=timeout, headers=get_headers(),
                         verify=False, allow_redirects=True)
        with LOCK: STATS["tried"] += 1
        return {
            "url": url, "status": r.status_code,
            "size": len(r.content),
            "server": r.headers.get("Server", "-"),
            "title": extract_title(r.text),
        }
    except Exception:
        with LOCK: STATS["err"] += 1
        return {"url": url, "status": 0, "size": 0, "server": "-", "title": "ERROR"}

def run_status_checker(args):
    if not args.wordlist:
        err("--wordlist required (URL list file)"); return

    try:
        urls = [l.strip() for l in open(args.wordlist, errors="ignore") if l.strip()]
        ok(f"Targets: {G}{len(urls):,}{RS}")
    except Exception as e:
        err(f"Cannot read file: {e}"); return

    filters = parse_filter(args.filter)
    info(f"Filter  : {Y}{filters if filters else 'all codes'}{RS}")
    divider()
    print(f"  {DM}{'STATUS':<8} {'SIZE':>9}  {'SERVER':<20}  TITLE / URL{RS}")
    divider()

    results = []; done = 0; start = time.time()

    with ThreadPoolExecutor(max_workers=args.threads) as ex:
        futs = {ex.submit(_status_worker, u, args.timeout): u for u in urls}
        for fut in as_completed(futs):
            done += 1
            res = fut.result()
            show = (not filters) or (res["status"] in filters)
            if show:
                results.append(res)
                print(f"\r  {fmt_status(res['status'])}     "
                      f"{res['size']:>9,}b  "
                      f"{DM}{res['server'][:18]:<20}{RS}  "
                      f"{res['title'][:28]}  {DM}{res['url'][:45]}{RS}")
            elapsed = time.time() - start
            eta = ((len(urls) - done) * elapsed / done) if done > 0 else 0
            progress(done, len(urls), "CHECK", f"matched:{len(results)} eta:{eta:.0f}s")

    print(); divider()
    ok(f"Checked : {Y}{STATS['tried']:,}{RS} in {Y}{time.time()-start:.1f}s{RS}")
    ok(f"Matched : {G}{B}{len(results)}{RS}")
    ok(f"Errors  : {R}{STATS['err']}{RS}")

    if results and args.output:
        lines = [f"[{r['status']}]  {r['size']:>9,}b  {r['server']:<20}  {r['url']}"
                 for r in results]
        save_results(lines, args.output)

  
    divider()
    code_counts = defaultdict(int)
    for r in results:
        code_counts[r["status"]] += 1
    for code, count in sorted(code_counts.items()):
        bar = status_color(code) + "█" * min(count, 40) + RS
        print(f"  {fmt_status(code)}  {bar}  {Y}{count}{RS}")


# ── MODULE: 403 Bypass ────────────────────────────────────────────────────
#
# URL construction rules:
#   Given target: https://example.com/status/403
#     base  = https://example.com
#     path  = /status/403
#
#   PATH-AFTER  : base + path + payload   → https://example.com/status/403%20
#   PATH-BEFORE : base + payload + path   → https://example.com/%2f/status/403
#   MID-PATH    : base + seg1 + payload + seg2 → https://example.com/status/./403
#   HEADER-ONLY : base + path  (unchanged URL, inject headers)

BYPASS_HEADERS = [
    {"X-Forwarded-For": "127.0.0.1"},
    {"X-Forwarded-For": "localhost"},
    {"X-Custom-IP-Authorization": "127.0.0.1"},
    {"X-Forwarded-Host": "127.0.0.1"},
    {"X-Originating-IP": "127.0.0.1"},
    {"X-Remote-IP": "127.0.0.1"},
    {"X-Remote-Addr": "127.0.0.1"},
    {"X-Host": "127.0.0.1"},
    {"X-Real-IP": "127.0.0.1"},
    {"X-Original-URL": "/"},
    {"X-Rewrite-URL": "/"},
    {"Referer": "https://127.0.0.1/"},
    {"Client-IP": "127.0.0.1"},
    {"True-Client-IP": "127.0.0.1"},
]

AFTER_PAYLOADS = [
    "/", "//", "/.", "?", "%20", "%09", "%23",
    "..;/", ";/", "/..", "/%20", "/%2f",
    "/%252f", "/.;", "/;/", "/.%2f",
]

BEFORE_PAYLOADS = [
    "/%2f", "/%2f%2f", "/%252f", "/..;", "/..",
]

MID_PAYLOADS = [
    "/./", "//", "/%2f", "/.;/", "/../",
    "/;/", "/%09/", "/%20/",
]


def _build_auto_tasks(parsed):
    """
    Build bypass URL candidates using the correct scheme:
      PATH-AFTER  : scheme://host/original/path + payload
      PATH-BEFORE : scheme://host + payload + /original/path
      MID-PATH    : inject payload between path segments
      HEADER-ONLY : original URL unchanged, with header variants
    """
    scheme = parsed.scheme
    netloc = parsed.netloc
    path   = parsed.path

    if not path or path == "/":
        path = "/"

    base     = f"{scheme}://{netloc}"
    orig_url = f"{base}{path}"

    tasks = []

    
    for payload in AFTER_PAYLOADS:
        tasks.append((f"{orig_url}{payload}", f"after:{payload}", {}))

    
    for payload in BEFORE_PAYLOADS:
        tasks.append((f"{base}{payload}{path}", f"before:{payload}", {}))

    
    segments = [s for s in path.split("/") if s]
    if len(segments) >= 2:
        for i in range(1, len(segments)):
            left  = "/" + "/".join(segments[:i])   
            right = "/".join(segments[i:])          
            for payload in MID_PAYLOADS:
                new_path = left + payload + right
                tasks.append((f"{base}{new_path}", f"mid:{payload}", {}))

  
    for hdr in BYPASS_HEADERS:
        tasks.append((orig_url, f"header:{list(hdr.keys())[0]}", hdr))

    
    for payload in AFTER_PAYLOADS[:6]:
        for hdr in BYPASS_HEADERS[:6]:
            tasks.append((f"{orig_url}{payload}", f"combined:{payload}", hdr))

    return tasks


def _build_custom_tasks(parsed, payloads):
    """
    Custom payload mode:
      Each payload is appended TO the original path, not just the domain.
      CORRECT: https://example.com/status/403/<payload>
      Also tests: header-only variants with each payload URL
    """
    scheme = parsed.scheme
    netloc = parsed.netloc
    path   = parsed.path.rstrip("/")  

    base     = f"{scheme}://{netloc}"
    tasks    = []

    for payload in payloads:
        
        p = payload.strip().lstrip("/")
        
        url = f"{base}{path}/{p}"
        tasks.append((url, f"custom:{p}", {}))

    
    for payload in payloads[:50]:  
        p   = payload.strip().lstrip("/")
        url = f"{base}{path}/{p}"
        for hdr in BYPASS_HEADERS:
            tasks.append((url, f"combined:{p}", hdr))

    return tasks


def _bypass_worker(url, label, headers, timeout, baseline_size):
    try:
        r = requests.get(url, timeout=timeout,
                         headers=get_headers(headers),
                         verify=False, allow_redirects=False)
        with LOCK: STATS["tried"] += 1

        if r.status_code != 200:
            return None

        size = len(r.content)

        
        if baseline_size is not None and abs(size - baseline_size) <= 50:
            return None

        return {
            "url": url, "label": label, "headers": headers,
            "status": r.status_code,
            "size": size, "words": len(r.text.split()),
        }
    except Exception:
        with LOCK: STATS["err"] += 1
    return None


def run_403_bypass(args):
    if not args.url:
        err("--url required"); return

    parsed = urlparse(args.url)
    if not parsed.scheme or not parsed.netloc:
        err("Invalid URL. Use full URL with scheme (https://...)"); return

    
    baseline_size = None
    info(f"Target   : {Y}{args.url}{RS}")
    info("Fetching baseline...")
    try:
        br = requests.get(args.url, timeout=args.timeout,
                          headers=get_headers(), verify=False, allow_redirects=False)
        baseline_size = len(br.content)
        info(f"Baseline : {fmt_status(br.status_code)}  "
             f"Content-Length: {Y}{baseline_size:,} bytes{RS}")
        if br.status_code != 403:
            warn(f"Server returned {br.status_code}, not 403. Proceeding anyway.")
        info(f"Hits within ±50b of baseline will be suppressed (false-positive filter)")
    except Exception as e:
        warn(f"Baseline check failed: {e}")

    
    if args.payloads:
        payloads = read_wordlist(args.payloads)
        if not payloads: return
        tasks = _build_custom_tasks(parsed, payloads)
        info(f"Mode     : {C}Custom payload{RS}  ({len(payloads):,} payloads)")
    else:
        tasks = _build_auto_tasks(parsed)
        info(f"Mode     : {C}Auto{RS}  (path-after, path-before, mid-path, header, combined)")

    info(f"Tasks    : {Y}{len(tasks):,}{RS} combinations")
    divider()
    print(f"  {DM}{'STATUS':<8} {'SIZE':>9}  {'WORDS':>6}  {'TECHNIQUE':<28}  URL{RS}")
    divider()

    hits = []; done = 0; start = time.time()

    with ThreadPoolExecutor(max_workers=args.threads) as ex:
        futs = {
            ex.submit(_bypass_worker, url, label, hdrs, args.timeout, baseline_size):
            (url, label, hdrs)
            for url, label, hdrs in tasks
        }
        for fut in as_completed(futs):
            done += 1
            res = fut.result()
            if res:
                hits.append(res)
                hdr_str = (list(res["headers"].keys())[0]
                           if res["headers"] else "none")
                print(f"\r  {G}{B}[BYPASS]{RS}  "
                      f"{fmt_status(res['status'])}  "
                      f"{res['size']:>9,}b  {res['words']:>6}  "
                      f"{C}{res['label']:<28}{RS}  {Y}{res['url']}{RS}")
                if res["headers"]:
                    print(f"           {DM}Header: {hdr_str}{RS}")
            elapsed = time.time() - start
            eta = ((len(tasks) - done) * elapsed / done) if done > 0 else 0
            progress(done, len(tasks), "BYP ", f"hits:{len(hits)} eta:{eta:.0f}s")

    elapsed = time.time() - start
    print(); divider()
    ok(f"Attempts : {Y}{STATS['tried']:,}{RS} in {Y}{elapsed:.1f}s{RS}")
    ok(f"Bypasses : {G}{B}{len(hits)}{RS} verified (200 OK + size check)")
    ok(f"Errors   : {R}{STATS['err']}{RS}")

    if hits and args.output:
        lines = []
        for r in hits:
            lines.append(
                f"[{r['status']}]  Size:{r['size']:,}  Words:{r['words']}  "
                f"Technique:{r['label']}  {r['url']}"
            )
            if r["headers"]:
                lines.append(f"        Header: {r['headers']}")
            lines.append("")
        save_results(lines, args.output)
    elif not hits:
        warn("No verified bypasses found.")



def build_parser():
    p = argparse.ArgumentParser(
        prog="void-recon",
        add_help=False,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("-m", "--module",   metavar="MODULE",
                   choices=["fuzz", "pattern", "check", "bypass"])
    p.add_argument("-u", "--url",      metavar="URL")
    p.add_argument("-w", "--wordlist", metavar="FILE")
    p.add_argument("-p", "--payloads", metavar="FILE")
    p.add_argument("-t", "--threads",  type=int, default=30)
    p.add_argument("-T", "--timeout",  type=int, default=10)
    p.add_argument("-x", "--ext",      metavar="EXTS", default="")
    p.add_argument("-fc","--filter",   metavar="CODES", default="")
    p.add_argument("-o", "--output",   metavar="FILE")
    p.add_argument("-h", "--help",     action="store_true")
    return p


def main():
    parser = build_parser()
    args   = parser.parse_args()

    banner()

    if args.help or not args.module:
        usage()
        sys.exit(0)

    STATS.clear()

    if   args.module == "fuzz":    run_dir_fuzzer(args)
    elif args.module == "pattern": run_pattern_fuzzer(args)
    elif args.module == "check":   run_status_checker(args)
    elif args.module == "bypass":  run_403_bypass(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {Y}Interrupted.{RS}\n")
        sys.exit(0)
