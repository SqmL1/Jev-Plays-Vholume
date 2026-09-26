# Jev: VHOLUME route planning and control spec

**Status:** Draft v0.1 · 26 September 2026

## Goal

Build Jev, an agent that completes a selected VHOLUME time trial through screen observation and ordinary player inputs. Jev should discover a valid route, learn to traverse it consistently, and improve its completion time over repeated attempts. The primary objective is **minimum valid finish time**; track average velocity, peak velocity, and route length as diagnostics. Verify the game's exact ranking/scoring rules before optimizing for any separate score.

## Scope and assumptions

- Start with one fixed map and spawn, one display resolution and HUD configuration, and offline/local time trials.
- Observe rendered frames and HUD. Send mouse and keyboard inputs through a controller adapter. Do not assume a native gameplay API or accurate position telemetry.
- Prefer locally available map geometry if recoverable from the installed game. A cooked level and its referenced meshes may require reconstruction of actor placement, collision, checkpoints, and finish; a bare mesh is not automatically a navigable map.
- If extracting the official map is impractical, use a manually annotated route or a visual map assembled from recorded runs. Both should feed the same planner interface.
- The first release should finish reliably; speed optimization follows a successful baseline.

## System outline

| Component | Input | Output | Responsibility |
| --- | --- | --- | --- |
| Capture | Game window | Timestamped frames | Stable resolution, frame rate, cropping, run recording |
| Perception | Frames | Observation + confidence | Read speedometer/timer, recognize movement state, visible landmarks, start/checkpoints/finish, deaths |
| Localization | Observations + previous action + map | Position/heading/velocity estimate + uncertainty | Match landmarks and predicted motion; recover after missed observations |
| Map adapter | Extracted level, annotated screenshots, or demonstrations | Traversal graph | Represent surfaces, gaps, wall-run segments, checkpoints, hazards, goal |
| Dynamics learner | State, input sequence, result | Reachability and transition model | Estimate time, exit speed, failure risk for movement primitives |
| Planner | Graph + current belief state | Route and target maneuver | Choose feasible, low-time route; replan after deviations |
| Controller | Target maneuver + estimated state | Timed keyboard/mouse input | Steer, jump, slide, wall-run setup; release stuck inputs |
| Evaluator | Recording + outcome | Metrics and failure labels | Compare attempts and update models |

## Observation and state

Use **percepts** for the data Jev can actually observe; use **state estimates** for values inferred from those observations.

```text
Observation(t): frame, timestamp, HUD speed?, HUD timer?, crosshair/visual cues?,
                visible landmarks, ground/wall/air cues, checkpoint/finish cue,
                death/reset cue, confidence per field

BeliefState(t): position distribution (x,y,z), heading/pitch distribution,
                horizontal/vertical velocity, movement mode,
                current checkpoint, route progress, uncertainty
```

The speedometer may show speed magnitude rather than the full velocity vector. Facing direction is the camera's apparent heading, while travel direction may differ during strafes or wall runs. Position is not directly observable from a mesh: it must be aligned to the live camera view using landmarks, a known spawn, motion estimates, and periodic corrections. “Distance to finish” should initially mean remaining **estimated route time** plus route progress, with geometric distance reported separately.

Validate HUD availability and how each movement state appears using short labeled recordings. If states such as sprinting or wall-running have no reliable on-screen indicator, infer them from frame motion and recent input, and keep uncertainty explicit.

## Map acquisition milestone

1. Inspect the installed game files for packaged level content. Record container format, map package names, whether assets are readable, and whether useful meshes, placements, or collision can be obtained. Do not assume the source Unreal project can be recovered.
2. Export or derive a local analysis representation for **one** official level: traversable surfaces, walls usable for movement, gaps, hazards, spawn, checkpoint order, and finish. Manually label missing gameplay semantics.
3. Align map coordinates with at least three recognizable in-game landmarks and a recorded spawn. Validate the alignment on a held-out run.
4. If placement/collision is unavailable, annotate a coarse map and demonstrated route from footage. Keep the map adapter independent of its source.

**Exit criterion:** Jev can identify the spawn and track which of several marked route segments it occupies during a recorded run. Asset recovery is a research task until this criterion is met.

## Traversal graph and objective

Represent a sparse graph of **movement states**, not just points in 3D space. A node includes a region/surface, approach heading, speed band, movement mode, and checkpoint progress. An edge is a feasible maneuver such as run, slide, jump, wall-run, or landing, with measured or simulated input sequence and resulting state.

For each edge store estimated duration, exit speed/heading, success probability, and failure or reset cost. An edge exists only if the maneuver is physically reachable from its input state. Velocity required to reach a point is a **feasibility condition**, not the cost itself. A useful first planner minimizes expected completion time, including retry cost:

```text
route value ≈ sum(edge time + failure probability × recovery cost)
```

The planner should respect ordered checkpoints, collision and movement constraints. Because time and reachability depend on entry speed and direction, a distance-only A* graph cannot solve the full problem. Start with measured movement primitives and a coarse state graph; use A* or dynamic programming where costs are well behaved, then improve edge models from runs. Replan from the current estimated state when Jev misses a maneuver. A short receding-horizon controller can choose the next inputs while tracking the planned edge.

## Delivery stages

| Stage | Deliverable | Acceptance check |
| --- | --- | --- |
| 0. Instrument | Capture, input adapter, synchronized run log, manual reset | Replay shows timestamped frames and exact input history; emergency stop releases inputs |
| 1. Observe | HUD reader and coarse movement/death/finish labels | Measure recognition accuracy on labeled clips; report uncertainty and missed states |
| 2. Baseline | One manually defined route and simple closed-loop controller | Finishes the chosen time trial repeatedly from the fixed spawn |
| 3. Map | Map adapter and localization aligned with one level | Recognizes route segment and detects off-route states in recorded and live runs |
| 4. Plan | State graph, measured transitions, time-aware route search | Proposed route beats the baseline in repeated valid attempts |
| 5. Improve | Learn transition parameters and tune maneuvers from run logs | Better median completion time without materially reducing finish rate |

Record finish rate, median valid time, best valid time, checkpoint completion, speed profile, localization error where labeled, and recovery frequency. Fix test conditions (resolution, graphics settings, spawn, version, and controller sensitivity) when comparing routes. No single fast run should count as proof of improvement.

## Open questions and risks

1. Which specific VHOLUME level and time trial should be the first target? What does the game display for speed, timer, checkpoints, and movement state?
2. Can installed official level assets yield actor transforms and collision, or only disconnected visual meshes? Are packages encrypted or otherwise inaccessible?
3. How do mouse sensitivity, field of view, frame rate, and input latency affect repeatability?
4. Are checkpoints mandatory and ordered? Does the timer or leaderboard use any rules beyond elapsed time?
5. Which movement primitives preserve or gain speed, and what is the recovery cost of failure?

**First practical experiment:** Record several manually played attempts on one course with HUD visible, inspect the local level assets, and label the spawn, three landmarks, checkpoints, finish, and a successful route. This decides whether the next iteration uses extracted geometry or a visual/annotated map.

## References

- [VHOLUME Steam page](https://store.steampowered.com/app/4131730/VHOLUME/) — game and time-trial context.
- [Official VHOLUME mapping guide](https://ironequal.com/vholumeMapping/) — custom-map tooling; it does not establish availability of original campaign project files.
