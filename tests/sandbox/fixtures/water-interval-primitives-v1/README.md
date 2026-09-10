# Mathematical test inputs

`heos-water.json` is the original source-pinned CoolProp water Helmholtz JSON (SHA256 a10a0da6c55e623cccc1f56a70cb348c772d8fc1710a6a142b459abb0dec4586); accompanying CoolProp-LICENSE preserves its license. The mathematical wrapper verifies this exact hash.

`saved-initial.json` and `saved-initial-forward.json` are manufactured mixed-storage research state/output fixtures. Their observations only select a numerical density search bracket; strict full-rectangle residual signs and derivatives determine acceptance. They do not establish real material properties or global phase stability.
