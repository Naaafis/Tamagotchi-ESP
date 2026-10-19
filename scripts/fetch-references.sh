#!/usr/bin/env bash
# Clone upstream reference repos into references/ (git-ignored).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p references
repos=(
  neubauek/CircuitPython-Virtual-Pet
  FoamyGuy/Blinka_Displayio_PyGameDisplay
  adafruit/Adafruit_CircuitPython_ILI9341
  jcrona/tamalib
  RBEGamer/TamagotchiESP32
  Almarch/Nanogotchi
  beccamakes/esp32-s3-tamagotchi
)
for r in "${repos[@]}"; do
  dest="references/${r##*/}"
  if [ -d "$dest/.git" ]; then
    echo "update $r"; git -C "$dest" pull --ff-only --quiet || echo "  (pull failed, skipping)"
  else
    echo "clone  $r"; git clone --depth 1 --quiet "https://github.com/$r.git" "$dest" || echo "  (clone failed, skipping)"
  fi
done
