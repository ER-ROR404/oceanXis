# tests/fixtures/

Small, synthetic, **non-sensitive** fixtures that let the entire pipeline be tested WITHOUT
downloading Copernicus data (CI-safe). These are the ONLY data files that may be committed
(exception to RULE 12, per `.gitignore`).

Intent:
- synthetic_surface_input.nc      7-channel surface inputs on a tiny grid
- synthetic_glorys_target.nc      reference temperature at the 15 depths
- synthetic_argo_profile.nc       independent validation profile (RULE 9)
- expected_profile.json           expected API profile output

Generate tiny fixtures with a script (not real ocean data) during the coding phase.
