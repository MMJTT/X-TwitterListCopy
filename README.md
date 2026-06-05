# x-listcopy

Copy members from one X/Twitter List to another List you own, using your logged-in web cookies.

[中文说明](README.zh-CN.md)

## Repository Description

Copy X/Twitter List members with logged-in web cookies, dry-run safety checks, duplicate skipping, and bilingual docs for modern List workflows.

## Why This Exists

The original `Noleli/listcopy` project was a small PHP app that used Twitter OAuth 1.0a and old REST endpoints. Those endpoints and app keys no longer work reliably in 2026. `x-listcopy` keeps the same practical goal, but uses the current X web GraphQL flow observed from the logged-in web app.

This tool was built after a real successful copy:

- Source List members read: `188`
- Destination List members after copy: `185`
- Remaining failures: `3`, all rejected by X with `code 104`

## Important Notice

This project is not affiliated with X Corp. It uses web GraphQL endpoints that are not a stable public API. X can change them at any time.

Use this only with accounts and Lists you control. You are responsible for following X's Terms of Service, rate limits, and local laws.

Your `auth_token` and `ct0` cookies are sensitive credentials. Treat them like passwords:

- never commit them
- never paste them into public issues
- refresh/log out after use if you want to invalidate the session

## Features

- Copy members from a public or accessible source List to a List you own
- Copy to an existing destination List
- Create a new destination List
- `--dry-run` mode before any write operation
- Requires `--yes` before mutating your account
- Skips members already in the destination List
- Handles X's current List mutation quirk where the member is added but the GraphQL response reports a List banner decode error
- No third-party Python dependencies

## Requirements

- Python 3.10+
- A logged-in X account in your browser
- A destination List owned by your account, or permission to create one

## Installation

Clone the repository:

```bash
git clone https://github.com/your-name/x-listcopy.git
cd x-listcopy
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the CLI:

```bash
pip install -e .
```

Run tests:

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

## Get Your Cookies

1. Open `https://x.com` in a browser where you are logged in.
2. Open Developer Tools.
3. Go to the Application/Storage tab.
4. Find Cookies for `https://x.com`.
5. Copy the values for:
   - `auth_token`
   - `ct0`

Export them locally:

```bash
export X_AUTH_TOKEN="your-auth_token-cookie"
export X_CT0="your-ct0-cookie"
```

Optional:

```bash
export X_BEARER_TOKEN="current-web-bearer-token"
```

Normally you do not need `X_BEARER_TOKEN`; the tool discovers the current public web bearer token from X's frontend bundle.

## Usage

Always start with a dry run:

```bash
x-listcopy \
  --source "https://x.com/i/lists/2026486577304842549?s=20" \
  --dry-run
```

Copy to an existing List:

```bash
x-listcopy \
  --source "https://x.com/i/lists/2026486577304842549?s=20" \
  --dest-list-id "2062729798158565650" \
  --yes
```

Create a new private List and copy into it:

```bash
x-listcopy \
  --source "owner/list-slug" \
  --create-list-name "Copied List" \
  --description "Copied with x-listcopy" \
  --private \
  --yes
```

Limit a copy for testing:

```bash
x-listcopy \
  --source "https://x.com/i/lists/2026486577304842549" \
  --dest-list-id "2062729798158565650" \
  --limit 10 \
  --yes
```

You can also run it as a module:

```bash
python -m x_listcopy --source "owner/list-slug" --dry-run
```

## Supported List References

```text
1234567890
https://x.com/i/lists/1234567890
https://twitter.com/owner/lists/list-slug
owner/list-slug
```

Numeric List IDs are the most reliable format.

## Exit Codes

- `0`: command completed without member-add failures
- `1`: command completed but at least one member failed to add
- other non-zero values: configuration, authentication, network, or GraphQL failure

## Common Errors

### `Set X_AUTH_TOKEN and X_CT0`

The cookie environment variables are missing.

### `Could not find X GraphQL operations`

X changed its web frontend bundle. Open an issue with the operation names that failed.

### `Authorization: You aren't allowed to add members to this list`

X rejected that specific member or destination List operation. In observed runs, some users cannot be added because of account privacy, blocking, suspension, or other X-side policy checks.

### `DecodeException` involving `default_banner_media_results`

The observed behavior in June 2026: `ListAddMember` can successfully add the member while the response body fails to decode a List banner field. The tool treats this specific response as a successful add for `ListAddMember` only.

## Security Model

The tool sends requests directly from your machine to X. It does not store cookies, upload them, or write them to disk.

Recommended workflow:

1. Export cookies in a local shell.
2. Run `--dry-run`.
3. Run the copy with `--yes`.
4. Close the shell.
5. Refresh/log out of X if you want the cookies invalidated.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
PYTHONPATH=src python -m unittest discover -s tests
```

Project layout:

```text
src/x_listcopy/
  client.py      X web GraphQL client
  cli.py         command-line interface
  models.py      dataclasses
  parsing.py     List URL and timeline parsing
tests/
  test_x_listcopy.py
```

## Roadmap

- Optional JSON output
- Resume file for very large Lists
- Better progress summaries

## License

Apache-2.0
