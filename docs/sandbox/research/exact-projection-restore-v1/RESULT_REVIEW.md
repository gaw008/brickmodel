# Independent actual projection-restore result review

PASS for actual original-host numerical projection restoration. Saved supervisor exit 0 in 3.436563125 s; runner 3.114039833 s, restore/reencode/verification section 2.061400875 s. No trajectory integration or resume occurred.

Reviewed runner 660bd3873ee0d6ce428f0d70e84da6852a83e9665f68f130c8466f089c95ed26 and candidate 6c5ec48fda6c2600ca9000bd9b4c87c2f09a8cfa58d83e4c8e73abc0cd9e6d25. Before calling restore it checks actual installed package location, original state and policies, then the explicit current82-to-historical78 compatibility. Independently verified every original module hash and all non-module metadata match, and the actual difference is exactly the four pinned verifier modules saved in runtime-compatibility.json. Both complete runtimes remain separately recorded; current before/after are equal.

Independently checked all runner/supervisor input hashes and identical input maps. Compared actual reencoded-record.json bytes directly to the original strict record: full byte equality, SHA256 ac03be011f4f1b3dd47e12647f523e223797dcd53031d9dbd1b96d9e2f67af52. Saved return reports 30 accepted steps, 2 packets and 2 canonical ledger aliases. The reviewed actual runner checks each frame ledger is the same Python object as exactly one accepted step; saved memberships are [1,1]. Object identity is an in-process assertion supported by the saved run, not something claimed to survive ordinary JSON serialization.

The function result remains a typed numerical projection with resume_authorized=false. Historical observations retain their projection semantics; no live inverse graph is fabricated. Current82 read compatibility is not a cross-version execution permission. Separate continuation admission remains necessary.

This reviewer performed only saved-data/hash/byte comparisons; no EOS, repeated restore or audit execution.
