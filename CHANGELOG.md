# Changelog

What changed in each release, and what the review caught before it shipped.

Every pull request gets a live demo while it is reviewed. CI (tests, the API contract, builds,
the demo) is the gate for merging. [CodeRabbit](https://coderabbit.ai) gives a second opinion
(one review an hour, in queue order), which may arrive after the merge. Its findings are fixed
in a follow-up or deferred with a reason. The tables below list them, so you can see what the
review found that we missed. They come from the PR threads
via `python tools/changelog.py <PR numbers>`.

Plans and ideas live in the [issues](https://github.com/joethesaint/savemylinks/issues).

## Unreleased

- **Keyboard shortcuts and dot-repeat** ([#9](https://github.com/joethesaint/savemylinks/pull/9)):
  `j/k` select, `o` open, `e` edit, `c` category, `d` delete with Undo, `.` repeat, `?` help.
- **Clippy teaches Vim habits** ([#24](https://github.com/joethesaint/savemylinks/pull/24)): after
  the slow way twice, one "Did you know?" tip for the faster key.
- **Installable on phones with share-to-save; a download page with SHA-256 checksums; link
  previews for SaveMyLinks' own pages** ([#11](https://github.com/joethesaint/savemylinks/pull/11)).
- **License:** SaveMyLinks is MIT licensed ([#10](https://github.com/joethesaint/savemylinks/pull/10)).
- **Live demo for every PR**, posted on the PR while it is reviewed; this changelog with the
  review findings ([#12](https://github.com/joethesaint/savemylinks/pull/12)).

### Reviewed by CodeRabbit

| PR | What CodeRabbit found that we missed | Where | Severity | Status |
|---|---|---|---|---|
| [#9](https://github.com/joethesaint/savemylinks/pull/9) | Keep Undo available when restoration fails | `app/templates/index.html` | Major | Fixed in `7d1ef88` |
| [#9](https://github.com/joethesaint/savemylinks/pull/9) | Expose the selected link to assistive technology | `app/templates/index.html` | Minor | Fixed in `7d1ef88` |
| [#9](https://github.com/joethesaint/savemylinks/pull/9) | Handle rejected mutation requests | `app/templates/index.html` | Minor | Fixed in `7d1ef88` |
| [#9](https://github.com/joethesaint/savemylinks/pull/9) | Correct the page after deletions finish, not before | `app/templates/index.html` | Minor | Fixed in `7d1ef88` |
| [#11](https://github.com/joethesaint/savemylinks/pull/11) | Review requested after merge; still in progress | | | Pending |
| [#24](https://github.com/joethesaint/savemylinks/pull/24) | Merged on green CI; not yet reviewed | | | Pending |

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
