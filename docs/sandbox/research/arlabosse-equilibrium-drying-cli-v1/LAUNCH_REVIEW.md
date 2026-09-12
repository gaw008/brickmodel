# Public CLI launch static review

APPROVE for the single preregistered launch. PLAN and launcher agree: the reviewed public entry, explicit --steps 1 / duration 1 s, installed Python with -I and PYTHONPATH removed, original source root, and new exclusive result path. The old 2792 input records are checked against current SHA before launch; entry, PLAN and launch.py add three inputs. Existing native/supervised directories and symlinks are refused, followed by exclusive directory creation. There is one run_attempt call, no loop/retry, and process status/exit/input-unchanged determine launcher success.

The unchanged existing supervisor owns the original process group with 165 s / 5 s cleanup; complete status already requires leader reaping and no recorded cleanup errors. The CLI retains its stated 40/100/150 s cooperative budgets and its own complete/failed records. Neither script changes source physics or the installed package, and the plan keeps elapsed/allowed time distinct from physical-clock and state comparisons. No material/full-cycle/convergence qualification is introduced.

Static identities:

- `PLAN.md`: `1df694da097944c11af1723b8c080c3bf148382dca630b2fc2c0052c1890940a`
- `launch.py`: `be6612996ebfb6757de51ed88e52bc42b316393851bf3200f66399e60fcb3aec`
- `run_equilibrium_drying.py`: `c1e567f6f1fd74d488d0e64c66b650d494711c3ed786f4f3aae7d79c430b1df8`

No launcher, CLI, EOS or tests were executed in this review. Future saved-result comparison remains a separate step.

## Review Summary

| Severity | Count | Status |
|---|---:|---|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — bounded static launch review.
