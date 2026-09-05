# Public source release

Source commit: `3a4c23f3bae8da264323fea75d6fe593ca562845` in the original private work repository.
This repository starts a separate public history; the private history is not copied.
All source code, configurations, schemas and tests are preserved byte-for-byte.
The public README and this notice explain the release boundary; .gitignore adds
exact exceptions for existing documentation and retrieval fixtures. No license for
third-party software, VASP pseudopotentials or model weights is granted here.

A fresh local registry can be initialized explicitly after installing dependencies:

```bash
python -m scripts.init_registry --db data/project_registry.sqlite3
```

Do not run this against an existing registry without its migration/review process.
The versioned AQCat25 Fe45 calibration package is retained as a reference/test
fixture because source tests depend on it; it is not TS-domain calibration.
No currently running calculation or private model is reproduced by this checkout.

The following tracked artifacts were omitted from the public snapshot:

- `archive/web_sources/fe110_co_paper_landing_20260623.html`
- `archive/web_sources/vtst_optimizers_20260623.html`
- `archive/web_sources/wx_article_text.txt`
- `data/project_registry.sqlite3`
- `outputs/adsorption_topic1_20260702/review_9627285/CONTCAR_final_CO_plus_C2H2`
- `outputs/adsorption_topic1_20260702/review_9627285/POSCAR_initial`
- `outputs/aqcat25_handoff_test_20260718_cpluso/POSCAR.aqcat25`
- `outputs/aqcat25_handoff_test_20260718_cpluso/gpu_result.json`
- `outputs/aqcat25_handoff_test_20260718_cpluso/gpu_result_manifest.json`
- `outputs/aqcat25_handoff_test_20260718_cpluso/handoff.json`
- `outputs/aqcat25_handoff_test_20260718_cpluso/run_gpu_test.sbatch`
- `outputs/aqcat25_species_smoke_v2/ch3o/handoff.json`
- `outputs/aqcat25_species_smoke_v2/ch3o/input/POSCAR`
- `outputs/aqcat25_species_smoke_v2/ch3o/output/job_736/POSCAR`
- `outputs/aqcat25_species_smoke_v2/ch3o/output/job_736/gpu_result_manifest.json`
- `outputs/aqcat25_species_smoke_v2/ch3o/output/job_736/producer_exit_record.json`
- `outputs/aqcat25_species_smoke_v2/ch3o/output/job_736/result.json`
- `outputs/aqcat25_species_smoke_v2/h2_derived/handoff.json`
- `outputs/aqcat25_species_smoke_v2/h2_derived/input/POSCAR`
- `outputs/aqcat25_species_smoke_v2/h2_derived/output/job_735/POSCAR`
- `outputs/aqcat25_species_smoke_v2/h2_derived/output/job_735/gpu_result_manifest.json`
- `outputs/aqcat25_species_smoke_v2/h2_derived/output/job_735/producer_exit_record.json`
- `outputs/aqcat25_species_smoke_v2/h2_derived/output/job_735/result.json`
- `reports/孙柏权周报.docx`
