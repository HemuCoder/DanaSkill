# Local Web device scope

This installation keeps engine 0.1.14 and applies `devices.patch` to its
official source (`engine-v0.1.14`, commit
`866f3557a13847bf450d8d09d23459243d2fb7c3`). It is a local customization,
not an upstream release. `scripts/VERSION` and `engine-probe` keep their
upstream version so the launcher's version contract stays valid.

`build-phase start` defaults to `--devices desktop`. Explicitly requested
device classes can be supplied as a comma-separated list of `desktop`,
`tablet`, and `mobile`; the state records this as `deviceClasses`.
Saved-capture gates, local and remote HTML rendering, finish checks, and
their guidance all use this list. Reference widths are 1440, 768, and 390.
Old state without the field uses desktop; invalid or empty scopes fail.

This repository includes the patched Apple Silicon Mac binary only, under
`scripts/bin/darwin-arm64/impeccable`. Other hosts must rebuild and put the
result at the matching launcher path (or set `IMPECCABLE_BIN` to it). An
official binary found or downloaded by the launcher does not contain this
patch. Published builds remap compiler source paths to `/impeccable-source`
and `/cargo-cache`, preserving behavior without workstation paths.

Rebuild for the current host with Rust, curl, tar, patch, and shasum:

```sh
sh build.sh /absolute/path/to/impeccable
```

The script checks the pinned source archive, applies the patch, runs the
comp-verbs library and capture-service tests, and builds the binary.
An upstream skill or engine update can overwrite this local customization;
check the new version's device contract before replacing it.
