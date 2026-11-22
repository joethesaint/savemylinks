# Changelog

What changed in each release, and what the review caught before it shipped.

Every pull request gets a live demo while it is reviewed, then a review by
[CodeRabbit](https://coderabbit.ai) (one an hour, in queue order). Its findings are answered in
the PR, fixed or deferred with a reason, before the final review and merge. The tables below
list them, so you can see what the review found that we missed. They come from the PR threads
via `python tools/changelog.py <PR numbers>`.

Plans and ideas live in [CHANGELOG_ROADMAP.md](CHANGELOG_ROADMAP.md).

## Unreleased

- **License:** SaveMyLinks is MIT licensed ([#10](https://github.com/joethesaint/savemylinks/pull/10)).
- **Live demo for every PR**, posted on the PR while it is reviewed; this changelog with the
  review findings.

## v0.1.0 · 22 November 2026

The first downloadable release: SaveMyLinks as one small program for Windows, macOS and Linux.

- **Run your own copy** ([#8](https://github.com/joethesaint/savemylinks/pull/8)): a Rust app
  (`native/`) that serves the full app on your computer with real link previews, your library in
  one file. 5 MB, about 12 MB of memory. No Python, no setup.
- **One contract, two apps:** `tests/contract` runs the same 18 checks against the Rust app and
  the Python app in CI, so they behave the same.
- **CodeRabbit reviews by label**, one an hour, with per-folder review notes
  ([#7](https://github.com/joethesaint/savemylinks/pull/7)).
- **Demo fixes:** Clippy loads again and moves (idle every 6-14 s, a move on click)
  ([#6](https://github.com/joethesaint/savemylinks/pull/6)); every PR tests and builds the demo
  before merge ([#5](https://github.com/joethesaint/savemylinks/pull/5)).

### Reviewed by CodeRabbit

| PR | What CodeRabbit found that we missed | Where | Severity | Status |
|---|---|---|---|---|
| [#8](https://github.com/joethesaint/savemylinks/pull/8) | Pin the validated addresses to each request. Connection-time DNS can bypass `assert_public` | `native/src/preview.rs` | Major | Fixed in `d5c0267` |
| [#8](https://github.com/joethesaint/savemylinks/pull/8) | Reject non-public IPv6 special-purpose ranges | `native/src/preview.rs` | Minor | Fixed in `d5c0267` |
| [#8](https://github.com/joethesaint/savemylinks/pull/8) | Return `None` when reading the response body fails | `native/src/preview.rs` | Minor | Fixed in `d5c0267` |
| [#8](https://github.com/joethesaint/savemylinks/pull/8) | Convert path-extractor failures to the API validation response | `native/src/main.rs` | Minor | Fixed in `d5c0267` |
| [#8](https://github.com/joethesaint/savemylinks/pull/8) | Reject non-object update bodies before checking fields | `native/src/main.rs` | Minor | Fixed in `d5c0267` |
| [#8](https://github.com/joethesaint/savemylinks/pull/8) | Validate save fields before clipping or checking for duplicates | `native/src/main.rs` | Minor | Fixed in `d5c0267` |
| [#8](https://github.com/joethesaint/savemylinks/pull/8) | Add Unix first-run commands | `README.md` | Minor | Fixed in `d5c0267` |
| [#8](https://github.com/joethesaint/savemylinks/pull/8) | Document recovery from the macOS launch block | `README.md` | Minor | Fixed in `d5c0267` |

8 findings, 1 major (security), all fixed before release. The contract gained 5 checks from them.
