# Third-Party Notices

This project includes content derived from third-party work, used under the terms of its original license.

## Platform Design Skills

The `skill/reference/ios.md` and `skill/reference/android.md` platform reference files are distilled from ehmo's `platform-design-skills` (Apple Human Interface Guidelines and Material Design 3 rules), rewritten in Impeccable's voice.

**Original work:** https://github.com/ehmo/platform-design-skills
**Original license:** MIT
**Author:** ehmo

The corresponding MIT license is included in `licenses/platform-design-skills.txt`.

## modern-screenshot

`scripts/modern-screenshot.umd.js` is the bundled modern-screenshot browser helper.

**Original work:** https://github.com/qq15725/modern-screenshot
**Original license:** MIT
**Author:** wxm

The MIT license is included in `licenses/modern-screenshot.txt`.

## DanaSkill local customization

Impeccable is Copyright 2025 Paul Bakaus and distributed under Apache-2.0.
This copy retains skill metadata `4.5.2` and is modified as
`explicit-device-scope.1`: Web work defaults to desktop, mobile and tablet
work requires an explicit user requirement, and build gates, capture paths,
reference workflows and finish reviewers preserve that scope.

The changed skill entrypoint, references and reviewers carry local-change
notices. The Apple Silicon engine is rebuilt from upstream engine `0.1.14`
with the patch in `scripts/engine-scope/devices.patch`; the same directory
contains its pinned source revision and reproducible build command.
Published builds remap compiler source paths to remove workstation paths.
These modifications are distributed under the same Apache-2.0 license.
