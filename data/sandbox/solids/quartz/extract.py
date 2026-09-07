"""Extract limited quartz facts from locally retained original NIST HTML.

The original copyrighted pages stay in the ignored source cache. This parser
uses named coefficient tables and preserves printed numeric strings. It does
not fetch data, fit coefficients, supply solid volume, or smooth transitions.
"""
from decimal import Decimal, localcontext
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path


class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            if self.table is not None:
                raise ValueError("nested table needs explicit parser support")
            self.table = {"label": dict(attrs).get("aria-label"), "rows": []}
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.table["rows"].append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def read_tables(path):
    parser = Tables()
    parser.feed(path.read_text())
    parser.close()
    return parser.tables


def shomate(coefficients, temperature):
    a, b, c, d, e, f, g, h = map(Decimal, coefficients)
    t = Decimal(temperature) / 1000
    return (a+b*t+c*t*t+d*t*t*t+e/t**2,
            a*t+b*t*t/2+c*t**3/3+d*t**4/4-e/t+f-h,
            a*t.ln()+b*t+c*t*t/2+d*t**3/3-e/(2*t*t)+g)


def main():
    root = Path(__file__).resolve().parents[4]
    cache = root / "runs/sandbox/source-cache/quartz-20260907"
    web_path, janaf_path = cache / "nist-quartz-table.html", cache / "janaf-O-037.html"
    verified_assets = {
        web_path: "d9c37c3d778299acae5aaa8c9e75105bbd13f777dcfd85d2e7110f9046df42e5",
        janaf_path: "2a1bb000c0223a3227495b9103ae0feb553c4b2c26da721a89c464648c83b728",
    }
    for path, expected in verified_assets.items():
        if sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("original source changed; recheck CAS/mass/standard state and all tables")
    tables = read_tables(web_path)
    coefficient_tables = [t for t in tables if t["label"] == "Solid Phase Heat Capacity (Shomate Equation)"]
    if len(coefficient_tables) != 1:
        raise ValueError("unique quartz coefficient table required")
    rows = coefficient_tables[0]["rows"]
    indexed = {r[0]: r[1:] for r in rows if r}
    if indexed["Temperature (K)"] != ["298. to 847.", "847. to 1996."]:
        raise ValueError("source ranges changed; manual review required")
    coefficients = [[indexed[k][i] for k in "ABCDEFGH"] for i in (0, 1)]
    evaluated = [t for t in tables if t["label"] == "Data from Shomate Coefficients"]
    if len(evaluated) != 2:
        raise ValueError("two evaluation tables required")
    checked = []
    with localcontext() as context:
        context.prec = 60
        for segment, table in enumerate(evaluated):
            for row in table["rows"][1:]:
                if len(row) != 5:
                    raise ValueError("unexpected evaluation row")
                cp, h, s = shomate(coefficients[segment], row[0])
                errors = []
                gibbs_function = s - 1000*h/Decimal(row[0])
                for computed, printed in ((cp,row[1]),(h,row[4]),(s,row[2]),(gibbs_function,row[3])):
                    value = Decimal(printed)
                    # Half a printed decimal unit is formatting resolution,
                    # not measurement or parameter uncertainty.
                    half_unit = Decimal(5).scaleb(value.as_tuple().exponent-1)
                    errors.append(abs(computed-value) <= half_unit + Decimal("1e-10"))
                checked.append({"segment":segment,"temperature_k":row[0],"printed_rounding_pass":all(errors)})
        below, above = (shomate(c,"847") for c in coefficients)
        jump = {"h_jump_j_mol":str((above[1]-below[1])*1000),
                "s_jump_j_mol_k":str(above[2]-below[2]),
                "g_jump_j_mol":str((above[1]-below[1])*1000-Decimal(847)*(above[2]-below[2]))}
    janaf_rows = [[c for c in r if c] for t in read_tables(janaf_path) for r in t["rows"]]
    transition = [r for r in janaf_rows if r and r[0] == "847.000"]
    if len(transition) != 2 or transition[0][-1] != "I <--> II" or transition[1][-1] != "TRANSITION":
        raise ValueError("transition locator changed; review original table")
    facts = dict(schema_version=1,source_id="nist-quartz-shomate-janaf-1967-chase1998",
        classification="literature_constitutive_model",species="SiO2_quartz",cas="14808-60-7",
        molar_mass_kg_mol="0.0600843",standard_pressure_pa="100000",reference_temperature_k="298.15",
        coefficients_order=list("ABCDEFGH"),
        segments=[dict(temperature_range_k=r,coefficients=c) for r,c in zip(([298,847],[847,1996]),coefficients)],
        transition_847k_rows=transition,
        unknown={"molar_volume_m3_mol":None,"thermal_expansion":None,"compressibility":None,
                 "coefficient_covariance":None,"sludge_mineral_fraction":None},
        runtime_admission="source_candidate_no_solid_volume_or_material_package_not_auto_loaded")
    target = Path(__file__).parent
    (target/"facts.json").write_text(json.dumps(facts,indent=2)+"\n")
    audit = dict(evaluation_count=len(checked),comparison_columns=["Cp","H-Href","S","-(G-Href)/T"],printed_rounding_checks=checked,
                 all_printed_rounding_pass=all(r["printed_rounding_pass"] for r in checked),
                 shomate_jump_at_847k=jump,
                 source_assets={str(p.relative_to(root)):dict(sha256=sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
                                for p in (web_path,janaf_path)},
                 extractor_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                 facts_sha256=sha256((target/"facts.json").read_bytes()).hexdigest())
    (target/"extraction_audit.json").write_text(json.dumps(audit,indent=2)+"\n")
    print(json.dumps(audit,indent=2))
    if not audit["all_printed_rounding_pass"]:
        raise SystemExit("printed rounding comparison failed; artifacts preserved")


if __name__ == "__main__":
    main()
