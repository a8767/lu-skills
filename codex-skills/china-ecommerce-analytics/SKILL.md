---
name: china-ecommerce-analytics
description: Consolidate authorized Chinese e-commerce shop exports into a multi-store operating report. Use for Taobao/Tmall, JD, Pinduoduo, Douyin, and Xiaohongshu store performance analysis; do not use it to bypass platform authentication or scrape restricted merchant data.
---

# China E-commerce Analytics

Build an auditable operating analysis from files the user has exported or from platform APIs to which the user has explicitly authorized access.

## Data access

- Prefer each platform's merchant API and OAuth authorization. Keep tokens and cookies out of source files, reports, logs, and chat responses.
- If interactive sign-in is necessary, the account owner completes passwords, SMS codes, QR scans, and CAPTCHA on the official platform page. Do not request, retain, or export credentials.
- Do not circumvent CAPTCHA, rate limits, access controls, or platform restrictions. Treat a public-market-data scraper as a source for price or competitor context only, never as an authoritative source of the user's shop operations.
- Before combining data, state the platforms, shops, date range, settlement currency, and whether figures are paid, shipped, settled, or estimated.

## Normalize before comparing

Create one row per `date × platform × shop` and retain the source file and original metric names. Normalize at least:

`gross_sales`, `paid_orders`, `refund_amount`, `refund_orders`, `ad_spend`, `shipping_subsidy`, `platform_commission`, `product_cost`, `inventory_units`, `visitors`, `buyers`, and `new_customers`.

Do not silently equate platform-specific definitions. Put missing values and unknown cost fields in an exceptions list. Compute derived metrics only when their inputs are present:

- net sales = gross sales − refund amount
- conversion rate = buyers / visitors
- average order value = net sales / paid orders
- refund rate = refund amount / gross sales
- contribution margin = net sales − product cost − ad spend − shipping subsidy − platform commission
- ROAS = attributable sales / ad spend

## Deliverable

Produce a concise daily, weekly, or monthly report with:

1. executive summary: total net sales, orders, margin, spend, and period-over-period movement;
2. platform and shop comparison with the source coverage clearly marked;
3. trend, funnel, refunds, profitability, inventory, and ad-efficiency findings as data permits;
4. anomalies with the metric, magnitude, likely drivers, and a recommended owner/action;
5. data-quality exceptions and assumptions.

Separate facts from inferences. Make recommendations actionable and rank them by expected impact and confidence. Ask for missing scope only when it would materially change a reported figure.
