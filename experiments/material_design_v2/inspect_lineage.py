"""Minimal read-only probe for unlinked derived observations."""
from pipeline import Study, DEFAULT_INPUT
s=Study(DEFAULT_INPUT)
s.import_xrf()
s.import_pellets()
known={(d['source_id'],d['sheet'],d['cell']) for d in s.derivations}
for r in s.observations:
    if r['evidence_status']=='source_derived' and (r['source_id'],r['sheet'],r['cell']) not in known:
        print(r, 'formula:',s.books[r['source_id']][r['sheet']][r['cell']].formula)
