#!/usr/bin/env bash
# Sanitize the disks before decommissioning the machine.
set -euo pipefail

dd if=/dev/zero of=/dev/sda bs=4M
diskpart clean
