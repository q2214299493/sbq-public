<!-- state-handoff:start current_task -->
# Current Task

## Objective

Screen three Fe45 CH* plus H* coadsorption relaxations for the CH* + H* -> CH2* + * initial state and select one compatible, retained CH*+H* minimum as the final IS.

## Current Evidence Snapshot

- Candidate A job `9701350` is scheduler RUN in `Gkn_normal` on `32*gknew071`.
- Candidate B, CH_top plus H_second_neighbor_hollow, was accepted by LSF as job `9701505` and is scheduler PEND.
- Candidate C, CH_long_bridge plus H_adjacent_top, was accepted by LSF as job `9701506` and is scheduler PEND.
- Both new jobs passed local structure, INCAR, production-input, remote POTCAR, duplicate-directory, and remote input-hash checks before submission.
- The calculation registry records jobs 9701505 and 9701506 with scientific status Not started.

## Lifecycle Status

- Phase: `active`

## One Executable Step

Monitor jobs 9701350, 9701505, and 9701506 to scheduler exit, then parse each OUTCAR/OSZICAR/CONTCAR for electronic convergence, ionic convergence, maximum movable force, final CH+H connectivity, final sites, unintended CH2 formation, and compatible final TOTEN.

## Submission Boundary

No additional adsorption candidate, resubmission, NEB, CI-NEB, DIMER, frequency, or TS action is authorized.

## Authoritative Constraint

Execution backend roles and handoffs remain governed by `configs/execution_backends.yaml`.

## Done When

- All three scheduler jobs reach terminal states and their calculation outputs are separately classified.
- Every completed candidate has electronic, ionic/force, and geometry status recorded without conflating scheduler completion with scientific acceptance.
- One retained CH*+H* minimum is selected as IS using compatible local energies and pathway suitability; non-selected converged candidates are retained in the registry.

## Authoritative References

- `calculations/fe110_ch_h_coadsorption_20260808/provenance/submission_batch_9701505_9701506.json`
- `calculations/fe110_ch_h_coadsorption_20260808/provenance/submission_batch_registration_receipt.json`
- `calculations/fe110_ch_h_coadsorption_20260808/provenance/runtime_checkpoint_three_candidates_20260808T131238.json`
- `calculations/fe110_ch_h_coadsorption_20260808/candidate_review/candidate_submission_update_20260808.json`
<!-- state-handoff:end current_task -->
