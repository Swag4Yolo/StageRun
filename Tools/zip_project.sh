#!/bin/bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
parent_dir="$(cd "$script_dir/.." && pwd)"
zip_path="$script_dir/srun.zip"

rm -f "$zip_path"

(cd "$parent_dir" && zip -qr "$zip_path" .)
