// Renders any list of row objects as a table (dynamic columns) — works for any source.
export default function ResultTable({ rows }) {
  if (!rows || rows.length === 0) return <div className="empty">No rows returned.</div>;
  const cols = Object.keys(rows[0]);
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {cols.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {cols.map((c) => (
                <td key={c}>{renderCell(c, r[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderCell(col, val) {
  if (typeof val === "boolean") return val ? "yes" : "no";
  if (col === "risk_tier") return <span className={`tier ${String(val).toLowerCase()}`}>{val}</span>;
  if (col === "status" && /deficient/i.test(String(val)))
    return <span className="tier high">{val}</span>;
  return String(val);
}
