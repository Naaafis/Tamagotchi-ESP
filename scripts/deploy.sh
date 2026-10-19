#!/usr/bin/env bash
# Copy firmware/ onto the CIRCUITPY drive. The board auto-reloads code.py on write.
# Never passes --delete, so lib/ (managed by circup), boot_out.txt, settings.toml
# and sd/ are left alone. Stale firmware files must be removed from the board by hand.
set -euo pipefail
cd "$(dirname "$0")/.."

DEST="${CIRCUITPY:-/Volumes/CIRCUITPY}"
if [ ! -f "$DEST/boot_out.txt" ]; then
  echo "CIRCUITPY not mounted at $DEST (no boot_out.txt). Plug the board into its USB port." >&2
  exit 1
fi

# -r recurse, -c compare by checksum (FAT can't keep mtimes, so this avoids rewriting
# unchanged files and triggering needless reloads), no -a since FAT has no perms/owners.
rsync -rcv \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.DS_Store' \
  --exclude 'README.md' \
  firmware/ "$DEST/"
sync
echo "deployed to $DEST"
