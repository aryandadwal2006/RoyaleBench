# Project Crown: Research Plan for a Superhuman Clash Royale Agent

**Project:** RoyaleBench Agent Research  
**Version:** 1.0  
**Created:** 18 November 2026  
**Relationship to RoyaleBench:** Separate research programme and eventual second paper  
**Long-term objective:** Develop a competitive agent that can challenge elite human players under a fair, reproducible and authorized match protocol.

---

## 1. Mission and separation from the benchmark paper

The first RoyaleBench paper should establish the evaluation infrastructure and the scientific methodology for measuring strategic competence. This project is the separate agent-development programme that uses that infrastructure to build the strongest possible Clash Royale-playing system.

The ambition is an eventual public human-versus-agent challenge, with Mohamed Light as an aspirational target if he is willing and the match can be arranged under agreed rules. Beating one named player is not guaranteed, and a single match would not establish that an agent is generally superhuman. The target is to develop a reproducibly strong agent, then evaluate it against multiple high-level opponents and, if possible, conduct a properly controlled series against an elite professional.

Do not distort the benchmark paper to advertise an unfinished agent. The second paper should stand on actual competitive results, not on an ambition or demo.

### Candidate second-paper identity

**Working title:** Learning Competitive Play in Partially Observable Real-Time Card Battles through Expert Imitation, League Self-Play and Model-Based Search

Potential scientific contribution:
- a strong policy for a spatial, resource-constrained, partially observable two-player game;
- a reproducible combination of expert demonstrations, recurrent belief-state modelling, league self-play and simulator-grounded lookahead;
- a controlled analysis of which components actually produce elite performance;
- a human evaluation protocol with repeated matches, matchup diversity and uncertainty.

The paper must contain a method or a meaningful empirical finding. "We trained a Clash Royale bot and it won" is not enough by itself.

---

## 2. Define what "best player" means

Use a staged definition rather than one viral match:

1. **Engine competence:** reliably beats weak scripted baselines and does not exploit simulator bugs.
2. **Strategic competence:** beats strong transparent heuristics, imitation policies and independently trained RL opponents.
3. **Population robustness:** retains high performance against a diverse, frozen league rather than one exploitable opponent.
4. **Expert-level performance:** competes evenly with strong human players under a controlled ruleset and repeated series.
5. **Elite challenge:** achieves a statistically persuasive result against one or more top professional players, including Mohamed Light if a mutually agreed challenge is possible.

A "Deep Blue moment" should mean a well-documented, independently witnessed competition with a strong protocol, not an isolated cherry-picked game.

### Required competitive reporting

- complete match count and all outcomes, including draws and forfeits;
- fixed deck and matchup for each series, with deck choice and seat/side assignment controlled;
- exact game version, rules, card levels and environment;
- player handles/names only with consent;
- win-rate confidence intervals and per-match logs/replays where legally shareable;
- separate training, validation and held-out opponents;
- no selective exclusion of losses or unfavourable games.

A best-of-five or best-of-seven demonstration is useful for publicity but weak evidence. A research evaluation should have enough repeated games and matchup/side variation to estimate performance with uncertainty.

---

## 3. Non-negotiable environment and sim-to-real requirements

The current CRForge-based RoyaleBench v1 is the training and testing foundation, not proof that the learned agent will transfer perfectly to the official game.

Before training a high-performance policy:

- complete the native CRForge installation and integration acceptance;
- build a simulator fidelity dossier for every card and mechanic used by the agent's deck pool;
- reproduce recorded game traces where permitted and compare tick-level state changes;
- test determinism, action legality, player-command delay, targeting, placement relocation and terminal outcomes;
- compare the simulator's observations against actual player-visible information;
- maintain version-specific configs when game balance or mechanics change;
- record and analyse any mismatch between simulated and actual gameplay.

Do not train on unsupported cards, abilities, champions or evolutions and then infer live-game strength from simulator wins.

### Deployment constraint

The first serious agent should be developed and evaluated in the offline benchmark and in approved test environments. Any eventual live-client demonstration must use a sanctioned, authorized setup and comply with the game's rules and terms. Do not bypass anti-cheat, evade platform controls or automate unauthorized public matchmaking. If direct automated deployment is not permitted, use a controlled simulator match, an authorized exhibition environment, or a human operator who executes the agent's decisions with the rules disclosed.

---

## 4. System architecture

The eventual system should be a modular agent with explicit interfaces:

1. **Perception/state encoder:** maps structured observations or screenshots to a common belief-state representation.
2. **Memory/belief model:** tracks opponent cycle, resources, likely strategy, uncertain entities and relevant history.
3. **Strategic policy:** proposes a card/action family and a strategic intent such as defend, pressure, cycle, punish or save.
4. **Spatial action proposer:** generates candidate legal tile-centre placements and relevant timing choices.
5. **Value / action evaluator:** estimates downstream value of candidate actions.
6. **Search controller:** selectively evaluates high-value candidates through model or simulator rollouts.
7. **Opponent model:** predicts opponent actions or a distribution over opponent policy types.
8. **Safety and protocol layer:** validates action legality, response identity and timing before returning ActionV1.

Keep the first strong agent on the structured FAIR track. This isolates strategic learning from perception and is the shortest path to a strong policy. Add screenshot perception after the core controller is competitive; the visual track from the benchmark paper provides the test bed.

### State representation

Start with a structured, seat-relative entity representation:
- spatial tokens for towers, buildings, troops, projectiles and effects;
- card/hand tokens with costs and cooldown/cycle state;
- resource and clock features;
- relative position, lane and target relationships;
- recent public events;
- recurrent memory or a compact belief state for opponent cycle and hidden information.

Compare a spatial Transformer with entity/role embeddings against a lighter recurrent baseline. Avoid a CNN-only architecture as the default when the input is already structured; keep architecture choice empirical.

The policy should be capable of variable entity count and explicit uncertainty. Never pass privileged engine state to the deployed policy.

---

## 5. Data strategy: imitation first, then self-play

### 5.1 Expert demonstrations

Collect or curate legal, high-quality match trajectories:
- publicly accessible replays only where their reuse is permitted;
- direct demonstrations recorded in a controlled benchmark environment;
- annotated tactical states from knowledgeable players;
- agent-versus-agent trajectories generated by diverse policies.

For each demonstration, capture ObservationV1, action, next observation, public events, match configuration and provenance. Split by complete match and seed/player source. Do not let near-identical frames from the same match leak across training and evaluation partitions.

Quality is more important than raw volume. A million noisy low-skill transitions may be less useful than a much smaller set of verified expert decisions.

### 5.2 Imitation learning

Train a policy with masked action likelihood:
- card/hand-slot selection;
- spatial placement distribution;
- wait/ability choice where supported;
- optional strategic-intent auxiliary target.

Use teacher-forcing on demonstrations, action validity masks and separate losses for the factorized action components. Track calibration and invalid-action rate. Do not train the agent to imitate an invalid or stale action merely because it appears in a raw replay log.

Use behaviour cloning as initialization, not as the final training method. The key problem is covariate shift: once the policy makes a mistake, it visits states absent from the expert dataset. Address this with on-policy data aggregation where feasible and subsequent self-play.

### 5.3 Reinforcement learning

Train with a reproducible actor-critic baseline, starting with masked PPO or recurrent PPO. Add complexity only if the baselines justify it.

Core requirements:
- self-play against a diverse opponent pool, not only the current latest checkpoint;
- symmetric seat assignments and controlled seeds;
- league snapshotting so old policies remain available;
- evaluation against frozen opponents throughout training;
- separate training, validation and final test seed groups;
- checkpoint selection by validation cross-play, not training reward;
- reward design centred on game outcomes, with potential-based shaping only if its effect is validated and it does not change the optimal policy;
- explicit penalty or separate reporting for invalid actions, timeouts and engine faults rather than silently treating these as normal strategic losses.

A league should contain:
- current learner snapshots;
- older policy versions;
- scripted and deck-aware heuristic agents;
- adversarial exploiters trained to find weaknesses;
- policies specialised for different deck archetypes and tempos.

Use a principled opponent sampler such as prioritised fictitious self-play or a related mixture. Report its sampling distribution and keep a frozen evaluation league that is never used for gradient updates.

### 5.4 Robustness and exploit prevention

A self-play agent can become strong against itself while remaining weak against humans or unusual strategies. Test:
- previously unseen opponents;
- different deck archetypes;
- different openings and cycle orders;
- strategy switches during the match;
- deliberate baiting and resource manipulation;
- unusual but legal placements;
- policy populations from earlier training stages.

Track exploitability empirically through a fixed suite of exploiters and opponent policies. Do not call the result formal game-theoretic exploitability unless a valid bound or solver is actually used.

---

## 6. Model-based planning and search

This is the leading candidate for the eventual performance differentiator, but search must earn its complexity through ablations.

### 6.1 Candidate proposal

A learned policy proposes a compact set of candidate actions:
- top-K card choices;
- multiple strategically distinct tile-centre placements per card;
- wait or no-op;
- relevant ability choices where supported.

Candidate generation should include both the policy's high-probability actions and a small exploration set. Avoid exhaustive enumeration of every hand-slot/coordinate combination at every decision.

### 6.2 Value model

Train a critic to estimate:
- probability of winning from the current state;
- expected terminal score or tower-health differential;
- uncertainty and out-of-distribution indicators.

Evaluate value calibration by game phase, deck matchup and opponent family. A critic that is well calibrated on self-play but fails against held-out opponents must not control search without safeguards.

### 6.3 Search options

Investigate in increasing order of complexity:

1. **One-step counterfactual evaluation:** use the exact CRForge engine to compare a small candidate set under fixed opponent continuations.
2. **Short-horizon beam search:** expand high-value action sequences with a learned value model.
3. **Receding-horizon planning:** replan after each new observation rather than committing to a long plan.
4. **Model-based search:** use a learned action-conditioned world model for cheap proposal screening, then confirm the top candidates with the exact simulator where affordable.
5. **Tree search / MCTS:** consider only after candidate generation, transition prediction and value estimates are sufficiently reliable.

For real-time decisions, search must fit the applicable operational deadline. The benchmark's paused-clock strategic profile can measure decision quality without latency pressure, while the separate cadence/latency evaluations can quantify the practical trade-off. Do not conflate these two regimes.

### 6.4 World model

If a learned world model is developed, it must predict more than static entity persistence:
- entity birth/death and identity association;
- movement and targeting;
- projectile/effect events;
- tower and unit health changes;
- resource evolution;
- opponent action distributions or an explicit conditioning mode;
- uncertainty under unfamiliar actions and states.

Use event-aware and entity-aware metrics, not just aggregate state MAE. Test whether better prediction improves policy value or planning decisions. A more accurate predictor is not automatically a stronger player.

---

## 7. Opponent modelling and strategic memory

The current benchmark already contains a common public-memory representation. The high-performance agent can build a private recurrent belief on top of that public input, but must not receive privileged observations.

Maintain uncertainty over:
- possible opponent hand/cycle states;
- estimated opponent elixir;
- card-specific return times;
- observed deck archetype or policy family;
- likely opening/defensive patterns;
- adaptation after an opponent changes strategy.

Use probability distributions or sets of possible states rather than a single falsely precise guess. Train the opponent model on diverse policies, not only humans or one self-play population.

Evaluate predictions with proper scoring rules and calibration, then test their decision value by ablation: does using the opponent belief improve competitive performance and counterfactual action quality?

---

## 8. Training curriculum

A staged curriculum reduces the chance of training a complex policy before basic mechanics work.

### Stage A: deterministic mechanics
- single-card legality and placement;
- command delay and action rejection;
- tower and building interactions;
- movement, targeting and projectile behaviour;
- resource accounting and terminal conditions.

### Stage B: tactical micro-scenarios
- defend against a known push;
- choose between counter-push and reset;
- defend with constrained elixir;
- place a building or spell against multiple threat geometries;
- choose when to wait or cycle;
- handle simultaneous threats in both lanes.

### Stage C: short self-play matches
- simplified fixed openings;
- constrained decks;
- short match horizons;
- opponent populations with distinct play styles.

### Stage D: full benchmark matches
- complete deck lists;
- hidden hand/cycle;
- full match duration;
- cross-archetype play;
- randomised but reproducible starts.

### Stage E: robustness and expert challenge
- held-out opponent pools;
- strategy changes;
- unfamiliar but valid openings;
- different game-data versions only after revalidation;
- controlled expert matches.

Curriculum stages should be training aids, not hidden evaluation shortcuts. Final test games must use the official full protocol.

---

## 9. Evaluation against human experts

The benchmark paper's visual/structured and competency diagnostics should provide the measurement system for this second project.

### Controlled human evaluation

Before any elite challenge:
- recruit several high-skill players with informed consent;
- agree on game rules, deck constraints, account/test environment and whether the player sees the agent identity;
- use a standard match schedule with side/deck swaps;
- predefine series length and statistical analysis;
- log every completed match and all technical failures;
- pay/compensate external participants where appropriate;
- publish only replays or personal information that participants consent to share.

For a named professional such as Mohamed Light:
- contact through legitimate public/professional channels;
- offer a fixed, transparent evaluation protocol;
- let the player choose or approve the challenge rules;
- do not imply endorsement or use their identity in marketing without consent;
- do not claim a result until the full series is completed and verified.

A single best-of-five is a demonstration, not proof. A stronger claim needs multiple series, more than one deck/matchup where feasible, adequate side swaps and uncertainty estimates.

### Human-versus-simulator gap

A human who is highly skilled in the official game may behave differently in CRForge due to simulator mechanics, visual presentation or missing game features. Therefore:
- validate the human's performance in the same environment used to train the agent;
- compare human decisions in simulator and official game only when the rules are equivalent;
- do not directly compare a CRForge rating with a live ladder rank;
- report simulator limitations and any game-version mismatch.

---

## 10. The second paper: claims and evidence

Potential central claims, only if supported:
1. The combination of expert imitation, league self-play and model-based candidate search improves performance over each component alone.
2. A recurrent public-information belief model improves robustness to hidden opponent cycle and strategy variation.
3. Planning improves strategic action quality and performance against held-out opponent populations, not just the training league.
4. The resulting agent is competitive with strong human players under a reproducible evaluation protocol.

Required ablations:
- behavioural cloning only;
- PPO/self-play without demonstrations;
- imitation plus self-play;
- policy without recurrent belief versus with belief;
- policy without search versus search;
- learned-model search versus exact-simulator verification;
- single-opponent training versus league training;
- training-only decks versus cross-archetype training;
- latency/decision-cadence and compute budget.

Report training data volume, total environment steps, hardware, compute budget, inference cost, model size, wall-clock training, hyperparameter search and all seed counts.

Do not claim "the best Clash Royale agent" based only on one internal benchmark. Define the comparison population and benchmark rules.

---

## 11. Roadmap and go/no-go milestones

The schedule begins after the ICML benchmark-paper submission and is deliberately longer than the benchmark project.

### Phase 0 — Finish the benchmark foundation
- complete local Windows headless acceptance;
- stabilize renderer, replay and match provenance interfaces;
- publish the benchmark methodology and initial cross-play baseline;
- establish simulator fidelity and supported-mechanic lists.

**Exit:** a reliable training/evaluation runtime and a versioned benchmark with reproducible output.

### Phase 1 — Data and imitation baseline
- curate legal expert and high-quality policy trajectories;
- implement the common state/action representation;
- train a small masked behaviour-cloning baseline;
- evaluate held-out match trajectories and tactical states;
- identify which errors come from observation, modelling and action selection.

**Exit:** a policy that beats basic scripted baselines without leakage and with reproducible performance.

### Phase 2 — League self-play
- add recurrent PPO or a comparable stable RL baseline;
- introduce a frozen-opponent league and exploiters;
- use cross-play evaluation to prevent self-play overfitting;
- checkpoint and archive each significant policy version.

**Exit:** consistent improvement across the frozen opponent league and held-out seeds.

### Phase 3 — Search and model-based control
- add candidate-action proposal;
- implement exact-simulator one-step counterfactuals;
- train and calibrate the critic;
- compare short-horizon beam/search methods;
- add a learned world model only when exact rollout cost justifies it;
- run search/no-search ablations.

**Exit:** statistically reliable performance improvement at declared compute and decision budgets.

### Phase 4 — High-skill human play
- recruit and evaluate multiple high-skill players;
- run controlled repeated matches;
- inspect agent losses with the diagnostic suite;
- use expert feedback and new demonstrations for the next training cycle;
- freeze a final candidate before any named professional challenge.

**Exit:** competitive human results with all match logs, rules and uncertainty reported.

### Phase 5 — Elite challenge
- only proceed with consent, an agreed ruleset and an authorized test environment;
- conduct a repeated match series, with deck and side arrangements fixed beforehand;
- arrange independent observation or recording;
- publish wins, losses, draws and technical failures, not only highlight games;
- make claims no stronger than the protocol and results support.

**Exit:** a verified public result, not a target date.

---

## 12. Engineering priorities for the agent programme

Build only the infrastructure that moves agent performance or makes the scientific evaluation more reliable:

1. stable replay-prefix reconstruction and deterministic branch/clone semantics;
2. versioned multi-deck environment configuration;
3. a clean vectorized training interface with exact seed controls;
4. high-throughput simulator stepping and batched state encoding;
5. policy/value training and checkpoint versioning;
6. opponent league manager and evaluation scheduler;
7. candidate-action generator and rollout search;
8. trained world model only when its predictive utility is demonstrated;
9. visual perception adapter after the structured agent is strong;
10. human evaluation and authorized exhibition interface.

Do not spend time on a glossy live-game UI before the policy can beat the frozen benchmark league.

---

## 13. Risks

| Risk | Mitigation |
|---|---|
| Simulator-to-live mismatch | fidelity audits, supported-mechanic constraints, authorized human evaluation and version-specific reporting |
| Self-play overfitting | league snapshots, exploiters, held-out opponents and cross-play matrices |
| Expert data scarcity/noise | small curated high-quality set, replay provenance and action validity checks |
| Search is too expensive | candidate pruning, learned value screening and staged compute budgets |
| World model is inaccurate in critical states | uncertainty-aware search and exact simulator verification of top actions |
| Strong benchmark score fails to transfer to people | human evaluation in the same environment before any live-game claim |
| Game balance changes | freeze game-data fingerprints and repeat evaluation for each supported version |
| Famous-player challenge does not happen | evaluate a wider high-skill pool; the paper must not depend on one person's participation |

---

## 14. Guiding principle

The benchmark project should tell us how to measure strategic competence. This project should use those measurements to improve it.

Do not optimize for a viral claim at the cost of reliable science. The intended sequence is:

**Measure rigorously → diagnose failure → train stronger policies → validate across opponents → challenge elite humans under agreed rules.**

A Deep Blue-style result would be extraordinary. It has to be earned through repeatable performance, sound simulator validation and a fair competition protocol.
