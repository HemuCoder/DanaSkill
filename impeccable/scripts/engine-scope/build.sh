#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: sh build.sh /absolute/path/to/output-binary" >&2
  exit 1
fi

case "$1" in
  /*) output_binary=$1 ;;
  *) echo "output path must be absolute" >&2; exit 1 ;;
esac

scope_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
build_root=$(mktemp -d "${TMPDIR:-/tmp}/impeccable-scope.XXXXXX")
trap 'rm -rf "$build_root"' EXIT HUP INT TERM
archive="$build_root/source.tar.gz"
source_root="$build_root/source"
mkdir "$source_root"

curl -fsSL --retry 2 --max-time 180 \
  https://codeload.github.com/pbakaus/impeccable/tar.gz/refs/tags/engine-v0.1.14 \
  -o "$archive"
expected=c14ab76a758678060f3eb7f6a5b1bee2b10d25ae151d5f41e0517439c528877d
actual=$(shasum -a 256 "$archive" | cut -d' ' -f1)
if [ "$actual" != "$expected" ]; then
  echo "source archive checksum mismatch" >&2
  exit 1
fi

tar -xzf "$archive" --strip-components=1 -C "$source_root" \
  impeccable-engine-v0.1.14/Cargo.toml \
  impeccable-engine-v0.1.14/Cargo.lock \
  impeccable-engine-v0.1.14/crates \
  impeccable-engine-v0.1.14/skill \
  impeccable-engine-v0.1.14/scripts/bundle-signing-keys.json \
  impeccable-engine-v0.1.14/browser-bundle \
  impeccable-engine-v0.1.14/ui/component-review \
  impeccable-engine-v0.1.14/tests/fixtures
patch -d "$source_root" -p1 < "$scope_dir/devices.patch"

export CARGO_TARGET_DIR="$source_root/target"
source_cache="${CARGO_HOME:-${HOME}/.cargo}"
export RUSTFLAGS="${RUSTFLAGS:+$RUSTFLAGS }--remap-path-prefix=$source_root=/impeccable-source --remap-path-prefix=$source_cache=/cargo-cache"
cargo test --locked --manifest-path "$source_root/Cargo.toml" -p impeccable-comp-verbs --lib
cargo test --locked --manifest-path "$source_root/Cargo.toml" -p impeccable --lib capture_service::
CARGO_PROFILE_RELEASE_LTO=false CARGO_PROFILE_RELEASE_CODEGEN_UNITS=16 \
  cargo build --locked --manifest-path "$source_root/Cargo.toml" --release -p impeccable
install -m 755 "$source_root/target/release/impeccable" "$output_binary"
