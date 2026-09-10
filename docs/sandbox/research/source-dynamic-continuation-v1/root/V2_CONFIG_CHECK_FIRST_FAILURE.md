The first inline passive configuration check exited 1 at `assert b.values == expected`.
`expected` was raw JSON lists; SourceRunConfig intentionally freezes them as tuples.
The failure was in that checker comparison, after both profiles passed load_source_run_config.
No EOS, source-study decode or native run was performed. The case, production code and driver
were unchanged. The saved check_v2_config.py compares raw JSON and then both validated frozen
representations separately; the result is recorded by its actual subsequent run.
