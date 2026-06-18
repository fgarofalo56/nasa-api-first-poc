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
