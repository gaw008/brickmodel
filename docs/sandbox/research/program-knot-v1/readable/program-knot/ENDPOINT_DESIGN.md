# Ordinary endpoint coalescence candidate

Original source must first reproduce the retained failure before applying this change. Scope is the outer wet ordinary branch only; no terminal-event tolerances, midpoint guards, state inventories, clocks or ledger weights are reset.

Keep the existing rounded proposed endpoint. Coalesce to the immediate known program/end boundary only when the maximum-step cap determines that endpoint, the positive residual is at most min(ulp(boundary), 32*ulp(min(maximum_step, boundary-start))), and the exact actual duration differs from the nominal cap by at most32 ulps of the cap. If a wet inventory limiter exists, both the nominal cap and actual boundary duration must be no larger than safe_fraction times the exact inventory/rate ratio.

The accepted panel integrates its entire actual endpoint interval. Its ledger end time and every stage weight already derive from those endpoints. No time-only jump or zero-duration step is permitted. The tiny bounded extension of the nominal maximum step is an explicit representation policy, not relaxed state/error acceptance. A directly requested adjacent-float interval still fails the original RK midpoint guard. A safe-inventory-limited segment cannot be extended beyond its exact safety duration. Dry continuation and other event approach scheduling stay unchanged until a separately demonstrated defect justifies changes.

Verification: original constant-source failure and original saved .005 affine cases; analytic amount/energy prefixes; exact presence of knot; no duplicate/crossing panels; dyadic/representable-neighbor controls; safe-limiter refusal; cancellation/resource preservation. Standalone ordinary integration remains an unchanged control.
