# Independent water element convention review

Reviewed only facts.json SHA256 a9b5bec83df94504346a5f93f3008a0029653f24bfc085babeb65bbdbb919838, README.md c5bc0fdd5bb74ce59c9aa191afb4a3899ce022af0c72d749457d8de6717408ae, and source-excerpt.txt 510543e4d5b343463126ed87957ba9f5b24d1bb4c0978fc51199c3acb2b769bc under data/sandbox/research/water-element-convention-v1. No repository edits, candidate implementation inspection or EOS calls.

The current primary CIAAW table explicitly gives the 2024 abridged H and O values recorded here: H 1.0080 ± 0.0002 and O 15.999 ± 0.001. Its isotope-variation caveat reinforces the supplied qualification: these are not a specific water sample's measured composition or probability distribution. The factual excerpt and its SHA match; the files correctly describe that SHA as an excerpt hash, not a complete-page hash. Sources independently opened: [CIAAW abridged table](https://www.ciaaw.org/abridged-atomic-weights.htm), [NIST water entry](https://webbook.nist.gov/cgi/cbook.cgi?Name=water).

Independent stdlib Fraction calculation passed: 2(1.0080)+15.999=18.0150; hydrogen share=2.0160/18.0150=672/6005; oxygen share=15.999/18.0150=5333/6005; the shares sum exactly to one. The formula weight is a nominal normalization input, not an instruction to replace the actual water provider's molar mass.

The runtime rule is coherent as the explicitly stated bookkeeping convention: for each water inventory use n*M_provider*w_element. Identical liquid/vapor shares and the same provider mass make phase exchange preserve both labeled elemental masses and total water mass. Keeping chemical water stoichiometry zero prevents this approximate coordinate choice from being used to justify water-forming or water-consuming atomic reactions. It is not an independently measured elemental composition, an isotope-resolving phase model, or a cross-species atomic-number certificate. Those limitations are explicit in both files and must remain enforced by any later consumer; this document review does not establish that the pending implementation enforces them.

No invented physical parameter or unsupported material admission is asserted by these files. Reported ± values are retained without an invented statistical model, and the nominal fractions are not presented as certified uncertainty bounds. Classification derived_from_evidence is appropriately qualified as a manufactured-test nominal convention, not a sample-specific measurement.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE these source and convention files for their explicitly limited purpose. Wet storage implementation and chemical-zero enforcement require separate code review.
