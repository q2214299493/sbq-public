# Fe(110) CO Dissociation Workflow

Current state: reviewed ordinary NEB submitted as job 9631737.

Selected Topic-1 endpoints are job 9558184 CO/top and job 9622455 C/long-bridge + O/hollow. Both local CONTCAR hashes match the VASP server. The whitelist has no transferable Fe(110) path; an Fe(211) record confirms only the reaction class.

The raw lowest-energy product required an exact 3x3 surface-symmetry mapping to avoid combining dissociation with long-range diffusion. The mapped endpoint passes identity, fixed-layer, geometry, and displacement gates.

Matched-static jobs 9631646/9631647 completed, passed the result gates, and were registered at `TOTEN=-371.99321585/-372.71083562 eV`. The endpoint-only reaction energy is `-0.71761977 eV`; no barrier exists yet.

MZ73 job 737 returned an uncalibrated AQCat25+BA-Sella predicted candidate. It passed the work return and geometry gates and was used only as the elongated-CO waypoint. The reviewed five-image path passed `dist.pl`, `nebmovie.pl 0`, fixed-layer, collision, and minimum-image continuity checks. Ordinary no-climb NEB job 9631737 uses 120 cores and is `PEND`. Next: monitor every image and decide continuation versus CI-NEB/DIMER only after the ordinary path is acceptable.
