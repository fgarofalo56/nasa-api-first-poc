// Human-friendly labels for the raw SAP-shaped column names the data products expose,
// so the UI reads like a supply-chain dashboard, not a database dump.
export const FIELD_LABELS = {
  matnr: "Material #",
  maktx: "Material",
  matkl: "Family",
  program: "Program",
  criticality: "Criticality",
  sole_source: "Sole-source",
  risk_tier: "Risk tier",
  risk_score: "Risk score",
  avg_delay_days: "Avg delay (days)",
  po_count: "PO count",
  late_po_count: "Late POs",
  std_lead_time_days: "Lead time (days)",
  std_unit_cost_usd: "Unit cost (USD)",
  uom: "Unit",
  // vendor
  vendor_name: "Supplier",
  name1: "Supplier",
  lifnr: "Vendor #",
  cage_code: "CAGE code",
  past_perf_score: "Past performance",
  small_business: "Small business",
  // purchase orders
  ebeln: "PO #",
  ebelp: "Line",
  menge: "Qty",
  meins: "Unit",
  netpr: "Net price (USD)",
  netwr: "Net value (USD)",
  waers: "Currency",
  eindt: "Due date",
  bedat: "Ordered",
  actual_delivery: "Delivered",
  delay_days: "Delay (days)",
  pad_anomaly: "Pad anomaly",
  status: "Status",
};

export const labelFor = (col) =>
  FIELD_LABELS[col] ||
  col.replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase());

// Slugify a material NAME to its blueprint filename. MUST match the slug() in
// tools/make_product_blueprints.py (lowercase, non-alphanumerics -> '-', collapsed,
// trimmed) so /img/products/<slug>.svg resolves. We key by NAME, not the random NSN
// matnr, because there are only ~24 distinct part names but every matnr is unique.
export const slug = (name) =>
  String(name || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

// Blueprint render URL for a material name (empty string if no name → caller shows the
// inline glyph fallback). The <img onError> fallback covers any missing file.
export const productImageSrc = (maktx) => (maktx ? `/img/products/${slug(maktx)}.svg` : "");

// Columns worth showing first in the results table (others follow, _ingested_at hidden).
export const PRIMARY_COLS = [
  "maktx",
  "matnr",
  "program",
  "criticality",
  "risk_tier",
  "risk_score",
  "avg_delay_days",
  "sole_source",
];
