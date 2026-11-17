# Pinned upstream source references

This directory contains Git submodules used for source inspection, API integration and reproducible attribution. They are not copied into RoyaleBench's own Python package and are not automatically shipped in a RoyaleBench release.

Initial pins:
- crforge: Apache-2.0, commit fa5959055c590a493d62c8dbc804e602832d08a6.
- RoyaleGym: MIT, commit 278bcb06dae717b89194b992235a9fa8a5209084.
- RoyaleSim: MIT source licence, commit a849c29ae632e12f81442c45b0d9b2d2f2f99f15; its data/raw directory is explicitly excluded from that licence.

Initialize the references after cloning RoyaleBench:

    git submodule update --init --recursive

To see the pinned revisions:

    git submodule status

Do not advance a submodule pointer casually. Use the upstream-upgrade checklist in docs/REUSE_PLAN.md and rerun the relevant tests before changing a pin.

The crforge source itself ships no game data. RoyaleSim's MIT licence does not cover data/raw. Do not copy upstream game tables, original game images/audio, private replays or other excluded assets into this repository.

A submodule pin is a source reference, not an endorsement of every upstream claim and not a substitute for reading the relevant licence. See docs/REUSE_PLAN.md for the precise reuse policy.
