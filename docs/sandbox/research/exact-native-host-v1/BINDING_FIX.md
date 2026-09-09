# Water backend identity correction

Frozen exact_free_host.py SHA256 1153884bad187c94d156c351a85aacb11983d9bff346c02ceba4d64277bb3918.
Frozen test_host_seam.py SHA256 a97facba635f79b716798f82a170a8913ae30ecf202444afc6a962363a607f99.

The original full operator canonical digest deliberately stops at water source/reference/numerical-limit descriptors. The new additional binding walks the same dataclass/mapping/sequence operator tree and records each actual water-provider slot's path, concrete module/class name, and full immutable implementation-descriptor digest. This includes independent chemical water, chemical ideal-vapor water, thermal mechanical water, and thermal gas-phase ideal-vapor water. Provider internal native kernels and mutable caches are not traversed. Existing full input digest and pre/post evaluation checks remain.

Original exact_free_host-before-binding.py and test_host_seam-before-binding.py retained. Actual RED binding-red.log: four failed, five passed. Missed implementation changes in three nonchemical slots and a concrete backend-class replacement were reproduced. Final binding-green02.log: nine passed in 0.12 seconds.

Command: `PYTHONPATH=/private/tmp/brick-exact-native-host-v1/overlay /private/tmp/brick-water-backend-probe/venv/bin/python -m pytest /private/tmp/brick-exact-native-host-v1/test_host_seam.py -q`

New tests use exact supported provider classes constructed as instrumented data shells, real provider recognition, real operator _digest, and real chemical _check_identity. They do not patch away the binding. Only physical evaluation is stubbed. The backend-class test deliberately uses equal None descriptors to isolate the concrete-class contribution; this shell is not claimed to be a physically initialized HEOS provider. The tests therefore establish binding/control flow, not EOS or constructor validity. Existing unrelated candidate/source files are untouched. No repository edit, EOS, installation, or commit occurred. Tesla was asked to review the final frozen hashes.
