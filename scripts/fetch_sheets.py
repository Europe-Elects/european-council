"""Reads the European Council tracker's Google Sheet and writes each tab as data/<tab>.csv for the page.
Needs GOOGLE_TOKEN (keyless login from google-github-actions/auth) and EUCO_SHEET_ID (repository secret).
The Sheet must be shared with ee-sheets-reader@project-6c08a079-4a01-46eb-aaf.iam.gserviceaccount.com (Viewer).
Usage: python3 scripts/fetch_sheets.py site/data
"""
import csv, json, os, sys, time, urllib.error, urllib.parse, urllib.request

TABS = ['Monthly', 'Changes', 'Leaders', 'Groups']   # Groups is optional
API = 'https://sheets.googleapis.com/v4/spreadsheets/'

def get(url):
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + os.environ['GOOGLE_TOKEN']})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (400, 403, 404):
                raise RuntimeError(f'Sheets API {e.code} (is the Sheet shared with the service account?) {e.read()[:300]!r}')
            if attempt == 3: raise
        except urllib.error.URLError:
            if attempt == 3: raise
        time.sleep(5 * (attempt + 1))

def main(out):
    sheet_id = os.environ.get('EUCO_SHEET_ID', '').strip()
    if not sheet_id: sys.exit('Secret EUCO_SHEET_ID is missing')
    os.makedirs(out, exist_ok=True)
    titles = {p['properties']['title'].strip().lower(): p['properties']['title'] for p in get(API + sheet_id + '?fields=sheets.properties.title')['sheets']}
    for tab in TABS:
        title = titles.get(tab.lower())
        if not title:
            if tab == 'Groups': print('Groups tab not found (optional)'); continue
            sys.exit(f'Tab "{tab}" not found in the Sheet')
        rng = urllib.parse.quote("'" + title.replace("'", "''") + "'", safe='')
        rows = get(API + sheet_id + '/values/' + rng + '?valueRenderOption=FORMATTED_VALUE').get('values', [])
        width = max((len(r) for r in rows), default=0)
        path = os.path.join(out, tab.lower() + '.csv')
        with open(path, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerows([r + [''] * (width - len(r)) for r in rows if any(str(c).strip() for c in r)])
        print(f'{path}: {max(len(rows) - 1, 0)} rows')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'site/data')
