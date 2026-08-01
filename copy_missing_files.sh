#!/bin/sh

# Copy files that exist in SOURCE but not in TARGET.
# Usage: ./copy_missing_files.sh /path/to/source /path/to/target

# Useful to copy the audio uploads from one directory to another.

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 SOURCE_DIR TARGET_DIR"
  exit 1
fi

src=$1
tgt=$2

if [ ! -d "$src" ]; then
  echo "Source directory does not exist: $src"
  exit 1
fi

if [ ! -d "$tgt" ]; then
  echo "Target directory does not exist: $tgt"
  exit 1
fi

# Remove trailing slashes for consistent relative path handling.
src=${src%/}
tgt=${tgt%/}

find "$src" -type f -print0 | while IFS= read -r -d '' file; do
  relpath=${file#"$src"/}
  dest="$tgt/$relpath"
  if [ ! -e "$dest" ]; then
    mkdir -p "$(dirname "$dest")"
    cp -p "$file" "$dest"
  fi
done
