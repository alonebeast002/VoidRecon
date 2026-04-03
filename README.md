```markdown
# VOID RECON
### Advanced Web Security Toolkit
**Developer:** ALONE BEAST [ https://github.com/alonebeast002/Void-Recon.git ] | **Version:** 2.0

```text
  _   _  _  ___   ___   ___  ___  ___  ___  _  _ 
 | | | |/ \|_ _| |   \ | __|/  __|/ _ \|  \| |
 | \_/ | O || |  | o  || _| | (__| O || | ' |
  \___/ \_/ |_|  |_|\_\|___| \___|\___/|_|\__|
  
  Advanced Web Security Toolkit | v2.1 | @alonebeast002
```
## Overview
VOID RECON is a high-performance, multi-threaded Python framework designed for automated web security reconnaissance. It eliminates redundant output and focuses on precision through baseline filtering and smart URL parsing.
## Key Features
 * **Advanced 403 Bypasser:** Implements path manipulation (Before/After/Mid-path) and header injection.
 * **Smart Baseline Filtering:** Compares response Content-Length against the original 403 baseline to eliminate false positives.
 * **Custom Status Filtering:** ffuf-style status code filtering (e.g., -fc 200,301).
 * **Multi-Threaded Fuzzing:** Optimized for speed with configurable concurrency and timeouts.
## Installation
```bash
git clone https://github.com/alonebeast002/void-recon
cd void-recon
chmod +x setup.sh
sudo ./setup.sh

```
*After installation, the tool can be executed globally using void-recon.*
## Usage Guide
void-recon -m <module> [options]
### Modules
| Module | Function |
|---|---|
| fuzz | Directory brute-forcing with wordlist support. |
| pattern | URL fuzzing by replacing the FUZZ keyword. |
| check | Bulk HTTP status verification for URL lists. |
| bypass | Automated 403 Forbidden bypass techniques. |
### Core Options
 * -u, --url : Target URL (Required for fuzz/bypass)
 * -w, --wordlist : Path to wordlist or URL list
 * -fc, --filter : Filter results by status code (e.g., 200,403)
 * -t, --threads : Concurrent thread count (Default: 30)
 * -o, --output : Export structured results to a file
## Technical Logic: 403 Bypass
Unlike basic tools, VOID RECON performs a **Baseline Check** before testing. If a bypass attempt returns a 200 OK but the page size matches the original 403 Forbidden response (within a 50-byte margin), the result is suppressed to ensure only genuine bypasses are reported.
### Examples
**1. Targeted Directory Scan (Filter 200/301):**
void-recon -m fuzz -u https://target.com -w paths.txt -fc 200,301
**2. Automated 403 Bypass:**
void-recon -m bypass -u https://target.com/admin -o bypass_results.txt
**3. Bulk Status Filtering:**
void-recon -m check -w domains.txt -fc 200 -o alive.txt
## Requirements
 * Python 3.7+
 * requests, colorama, urllib3
## Disclaimer
This tool is intended for **Authorized Testing Only**. The developer is not responsible for any unauthorized use or damages. Always secure written permission before initiating any security assessment.
```
