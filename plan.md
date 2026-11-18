# RoyaleBench: ICML 2027 Research and Implementation Plan

**Plan version:** 1.0  
**Created:** 18 November 2026  
**Target:** ICML 2027 Main Conference  
**Primary contribution type:** Datasets, Evaluations, and Benchmarks  
**Status:** Research plan, not a statement that planned experiments have been completed

---

## 0. Executive decision

The target is an ICML 2027 main-conference paper, submitted under **Datasets, Evaluations, and Benchmarks**. The ambition is a paper strong enough to be considered for a spotlight or an award distinction. That is an ambition, not a predictable outcome.

The existing RoyaleBench v1 repository is a useful engineering foundation, but its current evidence is not sufficient for a top-tier benchmark paper:

- one mirrored Hog 2.6 deck;
- one CRForge simulator and one fixed game-data build;
- structured observations only;
- one competitive testbed, not yet a broad benchmark suite;
- random-legal and one rule-based agent as the implemented baselines;
- a persistence forecaster, not a trained predictive world model;
- complete Windows headless v1 acceptance passed on 18 November 2026, but only on a three-seed smoke set;
- no large-scale cross-play results from independent seed groups;
- no demonstrated results from a serious learned policy or a frozen hosted-model participant.

The paper must therefore be more than a description of the existing code. It needs a defensible scientific question, a broader but controlled evaluation suite, a new evaluation methodology, and empirical findings that are useful beyond this specific game.

**Recommended central thesis:**

> Aggregate win rates are an incomplete measure of strategic competence in partially observable, real-time competitive environments. Rankings can depend on opponent archetype, deck matchup, decision cadence and observation modality. A benchmark should therefore combine competitive cross-play with paired visual-versus-structured evaluation and simulator-grounded diagnostics that separate perception, temporal state estimation, action grounding and strategic choice.

The proposed paper will combine:

1. a reproducible, FAIR structured-state competitive environment with a separate deterministic visual-observation track;
2. multiple verified deck archetypes and cross-matchups, not just one mirror matchup;
3. a paired visual-versus-structured protocol using the same underlying states and, where possible, the same multimodal model family;
4. competency diagnostics for resource management, opponent modelling, spatial reasoning, temporal planning and adaptation;
5. a simulator-grounded, counterfactual action-quality diagnostic that estimates candidate-set regret under explicitly fixed continuations;
6. an empirical audit of scripted, imitation-learned, RL, search-based, LLM and VLM agents across opponent and matchup shifts.

The make-or-break contribution is the causal decomposition of the visual-to-structured performance gap and the relationship between diagnostic competence and actual competitive outcomes. A new game wrapper or a leaderboard alone is unlikely to be sufficiently distinctive.

---

**Venue decision:** CVPR 2027 is no longer a viable new-submission target as of 18 November 2026: its paper registration deadline was 10 November AoE and its submission deadline was 16 November AoE. The 23 November supplementary-material cutoff is only for papers already submitted; it does not reopen submissions. The research plan therefore targets ICML 2027. Official CVPR dates: https://cvpr.thecvf.com/Conferences/2027/CallForPapers.

## 1. ICML 2027 target and constraints

The official ICML 2027 Call for Papers currently lists:

- Main-conference submission opens: **8 January 2027**.
- Abstract deadline: **14 January 2027, 23:59 AoE**.
- Full-paper deadline: **22 January 2027, 23:59 AoE**.
- Main paper length: **8 pages**, with references, impact statement and appendices outside that limit.
- There is no separate later supplementary-material deadline; the submission must contain the paper file and its supporting appendices by the main deadline.
- The author list cannot be changed after the abstract deadline. Final title and abstract edits are allowed until full-paper submission, but the abstract at the earlier deadline must already describe the real contribution.

For India (IST), the AoE cutoffs correspond to approximately **15 January 2027, 17:29 IST** for the abstract and **23 January 2027, 17:29 IST** for the full paper. Use the OpenReview deadline display as the final authority.

ICML 2027 explicitly includes the contribution type **Datasets, Evaluations, and Benchmarks**. Its guidance says the primary contribution can be a new benchmark, evaluation methodology, metric, tool, audit or substantive empirical analysis. It does not require a new learning algorithm or a new state-of-the-art model result. It does require clear scientific claims, originality, rigorous evidence, and honest treatment of assumptions and limitations. Contribution types are not separate tracks with separate acceptance quotas.

The paper should select **Datasets, Evaluations, and Benchmarks** unless the central contribution changes materially before submission. Do not label this a separate “benchmark track.”

The CFP also requires an AI Disclosure Statement. Substantive use of generative AI in research ideation, experimental design, code generation, data analysis, literature synthesis or substantial drafting must be disclosed. Maintain an accurate log of such use and independently verify every technical claim, experiment and citation. The authors remain responsible for all content.

The submission is double blind. Prepare an anonymized paper and artifact access path. Do not advertise the work as an ICML submission during the review period.

Official pages:
- ICML 2027 Call for Papers: https://icml.cc/Conferences/2027/CallForPapers
- ICML 2027 Dates and Deadlines: https://icml.cc/Conferences/2027/Dates
- ICML 2027 Contribution Types: https://icml.cc/Conferences/2027/ContributionTypes

---

## 2. Proposed paper identity

### Working title

**Beyond Win Rates: Diagnosing Strategic Competence in Partially Observable Competitive Games**

Alternative title if the counterfactual evaluation method becomes the dominant contribution:

**RoyaleBench: Counterfactual Evaluation of Strategic Decisions in Real-Time Competitive Games**

Avoid a title that implies RoyaleBench is a general-purpose game engine or the first benchmark for game-playing agents.

### Research questions

The paper should answer a small number of questions deeply:

**RQ1. Does aggregate competitive strength generalize?**  
Do agent rankings remain stable across deck archetypes, mirror versus cross-archetype matchups, seat assignments and opponent policy families?

**RQ2. Do match outcomes reveal the quality of individual strategic decisions?**  
Can an agent win through opponent-specific exploitation or policy quirks while making locally poor decisions? How strongly does match score agree with simulator-grounded action-quality measurements?

**RQ3. What is the causal value of common public-memory assistance?**  
Does exposing the same structured estimate of opponent elixir and card cycle improve action quality and competitive outcomes? In which states does it help, and where does it fail?

**RQ4. How does decision cadence affect strategy?**  
How do 5-tick and 20-tick observation/action intervals change outcomes and agent rankings? These are simulation cadences, not inference-time budgets. The paused-clock design must not be misrepresented as a real-time latency test.

**RQ5. How brittle are agents to opponent and matchup shift?**  
Does a model trained or prompted against one archetype retain performance against unseen deck archetypes and unfamiliar policies?

### Falsifiable hypotheses

These are hypotheses to test, not conclusions to write in advance:

- **H1, ranking instability:** agent rankings vary across matchup strata; a single aggregate rating hides meaningful agent-by-matchup interactions.
- **H2, outcome/decision mismatch:** match score and counterfactual action quality are correlated but not interchangeable; at least some agents show a measurable mismatch.
- **H3, information assistance:** common public-memory assistance changes decision quality most in states where opponent cycle/resource information is strategically relevant.
- **H4, specialization:** agents optimized against one deck or opponent family lose performance under held-out matchup or opponent shifts.
- **H5, cadence interaction:** changing decision cadence affects different policy families differently, even though it does not allocate different wall-clock reasoning budgets.

The paper must be willing to report that a hypothesis was not supported. Do not tune hypotheses after seeing the final test results.

---

## 3. Novelty and positioning against existing work

RoyaleBench cannot claim to be the first game-agent benchmark, the first multi-agent game benchmark, the first Clash Royale simulator, or the first RTS strategic-reasoning evaluation.

The related-work comparison must include at least:

- **RTSGameBench (2026):** a vision-language benchmark built around the Beyond All Reason RTS, with full-game matchups, diagnostic mini-games and a self-evolving scenario-generation framework. This is the most important recent strategic-game benchmark to differentiate from. RoyaleBench should not try to beat it by building another large visual RTS. Its distinct focus is structured FAIR state, competitive 1v1 micro-decisions, native placement semantics, public-information accounting and simulator-grounded action counterfactuals.
- **BALROG (ICLR 2025):** evaluates LLMs and VLMs across a suite of existing games and reports fine-grained agentic performance. RoyaleBench differs through competitive two-player interaction, hidden opponent state, common action semantics, paired seat swaps and cross-opponent evaluation.
- **GAMA-Bench / γ-Bench:** evaluates gaming ability in multiple classical multi-agent game-theory scenarios. Compare its dynamic scoring and generalization questions with RoyaleBench's real-time spatial/resource decisions.
- **AgentBench (ICLR 2024):** broad multi-environment LLM-as-agent evaluation. Use it to position the value of a focused, deeply instrumented environment rather than to claim broad coverage.
- **MultiAgentBench (ACL 2025):** collaboration and competition across multi-agent scenarios. Discuss where its task scope differs from a symmetric, adversarial real-time game.
- **GameBench (2024):** cross-domain game-based strategic reasoning evaluation.
- **RoyaleGym / RoyaleSim:** existing Clash Royale-oriented simulation and Gym-style infrastructure. These are prior environments and references, not interchangeable experimental results.
- **CRForge:** the upstream engine used by RoyaleBench. The paper must state clearly that RoyaleBench builds on it; the engine itself is not the paper's invention.
- **ClashAI and other public Clash Royale policies:** inspect for baseline reuse, training recipes and compatibility, but only include a policy in the official benchmark after licensing and interface audits.

The paper's defensible novelty should be the **combination of**:

1. a FAIR, seat-relative structured competitive protocol with explicit visibility and action provenance;
2. true paired cross-play across different strategy archetypes, not only mirror play;
3. counterfactual action-quality diagnostics reconstructed from deterministic simulator prefixes;
4. a statistically careful analysis of how ratings, tactical decision quality, opponent specialization and public-memory assistance relate.

A comparison table in the paper should explicitly state each work's environment, modalities, competition structure, observability, diagnostic evaluation, cross-play protocol and reproducibility artefacts. The comparison must be factual and should not dismiss prior work.

Reference starting points:
- RTSGameBench: https://arxiv.org/abs/2606.18950
- BALROG: https://arxiv.org/abs/2411.13543
- GAMA-Bench: https://arxiv.org/abs/2403.11807
- AgentBench: https://arxiv.org/abs/2308.03688
- MultiAgentBench: https://aclanthology.org/2025.acl-long.421/
- GameBench: https://arxiv.org/abs/2406.06613
- RoyaleGym: https://github.com/RoyaleGym/RoyaleGym
- RoyaleSim: https://github.com/RoyaleGym/RoyaleSim
- CRForge: https://github.com/voonhous/crforge
- ClashAI: https://github.com/vegetableleaf/ClashAI

A fresh literature sweep is required in December, especially for papers and benchmarks released after this list was assembled.

---

## 4. Scope: freeze v1, build a research benchmark layer

### Do not rewrite the existing v1 contract

The current v1 acceptance target remains:

- CRForge commit fa5959055c590a493d62c8dbc804e602832d08a6;
- game-data version 16.635.8, content SHA 062a11e0500c03cc041f123413b1ef1846b539a4;
- mirrored Hog 2.6, equal card/tower level 11;
- 18 × 32 tile-centre action grid, MASK_ALL_TILES=1, native PlayerCommands placement;
- structured FAIR observation;
- paused-clock profiles of 5 and 20 engine ticks;
- paired seat swaps, match manifests, Glicko-2 and match-level dataset export.

Keep this exact configuration as the compatibility and smoke-test baseline. Do not silently change the meaning of existing v1 results.

Add the ICML research suite as a separately versioned configuration (for example, icml-2027-v1 or research-v2). Every research result must identify its deck/matchup configuration and action-resolution version.

### Research deck suite

The single Hog 2.6 deck is insufficient for a broad strategic-generalization claim. Add **at least three distinct, classic deck archetypes**, subject to an explicit engine-fidelity audit:

1. **Cycle / pressure:** Hog 2.6 (existing anchor).
2. **Bait / control:** a classic Log Bait-style deck.
3. **Beatdown:** a classic Golem-style or other slow-investment archetype.
4. **Optional fourth archetype:** bridge-spam or another substantially different strategic style, only if the card mechanics pass the same audit and the runtime remains reliable.

Do not hard-code these candidate card lists into the paper before verification. Freeze exact ordered lists, card levels, tower settings, card support, spell interactions, building interactions and data fingerprints in a config file only after a reviewer can reproduce each selected mechanic in CRForge. Prefer non-champion, non-evolution decks initially, because they avoid a known class of opponent-elixir accounting complications.

At minimum evaluate:
- each deck mirrored against itself;
- each unordered cross-archetype matchup;
- both seat assignments for every seed and matchup.

This produces a matchup matrix rather than one leaderboard number. If three archetypes are the validated maximum, use all three and analyse them deeply. Do not add a fourth deck at the cost of incomplete validation.

### Separate benchmark layers

**Layer A: competitive matches.** Full matches against fixed and adaptive opponents, paired by seat and seed.

**Layer B: decision diagnostics.** Reconstructed states, fixed candidate-action sets and controlled counterfactual continuation rollouts. This is the proposed methodological contribution.

**Layer C: public-information estimation.** Opponent-cycle/resource prediction and controlled observation-memory ablations.

**Layer D: optional forecasting.** Keep the current persistence evaluator as a sanity baseline. Add a trained forecaster only if it contributes to a specific research claim and can be trained/evaluated without leakage. Do not let a secondary world-model experiment displace the central competitive-evaluation contribution.

---

## 5. The central methodological contribution: counterfactual action-quality evaluation

### Problem

A match win/loss score is a long-horizon outcome influenced by many factors: opponent policy, deck matchup, seat, stochastic initialization, and every decision made after the action being studied. A leaderboard can rank complete agents, but it does not by itself identify whether a specific tactical decision was good in the state where it was made.

### Proposed evaluator

Build a **rollout-based candidate-set regret** diagnostic from deterministic simulator replay.

For a sampled state s, generate a versioned candidate set C(s) consisting only of actions valid under the benchmark action schema. Include the agent's actual action when valid. The set should contain a reproducible mixture of:
- wait;
- each playable hand slot at strategically distinct legal locations;
- spell/defensive/pressure placements relevant to the state;
- only actions supported by the frozen v1 mechanics.

Reconstruct the same pre-decision state by replaying the original seed and joint-action prefix. For each candidate action a:
1. replay the prefix to the exact target decision;
2. intervene by forcing a for the evaluated agent;
3. keep the opponent continuation policy fixed within the comparison;
4. use a predeclared continuation controller for later decisions by the evaluated seat;
5. execute multiple paired rollouts only where environment randomness remains;
6. record terminal outcome and a separately specified short-horizon diagnostic, if needed.

Let V-hat(s,a) be the empirical value under the declared continuation and opponent-policy distribution. Define:

    Regret_C(s, a_agent) = max over a in C(s) of V-hat(s,a) - V-hat(s,a_agent).

This is **candidate-set regret under a specified rollout policy**, not optimal game-theoretic regret and not a proof that the best sampled action is globally optimal. State this limitation prominently.

Use terminal match score as the primary value where computation allows. A pre-registered short-horizon value based on public tower-health and resource differences can be secondary, with exact weights published before final evaluation. Do not invent reward weights after seeing model results.

### Validity checks

- Replaying a seed/action prefix must reproduce the saved pre-decision observation hash and engine tick.
- Candidate actions must be legal under the same mask and action schema presented to the agent.
- Candidate-generation code, coordinates, continuation policies, opponents, horizons and value function must be versioned and hashed.
- The candidate set must be balanced and not handcrafted separately for a model.
- If the agent's action is invalid or outside the candidate support, report it separately. Do not silently snap or repair it.
- Bootstrap at the state/seed-cluster level, not by treating all rollouts from one state as independent samples.
- Validate the metric on a small expert-reviewed set of tactical states. Human ratings are external face-validity evidence, not the numeric oracle.

### Deliverables

- A replay-based state reconstruction utility.
- A deterministic scenario manifest containing source match, seed, seat, decision ID, engine tick, observation hash and candidate-set version.
- A counterfactual rollout runner.
- Candidate-set regret and uncertainty metrics.
- Unit tests for exact prefix reconstruction, action validity, matched pairing and metric determinism.
- A report showing whether counterfactual action quality explains, complements or disagrees with aggregate competitive ranking.

This diagnostic is the highest-priority research addition after v1 acceptance. If replay reconstruction is not reliable by the end of the first research sprint, do not publish approximate counterfactual claims. Fall back to clearly labelled fixed-state tactical tasks and narrow the paper's claim.

---

## 6. Baseline agents: a benchmark needs more than two scripts

Use a fixed, auditable baseline suite. The goal is not to maximise the number of named models; it is to span qualitatively different policy classes.

### Required policy families

1. **Random-legal floor:** the existing random-legal agent. Retain it as a sanity check, not as the main opponent.
2. **Rule-based baseline:** the existing Hog-cycle policy for the Hog deck.
3. **Deck-aware heuristic:** a transparent, deterministic controller for each research archetype. It should account for playable card roles, elixir, known opponent cycle, defensive versus offensive state and legal placements. Publish all rules.
4. **Learned policy:** train at least one PPO-style policy on the same CRForge engine and ObservationV1/action interface. Train on training seed groups only; choose checkpoints/hyperparameters on validation groups; freeze one or more checkpoints before final test. Use action masks and a compact structured-state encoder. A small model is preferable to an unrepeatable compute-heavy policy.
5. **LLM agents:** evaluate at least two or three meaningfully different model families if API budget permits. Freeze provider, exact model ID/snapshot where available, system/developer prompt, observation rendering, JSON schema, temperature, top-p, token limit, retry behaviour and request timestamp. Report tokens, cost and latency separately from strategic score.

### Optional but valuable

- A human/high-skill player baseline or a small expert-reviewed tactical-state set. Recruit more than one annotator for the reviewed subset, report annotator agreement, and compensate external work appropriately.
- An existing public Clash Royale model such as ClashAI only if its source/checkpoint licence, game-data version, observation semantics and action mapping can be verified. RoyaleSim/CRForge result scores must not be pooled across engines.
- A second learned policy with different training data or architecture if it is necessary to test generalization rather than merely show one learned point.

### Training rules

- Training, validation and final test seed groups must be disjoint.
- If a policy is trained on a deck-specific distribution, identify that explicitly. Use held-out archetypes or matchups to test transfer.
- Never tune policies, prompts or thresholds against final test outcomes.
- Save model weights, source commit, training configuration, training seeds, validation selection criterion and checkpoint hash.
- The benchmark runtime should not require PyTorch or a training stack to run a submitted frozen checkpoint. Keep training dependencies optional.

---

## 7. Public-memory estimation and ablation study

The existing FAIR observation contract supplies player-visible information and a common public-memory block. Test the value of that design directly.

Evaluate at least these matched conditions:

1. **Full ObservationV1:** current public-memory and observation representation.
2. **No derived opponent memory:** remove estimated opponent cycle/elixir fields but retain raw player-visible events.
3. **Raw history condition:** supply a bounded raw public-event history without the derived summary, if this can be made protocol-equivalent.
4. **Corruption/sensitivity condition:** perturb or omit selected public events in a controlled way to measure reliance and calibration. Do not call this an official leaderboard score.

Primary measures:
- match score and candidate-set action regret;
- opponent-elixir estimation error and calibration;
- card-cycle/next-card prediction accuracy where identifiable;
- action legality and failed-action rate;
- performance stratified by whether cycle/resource information is decision-relevant.

Keep the information budget matched. Do not give one condition a longer transcript or more simulator state than another without stating that as a separate intervention.

---

## 7.1 Competency-focused diagnostic suite

The diagnostic layer should become a structured suite of controlled scenarios rather than one scalar score. RTSGameBench already demonstrates the value of full-game matchups plus competency-focused mini-games and scenario generation; RoyaleBench must differentiate through its competitive 1v1 setting, identical-state modality comparisons, explicit FAIR information boundary, paired seat/control design and simulator-grounded counterfactuals. Do not claim that competency mini-games themselves are new. See https://arxiv.org/abs/2606.18950.

Each scenario must be generated from a valid engine state or a replay prefix, serialized with a manifest, and validated by reconstructing the exact initial observation hash. Scenario construction may inspect simulator truth to label and stratify examples, but the agent input must contain only the information allowed by its track.

| Competency | Scenario construction | Primary measurement | Main failure mode exposed |
|---|---|---|---|
| Resource management | Freeze states at different own/opponent elixir levels, hand compositions and incoming threats; include constrained response choices | Candidate-set regret, elixir spent/wasted, defensive survival and opportunity cost | Overcommitment, inefficient cycling, poor trade decisions |
| Opponent modelling | Replay prefixes with different hidden cycles that induce distinguishable public play histories; request a distribution over possible opponent hand/cycle states | Brier score, log loss, calibration, top-k accuracy on identifiable targets; downstream action-regret difference | Treating uncertain opponent information as known; poor inference from partial histories |
| Spatial reasoning | Create states with multiple legal defensive/offensive placements and controlled threat trajectories | Placement regret under matched continuations, landing-point error where applicable, tower/unit damage avoided or achieved | Correct card but wrong location, range or lane |
| Temporal planning | Construct situations with known projectile/unit travel, command delay, observation cadence and time-to-impact | Timing regret, response delay, prevented damage and survival under controlled continuations | Acting too early/late, ignoring delayed actions or threats |
| Adaptation | Switch the opponent controller at a hidden, predeclared match point between distinct policy families | Adaptation lag, post-switch paired score, recovery curve and action-value change | Static policy, delayed strategy recognition, overfitting |
| Long-horizon planning | Evaluate sequences where immediate elixir/tower trades affect later states; sample multiple horizons from replayed states | Horizon-dependent candidate-set regret, terminal score and value consistency | Greedy local plays, failure to preserve future options |

Do not force all six diagnostics into a single aggregate benchmark score. Publish the per-competency vector, confidence intervals and the exact scenario support. If a scalar summary is useful, report it only as a secondary normalized composite with its weighting fixed in advance.

### Scenario-generation requirements

- Sample states across game phase, elixir, hand composition, tower-health asymmetry, entity density, deck matchup and opponent archetype.
- Balance easy, medium and difficult states using engine-grounded properties, not the target models' observed performance.
- Separate development scenarios, validation scenarios and a held-out diagnostic test set by source match and seed cluster.
- Include paired seat-frame transforms where the scenario should be symmetric.
- Require deterministic replay reconstruction and store initial-observation hashes.
- Retain hard, ambiguous and no-good-action cases; do not curate only visually obvious tactical problems.
- Make scenario generation deterministic from a published seed and configuration.

## 7.2 Visual and structured-state paired track

Promote a visual observation track from a distant future idea into a major research work package. It is a strong differentiator for an agent-evaluation paper, but it must be a genuinely controlled comparison rather than simply running a VLM on unrelated matches.

### Core question

How much performance is lost when the same agent family must infer the game state from rendered observations rather than receiving a structured FAIR state? Can the loss be attributed to perception, temporal state estimation, action grounding or strategic reasoning?

### Track design

1. **Structured FAIR track:** the current ObservationV1 input.
2. **Visual single-frame track:** one deterministic screenshot per decision, from the acting seat's perspective.
3. **Visual temporal track:** a fixed, documented number of previous frames at fixed simulation intervals, with no privileged event history.
4. **Optional hybrid track:** screenshot plus a small common public-memory summary. This is a separate track because it supplies derived state beyond pixels.

Use at least one multimodal model family capable of accepting both text-only structured observations and images. Evaluate that same model/version on matched states in structured and visual modes to isolate modality effects as much as practical. Then evaluate additional VLM families in the visual track. Match the action schema, candidate choices, opponent, seed, seat, decision cadence and output validation. For full games, use paired seeds and seat swaps; for tactical diagnostics, use the exact same reconstructed state for both modalities.

### Renderer and visual information contract

- Build or adapt a deterministic renderer whose board frame, card slots, elixir, towers, timer, effects and visible entities are stable across runs.
- The rendered image must encode only information available to that player. It must not reveal hidden hand, hidden elixir, future state, RNG state, hidden entity HP or the other seat's observation.
- Prefer original, redistributable visual assets. Do not place Supercell artwork, sounds, logos or proprietary game tables in the public artifact unless a licence explicitly permits redistribution. A neutral custom renderer is acceptable if this limitation is documented.
- Version the renderer, resolution, frame rate, camera transform, HUD, fonts, animation sampling and screenshot encoding. Hash renderer configuration and generated frames.
- Establish deterministic mapping from the agent's output coordinates to the common ActionV1 grid. Do not let a visual agent use a larger or strategically filtered action set.
- Define whether a visual model receives one image, a frame stack or video. Fix this across comparisons and record image dimensions, temporal spacing and token/frame budget.

### Decomposing visual-agent errors

Use engine truth only as an evaluator-side label to decompose failure:

- **Perception:** card identity, entity detection/count, entity position, tower health, elixir and timer estimation. Report precision/recall/F1 or MAE as appropriate.
- **Temporal estimation:** tracking stable entity identities, motion/velocity and event timing across frames. Report association accuracy and position/velocity error.
- **Action grounding:** difference between intended screen/board location and the encoded ActionV1 hand slot/tile coordinate, invalid-action rate and placement rejection.
- **Strategic choice:** candidate-set regret conditioned on the same true state and candidate set.
- **End-to-end outcome:** cross-play score and matchup-conditioned ranking.

The key analysis is not simply visual-versus-structured win rate. It is whether errors in perception and temporal state estimation explain the gap in action quality and match performance. Use state-matched paired analyses and report when a visual agent's strategic choice is good given its estimated state but the estimate itself is wrong.

### Visual-track exit gate

- Renderer determinism and visibility audit pass.
- Same underlying states are available to visual and structured evaluators.
- At least two VLMs can complete the protocol, or the paper explicitly labels a smaller pilot.
- One model family is evaluated in both modalities with matched prompt/action settings.
- Perception, action-grounding, tactical-regret and competitive metrics are all available.
- Asset provenance and redistribution permissions are documented.

Do not let the visual renderer delay the frozen v1 acceptance. It is a research-layer component and must be versioned independently.
---

## 7.3 A real world-model evaluation track

The current persistence forecaster is only a sanity baseline. For a benchmark intended to measure planning and strategic intelligence, add a genuine learned dynamics/prediction track rather than treating persistence as a world-model result.

### Separate prediction tasks

1. **Action-conditioned dynamics prediction:** predict future visible observations given a source observation and a declared action sequence. If both players' future actions are supplied, label this teacher-forced conditional dynamics prediction; it does not measure opponent modelling.
2. **Opponent-action prediction:** predict the opponent's action distribution from the agent's observation and past public history only. Do not pass the actual future opponent action to the predictor.
3. **Planning utility:** use a predicted model inside a fixed planner and measure the actual outcome/action quality of the resulting decisions under the exact simulator. Prediction accuracy and control utility are separate outcomes.

### Baseline models

- Persistence baseline (already implemented).
- Constant-velocity / deterministic entity extrapolation baseline.
- Entity-tracking plus event-rule baseline, where supported by visible state.
- Compact recurrent predictor.
- Entity-token Transformer or another learned action-conditioned model.
- Optional model-based planner that uses predictions to rank candidate actions and then verifies top actions against CRForge.

### Metrics

- Entity existence, type and stable-identity precision/recall/F1.
- Position and velocity error in tile units, with matched-entity reporting.
- Visible unit HP and tower HP MAE.
- Own and public-estimated opponent resource MAE and calibration.
- Entity-count error and overflow/truncation rate.
- Event classification and event-time error for public card plays, deaths, projectile launches/impacts and tower damage where the event contract supports unambiguous identity.
- Multi-horizon error and uncertainty calibration; report error accumulation rather than only one-step accuracy.
- Downstream candidate-set regret and actual match performance when the predictor is used for planning.

Use match/seed-cluster-separated train, validation and hidden test sets. The predictor must not receive future observations, future outcomes or hidden simulator state. If a joint future action sequence is used for dynamics evaluation, identify it as teacher forcing and keep it separate from the opponent-modelling task.

### Scientific question

Does lower multi-step prediction error improve strategic decisions, or can a model be more accurate on average while being worse on strategically decisive events? The planning-utility experiment is what makes this track scientifically meaningful. Do not claim that a forecaster is a stronger agent until it is integrated into a policy and evaluated in actual competition.

---

## 7.4 Parallel engine and external-policy tracks

RoyaleGym/RoyaleSim, FirstLight, Hasty-CR and ClashAI should be investigated as independent sources of environment implementations, policies, checkpoints and training methodology. Their existence is useful for both related work and external baselines. Integration is conditional on source/checkpoint licensing and a defensible observation/action mapping.

### Parallel engine evaluation

- Keep CRForge as the canonical engine for the frozen v1 track.
- Build a separate RoyaleSim/RoyaleGym adapter only after confirming version, rules, deck mechanics, action semantics, player-visible information and deterministic replay support.
- Publish separate engine-specific matchups, ratings and manifests. Never combine raw ratings or win rates across CRForge and RoyaleSim when the game mechanics or data fingerprints differ.
- Where a common policy can run on both engines through a tested adapter, report cross-engine transfer as an explicit generalization experiment, not as one merged leaderboard.
- Treat engine disagreement as an empirical robustness result. Reconstruct comparable states only when the semantics are genuinely equivalent.

### External policy integrations

- Inspect FirstLight and Hasty-CR for public checkpoints, training data provenance, licences, game version, action interface and information access.
- Inspect ClashAI for imitation/RL baselines and reusable training ideas; verify code and checkpoint licences before reuse.
- A policy requiring privileged simulator state, a different card/version vocabulary or non-equivalent action semantics cannot be called a compatible CRForge baseline.
- If a policy cannot be translated losslessly, run it only in its native, separately labelled engine track, or cite it as related work.
- Record the exact code commit, checkpoint hash, preprocessing, observation mode and adapter version for every imported baseline.

### What this adds

The objective is not the largest number of engines or policies. It is to test whether conclusions survive a second implementation and whether existing public agents can be compared without silently changing their information or action interface. This is a stretch work package after the core CRForge evaluation is reliable.
---

## 8. Competitive protocol and statistical analysis

### Match schedule

For every agent pair, deck matchup and seed:
- run both seat assignments;
- use the same frozen engine/data fingerprint;
- record all seeds and action/cadence settings;
- use unique match IDs;
- record wins, draws, losses, voids and technical failures separately.

Do not turn timeouts, invalid output, simulator faults or entity-overflow voids into strategic losses. Report technical reliability as its own outcome.

### Metrics

**Primary competitive measures**
- per-agent win/draw/loss;
- paired score (win = 1, draw = 0.5, loss = 0);
- pairwise cross-play matrix;
- Glicko-2 rating and rating deviation within each declared profile;
- per-deck and per-matchup scores.

**Primary diagnostic measure**
- rollout-based candidate-set regret, with state/seed-cluster confidence intervals.

**Secondary measures**
- ranking/rank correlation across matchup strata;
- seat advantage;
- action invalid/rejection rate;
- entity-overflow and void rate;
- opponent-cycle and elixir estimation error;
- cadence-conditioned request count;
- latency/token/cost reporting for hosted agents;
- prediction metrics if a trained forecaster is included.

Never combine forecasting quality and competitive ratings into one scalar.

### Statistical design

The independent unit for uncertainty is the simulator seed cluster, preserving both seat-swapped matches and all linked matchups from that seed. Do not compute confidence intervals by treating individual decisions or individual rollouts as independent.

Before final evaluation:
1. run a pilot on a disjoint pilot seed set;
2. estimate variance and seed-to-seed dispersion;
3. choose final seed counts to obtain a predeclared confidence-interval precision or power for the primary comparisons;
4. publish the stopping/sample-size rule before inspecting final test results.

Use a stratified cluster bootstrap over seed groups for 95% confidence intervals. For head-to-head conclusions, bootstrap the **paired difference** between agents, not two separate unpaired mean intervals. Use a paired permutation/randomization test as a robustness check where appropriate. Correct families of secondary pairwise tests with Holm or another predeclared method. Report effect sizes and intervals, not only p-values.

A reasonable planning range is **50–100 independent seed groups per key matchup** as an initial target, then refine from the pilot and compute/API budget. This is a planning range, not a universal minimum. Use fewer for expensive hosted-model sweeps only if the paper reports the wider uncertainty and limits its claims.

### Avoid a statistical trap in the current code

The current tournament runner computes per-agent seed-cluster score intervals. The ICML analysis also needs paired agent-vs-agent score-difference intervals, deck/matchup-stratified estimates, and an auditable table of seed-cluster results. Implement these as explicit output artefacts rather than deriving them manually in a notebook.

---

## 9. Implementation work packages

Keep the current v1 acceptance surface stable. Add the research suite behind a new config/schema version.

### WP0 — Fix bootstrap and complete v1 native acceptance

**Priority:** blocker  
**Target:** 18–22 November

- [x] Replace the duplicated hardcoded SHA comparison with a comparison against each submodule commit recorded by git ls-tree HEAD in the superproject.
- [x] Verify the updated PowerShell validation script on the user's Windows installation.
- [x] Complete the local integrated validation run (2026-11-18; the existing engine build was reused with `-SkipBuild`).
- [x] Confirm all three `tests/test_crforge_native.py` cases execute with zero skips.
- [x] Confirm upstream CRForge `:env:test`, all Python tests (120 passed), Ruff and config validation pass.
- [x] Complete both six-match headless tournaments, trajectory export and persistence forecasting.
- [x] Preserve the complete local run directory `results/validation-20261118-171426/`, including validation report, JUnit report, Gradle test report and generated outputs.
- [ ] Fix genuine failures at their source; never weaken acceptance checks merely to obtain a green run.

**Exit gate:** a complete local Windows validation report with all expected matches, non-empty splits, forecast examples at every horizon and no failed/void acceptance matches.

### WP1 — Lock scientific questions, protocol and paper positioning

**Priority:** blocker for research scope  
**Target:** 19–26 November

- [ ] Complete the related-work matrix covering RTSGameBench, BALROG, GAMA-Bench, AgentBench, MultiAgentBench, GameBench, RoyaleGym/RoyaleSim and CRForge.
- [ ] Write a one-page novelty memo that says exactly what this benchmark measures that those systems do not.
- [ ] Freeze the primary research questions and hypotheses in this plan or a dated protocol amendment.
- [ ] Decide exact deck archetypes by checking every card/mechanic against the pinned CRForge implementation.
- [ ] Decide which cadence profile is primary for each agent family. Never call cadence an inference-time budget.
- [ ] Specify all primary outcomes, exclusions, bootstrap clusters and sample-size rule before the final test run.

**Exit gate:** every planned experiment maps to a hypothesis, metric and data source. Remove any feature that does not support one.

### WP2 — Research deck/matchup configuration

**Priority:** high  
**Target:** 24 November–5 December

- [ ] Add a versioned research configuration that can describe multiple deck archetypes without changing v1 defaults.
- [ ] Select and validate three distinct classic archetypes; add a fourth only if card fidelity and time permit.
- [ ] Add mirror and cross-archetype matchup scheduling.
- [ ] Preserve both-seat swaps within each seed/matchup cluster.
- [ ] Add deck_id, matchup_id, ordered deck lists, levels and deck/configuration hashes to match and tournament manifests.
- [ ] Ensure every deck and matchup is visible in result summaries and leaderboard rows.
- [ ] Update dataset records/manifests with the deck and matchup provenance required to stratify analyses.
- [ ] Ensure seed groups remain assigned wholly to one dataset partition across all matchups and both seats.
- [ ] Add tests for schedule completeness, symmetry, provenance, reproducibility and no cross-split seed leakage.

**Exit gate:** the research tournament can run the complete deck/matchup matrix and produce a machine-auditable summary.

### WP3 — Counterfactual tactical diagnostic

**Priority:** highest research novelty  
**Target:** 27 November–12 December

- [ ] Implement deterministic seed-plus-action-prefix state reconstruction.
- [ ] Verify reconstructed observation hash and tick against the original trajectory.
- [ ] Build a versioned candidate-action generator using only legal, supported actions.
- [ ] Implement intervention rollouts with fixed opponent/continuation policies.
- [ ] Compute candidate-set regret, paired action-value differences and uncertainty.
- [ ] Build a stratified scenario corpus across game phase, elixir, tower-health situation, deck matchup and observed opponent strategy.
- [ ] Implement competency-specific resource-management, opponent-cycle inference, spatial-placement and temporal-response tasks; add adaptation-switch tasks if robust scenario generation is available.
- [ ] Verify metric stability under alternative continuation policies and opponent pools.
- [ ] Add a small independent expert review for face validity if suitable expert annotators are available.
- [ ] Publish candidate-set limitations; do not call the metric optimal regret or Nash exploitability.

**Exit gate:** same seed/prefix/action reproduces the same state; intervention comparisons are paired; candidate generation is deterministic; test scenarios are disjoint from the final test matches.

### WP4 — Agent baselines

**Priority:** high  
**Target:** 1–16 December

- [ ] Retain random-legal and current Hog-cycle rules.
- [ ] Implement deck-aware heuristic baselines for the additional archetypes.
- [ ] Train a compact masked behaviour-cloning / imitation policy on verified demonstrations.
- [ ] Train at least one compact masked PPO policy on CRForge using training seed groups.
- [ ] Implement a deterministic short-horizon search baseline using candidate actions and fixed continuation policies.
- [ ] Evaluate validation checkpoints and freeze the chosen checkpoint before the final test.
- [ ] Run frozen LLM and VLM model families; compare at least one multimodal family in both structured-text and screenshot modes on matched states.
- [ ] Record prompts, model IDs, endpoint/provider, decoding, retries, timestamps, token usage, cost and output validation.
- [ ] Test reproducibility and seed generalization of the learned policy.
- [ ] Audit external public policy code/checkpoints for licensing and semantic compatibility. Do not force incompatible RoyaleSim/FirstLight/Hasty policies into CRForge's leaderboard.

**Exit gate:** each final baseline has a named version, source/config/checkpoint hash, training protocol and a reproducible execution path.

### WP5 — Memory, cadence and robustness experiments

**Priority:** high  
**Target:** 8–19 December

- [ ] Run full versus no-derived-memory ablations.
- [ ] Run raw-event-history versus summarized-memory only if the information budget can be matched.
- [ ] Run controlled public-event corruption/omission experiments.
- [ ] Complete matched visual-versus-structured evaluations and decompose perception, temporal tracking, action-grounding and strategic-choice errors.
- [ ] Compare 5-tick and 20-tick cadence as simulation-frequency settings, keeping separate ratings.
- [ ] Analyse performance by deck, matchup, opponent family and seat.
- [ ] Measure whether an agent's ranking changes between mirror and cross-archetype play.
- [ ] Report technical failures and action validity independently from strategic score.

**Exit gate:** all ablations are paired, seed-matched and tied to explicit hypotheses.

### WP6 — Pilot, final evaluation and statistics

**Priority:** blocker for results  
**Target:** 15 December–5 January

- [ ] Run pilot seed groups; estimate dispersion and between-seed variation.
- [ ] Choose final sample sizes using the predeclared confidence-interval precision/power rule.
- [ ] Freeze test seed groups and protect them from training and prompt tuning.
- [ ] Freeze the complete agent pool, deck suite, prompts, checkpoints, candidate sets and analysis code.
- [ ] Run the full cross-play tournament and diagnostic rollouts.
- [ ] Re-run a small subset from scratch to verify deterministic reproducibility.
- [ ] Generate paired score-difference CIs, stratified matchup results, Glicko-2/RD tables, action-regret results and failure-rate summaries.
- [ ] Correct secondary multiple comparisons.
- [ ] Store raw match logs, manifests, compressed trajectories, counterfactual traces and machine-generated result tables.

**Exit gate:** all paper claims are directly traceable to immutable result artefacts and the final analysis script.

### WP7 — Paper and artifact freeze

**Priority:** submission blocker  
**Target:** 2–22 January

- [ ] Draft the paper while experiments run; do not wait until the result phase to start writing.
- [ ] Produce final diagrams and figures directly from the experiment artefacts.
- [ ] Run a full internal red-team review: novelty, statistical independence, simulator validity, hidden-state leakage, licensing, reproducibility and overclaiming.
- [ ] Create an anonymized artifact/reproduction package for double-blind review.
- [ ] Prepare the required AI Disclosure Statement and broader-impact statement.
- [ ] Finalize author list before the abstract deadline.
- [ ] Submit a genuine abstract by 14 January AoE.
- [ ] Freeze the 8-page main paper by 22 January AoE.

---

## 10. Experiment matrix

The following is the intended minimum research matrix. The exact number of seed groups is determined by the pilot and precision target.

| Dimension | Required conditions | Main question |
|---|---|---|
| Deck archetypes | 3 verified archetypes | Does strategic style matter? |
| Matchups | mirror and all cross-archetype pairs | Does ranking generalize across matchups? |
| Seats | both seat assignments per seed | Is there a seat/frame advantage? |
| Agents | random, rules, deck-aware heuristic, PPO, LLM(s) | How do policy families compare? |
| Cadence | 5-tick and 20-tick profiles where appropriate | Does observation frequency change strategy? |
| Memory | full, no-derived-memory, optional raw-history | Does common public memory help? |
| Tactical states | stratified state corpus and candidate actions | Does local decision quality agree with match score? |
| Opponents | multiple fixed and learned opponent families | Is the agent specialized or robust? |
| Reproducibility | repeated seed/prefix replays | Are the measurements deterministic? |

A full Cartesian product can be too expensive, particularly for hosted LLMs. Use a declared tiered design:

- **Tier 1, full benchmark:** lightweight deterministic and learned policies across every deck/matchup stratum.
- **Tier 2, costly hosted models:** focus on the primary matchup strata and a sample size justified by pilot uncertainty.
- **Tier 3, diagnostics:** sample states stratified across all decks and matchups, with a controlled fixed opponent pool.

Report exactly which agent was run in which conditions. Do not present a partial matrix as if every model was evaluated everywhere.

---

## 11. Data, reproducibility and release artifacts

Required artefacts:

1. Versioned config files for every deck, matchup and cadence.
2. Engine source commit and game-data content SHA.
3. Exact run manifest, seed groups, seat swaps and schedule.
4. Agent source/model/checkpoint hashes and all configuration.
5. Prompt and provider configuration for hosted LLMs, excluding secrets.
6. Raw per-match manifests, results and trajectories.
7. Dataset manifest with split membership and SHA-256 per shard.
8. Scenario corpus manifest and observation hashes.
9. Counterfactual candidate-action and rollout records.
10. Analysis scripts, environment lock files and machine-generated paper tables.
11. A single reproduction command for the published main tables.
12. A limitations and benchmark card that names unsupported mechanics, game-data limitations and intended use.

The game tables/assets remain subject to upstream and game-owner terms. Do not redistribute copyrighted game assets or imply endorsement by Supercell. Keep source and game-data licensing distinctions explicit. The benchmark is an offline simulator evaluation, not live-game account automation.

---

## 12. Eight-page paper structure

Use the main eight pages for scientific claims, not for a long tour of every software module.

**1. Introduction (about 1 page)**  
Explain why strategic-agent evaluation under partial observability and competitive interaction is difficult. State the gap, thesis, contributions and research questions. Do not claim there is no prior game benchmark.

**2. Related Work (about 0.75 page)**  
Compare game-agent benchmarks, RTS/VLM benchmarks, multi-agent evaluations, Clash Royale environments and competitive rating methods. Focus on differentiating assumptions and evaluation methodology.

**3. Environment and Benchmark Design (about 1.25 pages)**  
Describe CRForge as the upstream engine, the FAIR ObservationV1 contract, action semantics, decks, matchups, paired seat swaps, simulation cadence and reproducibility contract.

**4. Counterfactual Evaluation Method (about 1.25 pages)**  
Define scenario reconstruction, candidate action sets, rollout continuation policies, candidate-set regret and uncertainty. State exactly what the metric does and does not estimate.

**5. Agents and Experimental Protocol (about 1 page)**  
Describe rules, PPO and LLM baselines, data splits, seed clusters, prompts/checkpoints and statistical analysis.

**6. Results (about 1.5 pages)**  
Show the cross-play matrix and matchup-conditioned ranking; action-quality diagnostics; memory/cadence results; uncertainty and failure rates.

**7. Analysis and Limitations (about 0.75 page)**  
Discuss rank reversals, specialization, simulator dependence, candidate-set dependence, model API reproducibility, the restricted deck set and what cannot be inferred.

**8. Conclusion (about 0.25 page)**  
Summarize the benchmark's scientific utility and supported conclusions.

The appendix should include full deck lists, card/mechanic audit, schemas, exact prompts, extra statistical tables, candidate-set construction, ablations, model configurations, hyperparameters, data examples and full reproducibility instructions.

### Main figures and tables

- **Figure 1:** benchmark architecture and information/action boundary.
- **Figure 2:** deterministic replay and counterfactual intervention protocol.
- **Figure 3:** cross-play matrix / agent ranking by deck matchup.
- **Figure 4:** match score versus candidate-set regret, with uncertainty.
- **Figure 5:** public-memory ablation and cadence interaction.
- **Table 1:** prior benchmark comparison and capability coverage.
- **Table 2:** exact experimental agent pool and training/evaluation provenance.
- **Table 3:** aggregate and matchup-conditioned W/D/L, Glicko-2/RD and paired CIs.
- **Table 4:** counterfactual decision quality and robustness results.

Do not fill figures with unverified claims. Empty placeholders are acceptable during drafting, not for submission.

---

## 13. What would make this spotlight / best-paper competitive?

A spotlight or award-level benchmark paper needs a finding that changes how researchers evaluate agents, not merely a large repository.

The strongest possible outcome would be evidence for a general lesson such as:

- agent rankings based on match outcomes are not reliable across opponent/deck distributions;
- local tactical decision quality and full-game win rates reveal materially different strengths;
- common public-memory assistance benefits specific decision classes, not all states uniformly;
- agents overfit to an opponent archetype and fail under controlled strategic shifts;
- current LLM agents can produce syntactically valid legal actions yet systematically underperform on resource/cycle/spatial diagnostics.

These are examples of informative results, not promised findings. The results may contradict them.

**Best-paper stretch criteria:**
1. A clearly novel and reproducible evaluation method, not just a new implementation.
2. A verified multi-archetype benchmark with true cross-play.
3. Strong baselines including a learned policy and frozen language-model policies.
4. Seed-clustered statistical analysis and transparent uncertainty.
5. A convincing relationship (or meaningful disagreement) between competitive outcomes and decision-level diagnostics.
6. An empirical conclusion relevant to the wider ML agent-evaluation community.
7. A polished, anonymized, reproducible release with complete model/data provenance.

Do not build unrelated infrastructure to chase a best-paper label. Depth of evidence is more valuable than adding visual input, a second engine or dozens of weak baselines.

No acceptance, spotlight or award outcome can be guaranteed. A narrow one-deck leaderboard with a few LLM scores is not a realistic best-paper package.

---

## 13.1 Minimum publishable package versus spotlight stretch

The full Cartesian experiment matrix is not a requirement to execute every possible combination. Use the following hard priority split to protect the deadline.

### Minimum package for a credible ICML main-track submission

- Full local v1 native acceptance, with all three CRForge native adapter tests executed.
- Three validated archetypes, mirror and cross-archetype matchups, both seats and seed-clustered analysis.
- A deterministic redistributable visual renderer and screenshot-only FAIR track, separate from the structured ObservationV1 track.
- A same-model-family paired modality study on identical reconstructed states, with at least two VLM families if the API/compute budget permits.
- Competency diagnostics for at least four dimensions: resource management, opponent modelling, spatial reasoning and temporal planning. Adaptation and long-horizon planning should be added if the scenario/replay tooling is reliable.
- A transparent deck-aware heuristic, a short-horizon search baseline, an imitation-learning policy and one learned PPO policy, in addition to existing rules/random baselines.
- At least one serious frozen LLM participant and at least one VLM participant; two or more model families per modality are preferred when budget permits.
- Deterministic replay-prefix reconstruction and candidate-set regret on a stratified state set.
- One controlled public-memory ablation.
- Pilot-derived final sample size and paired score-difference intervals.
- One reproducible command/script for the principal paper tables.

A submission missing deterministic simulator validation, genuine cross-matchup evaluation, matched visual/structured comparisons or meaningful uncertainty is not rescued by adding more model names or a larger repository.

### Spotlight / award stretch

- Four verified archetypes rather than three.
- Two independently trained learned policies (for example, different training distributions or recurrent versus feed-forward policy).
- Three or more frozen LLM families with full cost/latency accounting.
- Independent expert review of a tactical-state subset with inter-rater agreement.
- Stability analysis of candidate-set regret under multiple continuation policies and opponents.
- A real learned world-model track with event-aware, multi-horizon metrics and a downstream planning-utility experiment.
- A separately reported RoyaleSim/RoyaleGym replication track or a compatible external-policy evaluation, with no cross-engine rating pooling.
- A clear, statistically robust finding about ranking reversals, hidden specialization or the gap between match outcome and tactical decision quality.
- A polished public benchmark package, reproducibility script and external users reproducing a subset before submission.

### What to cut first if the schedule slips

Cut, in this order:
1. fourth deck archetype;
2. optional trained forecaster;
3. third and subsequent hosted LLM models;
4. human full-match baseline (retain a small expert-reviewed diagnostic subset only if feasible);
5. secondary cadence or corruption ablations not tied to a primary hypothesis.

Do **not** cut:
- full native engine acceptance;
- the third archetype without an explicit reason and a correspondingly narrower claim;
- paired seat swaps and seed-cluster uncertainty;
- at least one real learned policy;
- deterministic replay validation for the counterfactual metric;
- the final held-out test separation.

If the counterfactual evaluator cannot be validated, the paper must change its central claim and become a narrower benchmark paper. It must not retain the counterfactual title or claims based only on approximate replay.

---

## 14. Explicitly out of scope before ICML submission

Do not spend the first ICML benchmark-paper schedule on:
- live Clash Royale client/account integration or unauthorized public-match automation;
- pooling RoyaleSim and CRForge ratings. A second engine may be added as a separately reported replication/transfer track only after the primary CRForge evaluation is complete and semantic compatibility is demonstrated;
- full deck-building or automatic deck search, unless a specific deck-generalization question requires a tightly controlled subset;
- the large-scale league-training programme for the eventual elite player (that belongs to Project Crown and the second paper);
- online public submissions or a secure multi-tenant sandbox;
- building a custom battle engine instead of using validated upstream engines;
- a large learned world-model stack that is not connected to a specific prediction or planning question;
- claims of general game intelligence, human-level play or professional-level play without direct evidence.

The visual renderer, screenshot track, competency diagnostics, small PPO/imitation/search baselines and a focused world-model study are now in scope for the ICML benchmark paper. The external process adapter is not an OS security sandbox. Do not invite untrusted public code until proper isolation is implemented.

---

## 15. Risks and fallback decisions

| Risk | Consequence | Response |
|---|---|---|
| CRForge bootstrap/runtime acceptance still fails | No trustworthy experimental engine | Fix only the native integration/build issue first; do not start large evaluation |
| Additional decks use unsupported mechanics | Invalid cross-deck conclusions | Restrict the deck suite to mechanics that pass native fidelity tests |
| Replay-prefix reconstruction is not deterministic | Counterfactual metric invalid | Block the metric; use fixed-state tasks only if their initial state can be reconstructed and verified |
| PPO baseline is weak or unstable | Misleading learned-agent comparison | Report training budget and seeds, add a second baseline only if reproducible; do not claim SOTA |
| Hosted LLM cost exceeds budget | Incomplete model matrix | Use a smaller preregistered subset and report uncertainty/cost honestly |
| API model versions change | Results not reproducible | Pin snapshots where possible, archive exact requests/responses and run timestamps |
| Pilot uncertainty remains large | Underpowered results | Reduce secondary claims, add seed groups if feasible, or submit a narrower result |
| Related work already covers an intended novelty | Weak originality | Pivot the claim to the unique counterfactual/FAIR competitive evaluation method, not benchmark breadth alone |
| No robust scientific finding emerges | A leaderboard-only paper | Do not manufacture an insight; consider a later venue after additional experiments |

### Submission go/no-go

By **5 January 2027**, the project should have:
- complete engine acceptance;
- verified research decks;
- all baseline families running;
- counterfactual diagnostic validated;
- pilot results supporting the final sample-size decision;
- frozen test protocol.

By **10 January 2027**, final results should be generated and reproducible. If not, narrow the paper's claims and experiment matrix; do not fill the paper with smoke-test numbers.

By **14 January 2027**, submit a complete, accurate abstract with the final author list. The abstract must not promise experiments that will not finish by the full deadline.

By **18 January 2027**, the complete paper should be internally frozen for critical review. Use 19–21 January only for corrections, reproducibility checks and formatting, not for starting a new experiment.

---

## 15.1 Separate follow-on agent paper

The long-term agent-building programme is deliberately separate from this benchmark/evaluation paper. Its detailed research and engineering plan is in [agent_research_plan.md](agent_research_plan.md). The benchmark paper should produce the trusted measurement infrastructure; the follow-on paper should use expert imitation, league self-play, opponent modelling and model-based search to develop a genuinely strong player. Do not claim elite-human performance until a controlled, repeated challenge establishes it.

## 16. Immediate next actions

1. Preserve the successful v1 acceptance artifact and keep the current v1 configuration frozen. Do not use the three-seed smoke output as paper evidence.
2. Complete WP1 (19–26 November): related-work comparison, one-page novelty memo, explicit research questions/hypotheses, verified candidate decks, primary outcomes and predeclared statistical protocol.
3. Audit the baseline anomaly: random-legal won 5/6 against the in-process Hog-cycle baseline and 6/6 against the JSONL Hog worker. Check policy logic, worker/in-process parity and action traces before strength comparisons.
4. Create a separate research config and implement three engine-verified archetypes with mirror/cross-matchups and paired seat swaps.
5. Build deterministic seed-plus-action-prefix reconstruction and the counterfactual candidate-set regret diagnostic. Verify state hashes and ticks before interpreting the metric.
6. Add deck-aware, imitation, PPO, search and selected LLM/VLM baselines only where they support a frozen hypothesis.
7. Draft the Introduction, Related Work and Environment sections in parallel with WP1–WP3.

**Current status:** v1 software acceptance is complete. Scientific scope, research implementation, large-scale evaluation and submission readiness remain outstanding.
