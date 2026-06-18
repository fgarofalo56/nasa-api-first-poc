# ⚠️ Disclaimer & data notice

[Home](../README.md) > [Documentation](README.md) > **Disclaimer & data notice**

> [!WARNING]
> **Illustrative reference · sample data only · not an official NASA document.**

This repository and its documents present a **generic, illustrative use case** for an
API-first, zero-move data marketplace in a mission-enterprise context. They are provided
for **education and architecture demonstration only**.

## 🧭 Contents

- [Not affiliated / not official](#-not-affiliated--not-official)
- [Synthetic data only](#-synthetic-data-only)
- [No private or controlled information](#-no-private-or-controlled-information)
- [Pricing & products](#-pricing--products)
- [Warranty](#-warranty)

## 🚫 Not affiliated / not official

- This material is **not affiliated with, endorsed by, sponsored by, or approved by NASA**
  or any U.S. Government agency. References to "NASA," "OCIO," "Artemis," and mission
  programs are used **only to frame a realistic illustrative scenario**.
- It is **not** a proposal, statement of work, commitment, contract, or recommendation
  directed at any specific organization, and it does **not** represent the views of any
  agency or vendor.

## 🗄️ Synthetic data only

- **All data is synthetic and fabricated** by the generator in `data/synthetic_data.py`
  (deterministic, pure-stdlib). Every vendor, material, price, quantity, date, CAGE code,
  and supply-risk figure is invented for demonstration.
- Vendor names carry a `(SYNTHETIC)` suffix. The dataset contains **no real NASA, ITAR,
  EAR, CUI, procurement-sensitive, or otherwise controlled information**, and no real
  Artemis/SAP procurement records.
- Any resemblance to real organizations, suppliers, parts, or transactions is coincidental.

## 🔒 No private or controlled information

Nothing here should expose information an agency would consider non-public. If you adapt
this material, **do not** introduce real controlled data; keep the system isolated and the
data synthetic, or apply the appropriate classification and handling controls first.

## 💰 Pricing & products

- Azure pricing shown by `tools/azure_pricing.py` is pulled **live** from the public Azure
  Retail Prices API and is **list (PAYG)** pricing as of retrieval — indicative only, not a
  quote. No staffing or services figures are included.
- Product, service, and architecture choices are **examples**. Verify against current
  vendor documentation before relying on them.

## 📄 Warranty

Provided **"as is," without warranty of any kind**. Use at your own risk.
