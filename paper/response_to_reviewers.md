# Response to Reviewer Comments

**Manuscript:** Congestion-Aware Joint Charging-Station Placement, Capacity, and Swarm-UAV Trajectory Design for Age-Optimal Data Collection
**Authors:** Phuc Hao Do, Tran Duc Le, Truong Duy Dinh, Van Dai Pham

We thank the reviewer for the careful and constructive reading. The comments
identified real weaknesses, and addressing them has clearly strengthened the
paper. Below we respond to each comment point by point and indicate where the
manuscript was changed. Reviewer comments are in *italics*; our responses and the
locations of the changes follow.

---

## Comment 1 (Trajectory: frozen visiting order)

*The CETSP trajectory freezes the cyclic visiting order (angular sort of k-means
centroids), which removes combinatorial routing optimization from the continuous
solver. Integrate a dynamic sequence optimization, or give a rigorous bound on
the suboptimality of the frozen order.*

**Response.** We agree that freezing the order was a genuine limitation. We no
longer freeze it. The trajectory block now alternates the continuous position
updates (Adam) with a discrete **2-opt re-ordering** of the visiting sequence: we
run a block of gradient steps, reorder the current hover points by 2-opt, and
repeat. This is a coordinate descent between the continuous positions and the
discrete sequence, so the order is optimized jointly with the positions. A 2-opt
pass on fixed points can only shorten the tour and the subsequent position polish
only lowers the objective, so the refinement never worsens the result and, in our
tests, improves it.

**Changes.** Section V-A (Trajectory block) rewritten to describe the
position/order alternation; `src/trajectory.py` implements the interleaved 2-opt
reordering. We also added an exact optimality-gap study (Comment on solver
guarantees), see below.

## Comment 2 (Swarm size: M = 12 to 20 is not a swarm)

*The manuscript claims a "swarm" but caps the experiments at M = 12 to 20, which
is a minor fleet. A swarm should be evaluated at M > 50.*

**Response.** We added a dedicated large-swarm scaling study. We scale the fleet
to **M = 60** UAVs over a 20 km field with K = 8M sensors, and we grow the
charging capacity with the swarm (C_tot = ceil(M/3) ports), consistent with our
provisioning law (Proposition 1): a large swarm is only worthwhile if its
charging capacity grows with it. The proposed contention-aware placement keeps
its advantage over the single pooled station and the coverage-optimal placement
across the whole range (gain 10.2 to 12.7%), and the peak AoI stays controlled
(50.6 min at M = 20 to 47.6 min at M = 60).

**Changes.** New Section VI subsection "Scaling to a large swarm" and new figure
(Fig. 10); `experiments/scale.py`.

## Comment 3 (Queue bound: tighten M/M/c//N with M/D/c//N)

*The finite-source M/M/c//N model is a loose conservative (exponential) upper
bound relative to the near-deterministic reality. Develop and benchmark an
M/D/c//N approximation to tighten the bound.*

**Response.** We added a deterministic-service **M/D/c//N approximation** using
the standard service-variability (Allen-Cunneen) correction, in which the mean
wait scales with (1 + c_s^2)/2 and deterministic service (c_s^2 = 0) halves the
M/M wait. Benchmarked against the discrete-event simulation, this tightens the
over-prediction of the real wait from about 4.5x (M/M) to about 2.3x (M/D). We
also explain the residual gap: it is due to the near-deterministic *operating*
(inter-request) process, which a service-only correction does not model. Both
models are upper bounds, so the reported AoI remains safe rather than optimistic.

**Changes.** `queue_model.finite_source_wq_md`; the M/D/c//N series added to the
DES-validation figure (Fig. 3) and discussed in Section VI-B; the conclusion
updated to reflect that this refinement is now included.

## Comment 4 (Related work: dynamic fleet charging)

*The paper discusses fleet charging but lacks citations on dynamic fleet
charging.*

**Response.** We added a dedicated discussion of dynamic fleet charging with
three references: auction-based charging scheduling for a multi-drone network,
decentralized electric-vehicle charging coordination, and mobile wireless-charger
routing for a sensor fleet. We state precisely what they lack relative to our
work: they schedule when and where each vehicle charges, but do not jointly place
and size the shared stations, nor couple the induced charging wait into an
Age-of-Information objective for a UAV swarm.

**Changes.** Section II (Related Work), "Energy-limited UAVs and charging"
subsection; three references added (now 36 references total).

## Comment 5 (Writing: AI-sounding phrases)

*Several phrases read as machine-generated (for example "honest reporting",
"sweet spot", "not a cosmetic refinement", and frequent use of "honestly"). The
sentence "We stress an honest point: an earlier version ..." suggests a revision
of a prior draft.*

**Response.** We revised the prose throughout to remove these phrases. In
particular, "sweet spot" is now "optimal swarm size", "not a cosmetic refinement"
is now "essential rather than incidental", and the words "honest" and "honestly"
were removed. The "an earlier version" sentence was rewritten as a hypothetical
model comparison ("Had the charging system been modeled as an open M/M/c queue, a
spurious crossover would appear ..."), which states the modeling point without
referring to any prior draft.

**Changes.** Introduction, Related Work, and Experiments (Sections I, II, VI).

## Comment 6 (Equation (12d) exceeds the column width)

**Response.** The constraint (12d) was shortened to a compact form,
"AoI_k(t) evolves as in (1)", which fits within the column.

**Changes.** Section IV, problem (P0).

## Comment 7 (References are not clean; "Available" links)

**Response.** We removed the "[Online]. Available: ..." URLs from all published
references, which now show only the DOI. The single preprint reference shows a
clean "arXiv:XXXX" identifier without a link.

**Changes.** `refs.bib` and the reference list.

---

## Additional strengthening (beyond the specific comments)

- An **optimality-gap** study now benchmarks the greedy block-coordinate solver
  against the exact optimum (enumerating all placements, port splits, and
  assignments) on small instances: the solver matches the optimum for M <= 6 and
  stays within 0.11% on average (below 1% worst case) at M = 8. This neutralizes
  the concern that the greedy solver has no optimality guarantee (Section VI,
  Table IV; `experiments/optimality_gap.py`).
- A **robustness** study shows the advantage is stable across the collection
  radius and charge time, and grows on a non-uniform (clustered) sensor field
  (Section VI, Fig. 9).

All results are reproducible; the code and data are available at
`https://github.com/haodpsut/swarm-uav-aoi-congestion`.
