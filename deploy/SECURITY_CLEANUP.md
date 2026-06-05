# Security Cleanup Plan

## What Was Found

The tracked file `analysis/terminal_log_extracted.csv` contains historical `request_token`-like strings captured from earlier manual Kite authentication terminal logs.

## Risk Level

These are likely expired short-lived request tokens. They are lower risk than a Kite API secret, a daily access token, or a token-store file.

They are still token-like material and should not remain in tracked source files.

## Immediate Safe Cleanup

Recommended current-tree cleanup, without rewriting Git history:

1. Sanitize token-like strings in `analysis/terminal_log_extracted.csv`.
2. Replace concrete historical values with a placeholder such as `[REDACTED_REQUEST_TOKEN]`.
3. Check for other generated terminal logs or analysis exports that may contain copied secrets.
4. Add generated terminal logs or analysis exports to `.gitignore` if they are not intended source artifacts.

Because `analysis/terminal_log_extracted.csv` is a tracked file and may be part of prior research/audit artifacts, get explicit approval before modifying or removing it.

## When To Rotate Kite Credentials

Rotate Kite credentials if any of the following happened:

- `KITE_API_SECRET` was committed.
- A daily `access_token` was committed.
- A token-store JSON file was committed.
- The repository was public or shared while credential material was present.
- You are uncertain whether a long-lived secret was exposed.

## When To Consider Git History Rewrite

Do not rewrite Git history casually.

Consider history rewrite only if long-lived secrets were committed, such as `KITE_API_SECRET`, a valid access token, or token-store contents.

Before rewriting history:

1. Rotate affected credentials first.
2. Coordinate with all clones and remotes.
3. Confirm the repository backup and branch strategy.
4. Use a purpose-built tool such as `git filter-repo` or BFG Repo-Cleaner.

Short-lived historical request tokens normally do not justify history rewrite by themselves if they are expired, but they should be sanitized from the current tree after approval.
