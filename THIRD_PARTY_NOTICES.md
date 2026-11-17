# Third-party notices and source provenance

This repository currently contains upstream Git submodule references and documentation. It has not yet copied or modified upstream source files into the RoyaleBench package.

## crforge

- Project: https://github.com/voonhous/crforge
- Pinned commit: fa5959055c590a493d62c8dbc804e602832d08a6
- Licence: Apache License 2.0
- Copyright: Copyright 2025-2026 voonhous
- Upstream files: third_party/upstream/crforge/
- Preserve the upstream LICENSE and NOTICE when distributing the submodule or any derived/ported source.
- crforge's NOTICE states that crforge ships no game data. Game tables are not part of the source licence.
- The upstream README requests source path and commit comments on ports/reimplementations. RoyaleBench intends to follow that request for any future port.

## RoyaleGym

- Project: https://github.com/RoyaleGym/RoyaleGym
- Pinned commit: 278bcb06dae717b89194b992235a9fa8a5209084
- Licence: MIT
- Copyright: Copyright (c) 2026 RoyaleGym contributors
- Upstream files: third_party/upstream/royalegym/
- Any future copied/adapted source must retain the copyright and MIT permission notice.

## RoyaleSim

- Project: https://github.com/RoyaleGym/RoyaleSim
- Pinned commit: a849c29ae632e12f81442c45b0d9b2d2f2f99f15
- Licence: MIT for source code
- Copyright: Copyright (c) 2026 RoyaleGym contributors
- Upstream files: third_party/upstream/royalesim/
- Critical exclusion: the upstream LICENSE explicitly says it does not cover data/raw/, which contains reproduced Supercell game-data tables. Those files are not MIT-licensed and must not be redistributed under this notice.

## Not yet copied

No source code from FirstLight_CR, ClashAI, Hasty-CR, clash-jev, MSU-AI/clash-royale-gym or KataCR is currently copied into RoyaleBench. Their intended reference-only roles and licence review status are documented in docs/REUSE_PLAN.md.

## Release rule

Before a release bundles any upstream source, include the relevant upstream license text and notices in the release artifact. Before copying or adapting a file, update this register with exact upstream path, commit, copyright holder, licence, local modifications and tests. No licence for source code grants rights to third-party game assets or data.
