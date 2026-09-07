# Further refinement after retained endpoint-energy failure

Original four trajectories passed their single-run checks, but two finest compressed endpoints differed by 4.7827488742768764e-6J > original1e-6J refinement gate. This failure remains in independent-ledger-audit.json and NUMERIC_REVIEW.md. It is not erased by successful accepted-step energy accounting.

Run the same compressed fixture, same initial state/motion/kinetics/potential/inverse and t0..1/8, at step caps1/512 and1/1024. Keep all N/E/T/P validation tolerances, solver tolerances, 40s wall limit and20 rejection cap. Increase only maximum_steps from100 to160 for these newly declared runs because the1/1024 grid requires128 accepted steps; this is explicit resource scaling, not a physical accuracy relaxation. The32-step case cost0.913s, so128 steps are expected within40s; preserve any actual failure.

Save both new runs separately; compare their endpoints under the original N1e-9mol,E1e-6J,T2e-5K,P1Pa gates. Report actual accepted dt/rejections and oracle differences; do not retrospectively mark the earlier pair passed. No material/external or wet validation follows from this numerical refinement.
