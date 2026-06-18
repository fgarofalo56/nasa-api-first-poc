import { labelFor, PRIMARY_COLS } from "../labels.js";

// Renders any list of row objects as a table with human-friendly column headers.
// Rows that identify a material (have `matnr`) are openable -> drill-down detail. The
// open affordance is a REAL <button> in the leading cell (keyboard/SR accessible); the
// whole row is also clickable for mouse convenience. The <tr> stays a row (no role
// override) so table semantics are preserved.
export default function ResultTable({ rows, onOpen }) {
  if (!rows || rows.length === 0) return <div className="empty">No rows returned.</div>;

  const present = Object.keys(rows[0]).filter((c) => c !== "_ingested_at");
  const cols = [
    ...PRIMARY_COLS.filter((c) => present.includes(c)),
    ...present.filter((c) => !PRIMARY_COLS.includes(c)),
  ];
  const clickable = !!onOpen && present.includes("matnr");

  return (
    <div className="table-wrap" role="region" aria-label="Query results" tabIndex={0}>
      <table className={clickable ? "clickable" : ""}>
        <caption className="sr-only">
          Query results, {rows.length} rows{clickable ? " — open a row for full details" : ""}
        </caption>
        <thead>
          <tr>
            {clickable && <th scope="col"><span className="sr-only">Details</span></th>}
            {cols.map((c) => (
              <th key={c} scope="col">{labelFor(c)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const open = clickable ? () => onOpen(r) : undefined;
            return (
              <tr key={r.matnr || r.ebeln || i} className={clickable ? "row-link" : ""} onClick={open}>
                {clickable && (
                  <td className="row-open">
                    <button
                      type="button"
                      className="row-open-btn"
                      aria-label={`Open full details for ${r.maktx || r.matnr}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        open();
                      }}
                    >
                      🔎
                    </button>
                  </td>
                )}
                {cols.map((c) => (
                  <td key={c}>{renderCell(c, r[c])}</td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function renderCell(col, val) {
  if (val === null || val === undefined) return <span className="muted">—</span>;
  if (typeof val === "boolean") return val ? "yes" : "no";
  if (col === "risk_tier") return <span className={`tier ${String(val).toLowerCase()}`}>{val}</span>;
  if (col === "status" && /deficient/i.test(String(val))) return <span className="tier high">{val}</span>;
  return String(val);
}
