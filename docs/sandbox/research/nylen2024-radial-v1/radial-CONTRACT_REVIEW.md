# Independent spherical geometry contract

Read docs/sandbox/RADIAL_HEAT_GEOMETRY.md before worker code freeze. Formula V=4*pi*(ro^3-ri^3)/3 follows direct volume integral; A=4*pi*r^2. With constant half-cell k, integrating steady Q=-4*pi*r^2*k*T' gives resistance (1/ri-1/ro)/(4*pi*k). Series resistances across a shared face preserve one power Q with opposite signs. Midpoint representatives and exact shell integrals must be distinguished from volume-averaged temperature; discrete storage requires actual shell volume regardless of representative choice.

Independent checks required: center face zero flux without division by zero; all other positive radii monotonic; boundary resistance from last representative to R; zero-k blocks conduction; Fick/Darcy equivalent distance A_face*integral(dr/A) applies geometry only and cannot upgrade compressible-state averaging to an exact solution; thermal and gas enthalpy contributions must remain in original ledger. Geometry identity must include shell faces and affect serialization admission. Default None should preserve arithmetic/order, not merely approximate outputs. Any deformation/liquid/program/codec consumers not supporting spherical geometry must fail explicitly.

Manufactured modal validation T=Tref+A*sinc(pi*r/R)*exp[-alpha*(pi/R)^2*t] satisfies zero central gradient and fixed exterior Tref. Center observation is not first midpoint; grid convergence or explicit reconstruction required. This geometric proof supplies no Nylen material coefficients, no shrinkage law, and no material validation.

Implementation review awaits author freeze.
