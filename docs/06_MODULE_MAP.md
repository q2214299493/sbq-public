# Module Map

Module READMEs own purpose, inputs, workflow, outputs, and done criteria. This file owns only status, dependencies, and the current gate.

Allowed statuses: `Planned`, `Active`, `Blocked`, `Completed`.

| Module | Status | Depends on | Current gate |
|---|---|---|---|
| `state_handoff` | Active | none | Audit/event/proposal manager implemented in review-first mode; initial managed-view baseline adoption requires one exact user-approved proposal |
| `catalysis_data_retrieval` | Active | source access, semantic model | CatApp and OC20NEB/CatTSunami machine access need confirmation |
| `convergence_workflow` | Active | retrieval, server | Five-layer production branch selected; clean static `9574228` accepted; any later layer-count comparison is validation-only |
| `adsorption_workflow` | Active | retrieval, AQCat25 GPU, VASP, convergence, registry | AQCat25 endpoint-relax interface smoke passed in job `727`; production batch handoff and compatible VASP relaxations/final statics remain required |
| `adsmind_lite` | Active | CARE species, clean slabs, adsorption rules | Fe(110) benchmark and Fe(100)/Fe(111) metallic detectors pass; carbide/oxide remain manifest-only and need real-surface validation |
| `fe_convergence_baseline` | Active | convergence evidence | Register seven-layer routine and eight-layer high-accuracy true Fe(110) branches |
| `transition_state_search` | Active | reviewed endpoints and path, VASP ordinary micro-NEB, completed-path validation | Formal 80-core local VASP ordinary micro-NEB job `9742743` is submitted on `sunboquan-codex` for the reviewed seven-image O-H local path with five internal images, `NSW=300`, and `LCLIMB=false`. Monitor it to `DONE` or `EXIT`, then run completed-path electronic, force, geometry, and scientific review before any CI-NEB or Dimer decision. By explicit user decision, ordinary-NEB pilots are optional diagnostics and are not a universal submission prerequisite; any supplied pilot evidence remains strictly validated |
| `ts_vibrational_validation` | Active | separate consistent partial-Hessian IS/TS/FS corrections only for future thermochemistry or kinetics | For Fe(110) CO dissociation, Dimer job `9656664` and local partial-Hessian job `9694935` satisfy the accepted Dimer-plus-target-mode scope with one `537.451689 cm^-1` C/O-dominated imaginary mode. Connectivity and optional VFA classification are not blockers; no kinetic-eligibility claim is made |
| `memory_migration` | Completed | state handoff | `MM-001` through `MM-005` complete; future updates are incremental and durable-only |
| `git_versioning` | Active | none | `origin` has no anonymous GitHub access (404) and is treated as private; consolidate reviewed task-scoped changes without committing calculation outputs or credentials |
| `calculation_registry` | Active | state handoff | Schema v8 preserves the existing scientific tables and adds immutable TS strategy-learning history; scientific result acceptance remains with the owning validation modules |
| `incar_custodian` | Active | owning scientific module | Recommendations remain review-only |
| `kinetic_data` | Planned | registry, validated DFT/TS data | Define production schema and CATKINAS/Zacros exports |
| `thermochemistry` | Blocked | Grade A TS and stable-state frequencies | Missing validated frequency inputs and conditions |
| `reaction_network` | Blocked | validated species, TSs, thermochemistry | Missing complete balanced mechanism |
| `baseline_mkm` | Blocked | kinetic data, reaction network | Missing validated CATKINAS-ready dataset |
| `coverage_mkm` | Blocked | baseline MKM, interaction model | Missing coverage-dependent parameters |
| `surface_kmc` | Blocked | kinetic data, lattice/event model | Missing Zacros-ready lattice and event catalog |
| `reactor_simulation` | Blocked | validated MKM/KMC rates | Missing reactor definition and operating conditions |
| `sensitivity_uncertainty` | Blocked | functioning kinetic/reactor model | Missing model and justified uncertainty ranges |

## Intake Rule

The `transition_state_search` module also owns the local learning extension
described in `modules/transition_state_search/LEARNING.md`. Its code and local
tests are implemented; scientific performance improvement is not yet measured.
The optional MatRIS NEB/Sella candidate/label/rerun integration is documented
in `modules/transition_state_search/SELLA_BRANCH.md`. A bounded real MatRIS/Sella
GPU component test passed as job 1509; full-loop VASP/scientific validation
remains pending, so this is not a completed scientific workflow.
The separate active calculation-monitoring task above remains unchanged.

For a new module:

1. Create `modules/<module>/README.md` with purpose, inputs, dependencies, workflow, outputs, and done criteria.
2. Add one row here with status and current gate.
3. Put unresolved prerequisites in `tasks/backlog.md`.
4. Put one thread-sized executable action in `tasks/current_task.md`.

Do not mark a module `Completed` until its README done criteria are met and outputs exist.
