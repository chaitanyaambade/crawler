# AxGen — Input Specification

> **Version:** 1.1
> **Last Updated:** January 30, 2026
> **Replaces:** 01_COMPANY_INFORMATION.md, 02_PRODUCT_INFORMATION.md, 03_CAMPAIGN_INFORMATION.md

---

## Principle

Ask the user only what the AI cannot figure out on its own. Everything else is the agent's job.

---

## Input Sources

| Source | What it provides | User effort |
|--------|-----------------|-------------|
| **Website scrape** | Company name, description, products, pricing, value props, brand voice, colors, social proof, landing pages | 0 — automatic |
| **Catalog connection** | Full product catalog, prices, categories, inventory, images (Shopify, WooCommerce, Amazon, etc.) | 0 — automatic after connection |
| **OAuth API import** | Ad account status, pixel/tracking setup, events configured, historical campaign data, existing audiences, past performance benchmarks | 0 — automatic after connection |
| **Agent research** | Competitor landscape, audience segments, demographics, psychographics, market trends, seasonality, industry benchmarks | 0 — automatic |
| **User conversation** | Subjective knowledge only the user has | 8-12 minutes |
| **Document upload** | Brand guidelines, pitch decks, past reports | Optional, 30 seconds |
| **Customer data upload** | Email/phone list for Custom Audiences and Lookalikes | Optional, 30 seconds |

---

## What the Agent Collects From the User

### Block 1: Website (5 seconds)

**Question:**
```
What's your website?
```

**Fields:**
- Website URL

**Fallback:** If no website, agent switches to extended conversation mode (Block 2 becomes longer, ~15 questions instead of 8).

**What this unlocks:** Agent scrapes in background and extracts company name, description, products, pricing, value props, brand voice, colors, review/social proof data, landing page URLs. Scrape runs while user continues answering questions.

---

### Block 1.5: Business Type (5 seconds)

**Question:**
```
What kind of business is this?

○ Online store (I sell products online)
○ Software / SaaS (subscription product)
○ Services (I sell expertise or appointments)
○ Local business (physical location)
○ App (mobile or web application)
○ Other: [        ]
```

**Fields:**
- Business type (single select)

**Why this matters:** This single answer changes how Blocks 3, 5, and 8 behave. A SaaS company's unit economics, goals, and offers are fundamentally different from a sports shop's. The agent adapts all downstream questions based on this.

**Agent may auto-detect:** If the website scrape clearly identifies the business type (e.g., Shopify store = e-commerce, "Book a consultation" = services), the agent pre-selects and asks the user to confirm instead of asking from scratch.

---

### Block 2: Confirm Scraped Profile + Product Catalog (30 seconds - 2 minutes)

**Not a question — a confirmation.**

Agent presents what it found and user confirms or corrects:

```
I found this on your website. Is this right?

Company: [extracted]
Type: [detected or selected from Block 1.5]
You sell: [extracted product/service categories]
Price range: [extracted]

[Looks right]  [Let me fix some things]
```

**Product catalog detection — three paths:**

```
Path A: Products found on website or connected platform
─────────────────────────────────────────────────────
I found [N] products in [N] categories:
- [Category 1] ([price range]) — [count] products
- [Category 2] ([price range]) — [count] products
- [Category 3] ([price range]) — [count] products

[Looks right]  [Let me fix some things]

Path B: Platform detected but not connected
───────────────────────────────────────────
I see you're on Shopify. Connect your store and I'll
pull your full product catalog automatically.

[Connect Shopify]  [Connect WooCommerce]  [Other platform]
[Skip — I'll add products manually]

Path C: No products found (weak website or no catalog)
──────────────────────────────────────────────────────
I couldn't find your products on your website.
Help me understand what you sell:

Option 1: Upload a product list
[Upload CSV/Excel]  [Download template]

Option 2: Tell me your main categories
Category 1: [           ] Price range: ₹[    ] - ₹[    ]
Category 2: [           ] Price range: ₹[    ] - ₹[    ]
Category 3: [           ] Price range: ₹[    ] - ₹[    ]
+ Add more

I don't need every product — just the main categories
you'd want to advertise.
```

**Supported catalog connections:**
- Shopify / WooCommerce (direct API)
- Amazon / Flipkart seller account
- Instagram Shop
- Google Business Profile (for local businesses)
- CSV / Excel upload (manual fallback)

**What the agent gets from catalog connection:**
- All products with names, descriptions, prices
- Product categories and hierarchy
- Product images
- Inventory / stock status
- Best sellers and ratings (if available)

**What this replaces:**
- Company doc: Section 1 (Business Identity), Section 2.3-2.4 (Brand Story, Differentiators — partial)
- Product doc: Section 1 (Product Overview), Section 3.3 (Key Features)

**Why it matters:** If the scrape got the basics right, the user spends 10 seconds here. If products weren't found, the fallback paths ensure the agent still gets what it needs without a 50-field form.

---

### Block 3: Unit Economics (1 minute)

**Questions adapt based on business type (Block 1.5):**

**E-commerce (single product or small catalog):**
```
Q1: "What does it cost you to make or deliver your product?"
    → Average cost per unit (COGS)

Q2: "What's a typical order value?"
    → Average Order Value
```

**E-commerce (multi-category catalog):**
```
Q1: "What are your approximate margins by category?"

    I found these categories on your site:
    - [Category 1]: margin ~[  ]%
    - [Category 2]: margin ~[  ]%
    - [Category 3]: margin ~[  ]%

    Or: ○ Roughly the same across all (~[  ]%)

Q2: "What's a typical order value?"
    → Average Order Value
```

**SaaS / Software:**
```
Q1: "What's your monthly plan price?"
    → Starting plan / most popular plan price

Q2: "How long does an average customer stay?"
    → Average retention in months
    → (Agent calculates LTV = monthly price × retention)
```

**Services / Lead gen:**
```
Q1: "What's a typical customer worth to you over a year?"
    → Customer lifetime value

Q2: "What's the most you'd pay for a qualified lead?"
    → Target cost per lead (optional — agent can calculate)
```

**Local business:**
```
Q1: "What's a typical customer spend per visit?"
    → Average transaction value

Q2: "How often do customers come back?"
    → Weekly / Monthly / Few times a year / One-time
    → (Agent calculates LTV from frequency × transaction value)
```

**App:**
```
Q1: "How does your app make money?"
    → Paid download / In-app purchases / Subscription / Ads / Free

Q2: "What's a user worth in the first 30 days?"
    → D30 LTV (optional — agent estimates from model if unknown)
```

**Fields (vary by type):**
- COGS per unit OR margin % per category (e-commerce)
- Monthly price + retention months (SaaS)
- Customer LTV + optional target CPL (services)
- Transaction value + visit frequency (local)
- Monetization model + D30 LTV (app)
- Average Order Value (e-commerce, local)

**Fallback:** If user doesn't know, agent estimates from industry averages and flags as approximate. Example: "I'm estimating your margin at ~55% based on fashion e-commerce averages. This affects your profitability targets — update this when you have exact numbers."

**What the agent calculates from this (no user input needed):**
- Gross margin % (e-commerce)
- Break-even ROAS (e-commerce)
- Maximum sustainable CPA
- Target ROAS / Target CPA
- LTV estimate (method varies by business type)
- Payback period (SaaS)

**What this replaces:**
- Product doc: Entire Section 2 (Pricing & Economics — 7 tables, 20+ fields)

---

### Block 4: Your Customer (2 minutes)

**Questions:**
```
Q1: "Describe your best customer in a sentence or two.
     Not who you wish bought — who actually does."

Q2: "What's the main reason they buy from you instead
     of someone else?"
```

**Fields:**
- Customer description (free text)
- Key differentiator (free text)

**What the agent derives from these two answers:**
- Target audience segments (refined by research)
- Buyer personas (agent builds, user validates later in strategy review)
- Positioning statement
- Core messaging angle
- Competitive differentiation for ad copy
- USP for headlines

**What this replaces:**
- Company doc: Entire Section 4 (Target Customer Profile — 4 subsections, 3 persona templates, demographics table, psychographics, negative personas)
- Product doc: Entire Section 3 (Value Proposition — problem/solution, benefits, features, USP)
- Product doc: Entire Section 5 (Target Customer — buyer profiles, pain points, desires, purchase triggers)
- Product doc: Entire Section 6 (Purchase Journey — buying behavior, objections, barriers, competitor alternatives)

**Why two questions work:** The agent doesn't need the user to fill out persona templates with demographics, psychographics, and pain points. The agent researches those. It needs the owner's intuitive understanding of WHO buys and WHY — then it builds the detailed profiles itself and presents them for validation during strategy review.

---

### Block 5: Goal and Budget (1 minute)

**Questions adapt based on business type (Block 1.5):**

```
Q1: "What's the main thing you want from ads?"
```

**Goal options by business type:**

| Business type | Options |
|--------------|---------|
| E-commerce | Sales / Awareness / Repeat purchases |
| SaaS | Trial signups / Demo bookings / Awareness |
| Services | Leads / Appointments / Awareness |
| Local business | Store visits / Bookings / Calls / Awareness |
| App | App installs / In-app actions / Awareness |

```
Q2: "How much can you spend per month on ads?"
    → Monthly budget (number)
```

**Fields:**
- Primary objective (select — options vary by business type)
- Monthly ad budget (number)

**What the agent handles from here (no user input needed):**
- Target ROAS and max CPA (calculated from Block 3 margins)
- Daily spend limit (budget / 30)
- Platform recommendation (based on business type, budget, goal)
- Budget allocation across platforms
- Budget allocation across funnel stages
- Campaign count recommendation (based on budget and plan limits)
- Campaign layer strategy (brand vs category vs product — agent decides based on budget and catalog size)

**What this replaces:**
- Campaign doc: Section 1 (Campaign Objective), Section 2 (Target Metrics — all KPIs), Section 3 (Budget & Timeline)

---

### Block 6: Where You Sell (30 seconds)

**Question:**
```
"Where are your customers?"
    → India only / India + specific countries / Global
```

**For local businesses (detected from Block 1.5):**
```
"Where are your customers?"
    → Within [  ] km of my location
    → Specific areas in my city: [          ]
    → Entire city ([detected city])
```

**Fields:**
- Geographic scope (select)
- Specific countries or radius (if applicable)

**What this replaces:**
- Company doc: Section 3.1 (Geographic Markets — 4 fields including languages and exclusions)

**Why this is enough:** The agent infers language from geography and website language. Excluded regions are rare and can be handled in compliance block or strategy review.

---

### Block 7: Restrictions (1 minute)

**Question:**
```
"Any restrictions I should know about?"

□ We never offer discounts
□ We can't make health/results claims
□ We're in a regulated industry (alcohol, finance, healthcare)
□ There are specific words or claims we can't use
□ No restrictions

If anything specific: [free text field]
```

**Fields:**
- Restriction checkboxes (multi-select)
- Specific restrictions (free text, optional)

**What this replaces:**
- Company doc: Entire Section 7 (Compliance & Legal — special ad categories, industry restrictions, legal restrictions, approval requirements)
- Product doc: Entire Section 11 (Compliance — claim restrictions, regulatory, competitor mention policy)

**Why checkboxes + free text works:** Most businesses have zero restrictions. For those that do, the checkboxes catch the common ones (regulated industry, no discounts). The free text catches edge cases ("We can't mention competitor X by name"). The agent uses this as a hard constraint during ad copy generation and creative strategy.

---

### Block 8: Available Offers (1 minute)

**Question adapts based on business type (Block 1.5):**

**E-commerce:**
```
"What can I offer in ads to get people to buy?"

□ Percentage discount (max: [  ]%)
□ Fixed amount off (max: ₹[    ])
□ Free shipping (above ₹[    ] / on all orders)
□ First-order discount
□ Bundle deal
□ Money-back guarantee ([  ] days)
□ No offers — sell at full price only
```

**SaaS:**
```
"What can I offer to get people to sign up?"

□ Free trial ([  ] days)
□ Extended free trial
□ Discount on annual plan ([  ]% off)
□ Free tier available
□ Money-back guarantee ([  ] days)
□ No offers — standard pricing only
```

**Services / Lead gen:**
```
"What can I offer to get people to reach out?"

□ Free consultation
□ Free audit / assessment
□ Downloadable guide / resource
□ First session discount ([  ]% off)
□ Money-back guarantee
□ No offers — they book at standard rates
```

**Local business:**
```
"What can I offer to get people through the door?"

□ First visit discount ([  ]% off)
□ Loyalty deal (buy X get Y)
□ Seasonal offer
□ Free trial class / session
□ Bundle / package deal
□ No offers — standard pricing only
```

**App:**
```
"What can I offer to get people to download?"

□ Free premium trial ([  ] days)
□ Referral bonus
□ In-app credits (₹[    ] value)
□ Launch discount ([  ]% off)
□ No offers — standard pricing only
```

**Fields:**
- Available offer types (multi-select with parameters — options vary by business type)

**What this replaces:**
- Product doc: Entire Section 7 (Offers & Promotions — available offers table, restrictions, seasonal calendar)
- Campaign doc: Entire Section 4 (Offer & Promotion)

**Why this matters for the agent:** Offers are one of the strongest levers in ad performance. The agent needs to know what's available so it can test offer-led vs. value-led messaging. If the user says "no offers," the agent adjusts creative strategy to focus on brand/product value instead.

---

### Block 9: Past Experience (1 minute, optional)

**Question:**
```
"Have you run paid ads before?"

● Yes
○ No, first time

[If yes]:
"In a sentence or two — what worked and what didn't?"
```

**Fields:**
- Has run ads before (boolean)
- What worked / didn't (free text, optional)

**What this replaces:**
- Company doc: Entire Section 6 (Historical Performance — benchmarks table, what worked/failed, other channels, organic channels)
- Product doc: Entire Section 12 (Historical Performance — best ads, failed approaches, audience performance)

**Why free text, not tables:** The hard performance data (CPA, ROAS, CTR, best audiences, top creatives) comes from the API import automatically. This question captures the subjective insight — "video ads crushed it but carousels bombed" or "we tried targeting men and it was a total waste" — things the data might show but the user's interpretation adds context.

---

### Block 10: Ad Account Connection (2 minutes)

**Not a question — an action.**

```
Connect your Meta ad account so I can:
• Import your past campaign data
• Check your tracking setup
• Create campaigns when you're ready

I'll never spend money or make changes without your approval.

[Connect Meta Ads]  (required)
[Connect Google Ads] (optional)
```

**What the agent gets automatically after connection:**
- Account health status
- Pixel installation and event configuration
- Conversions API status
- Event Match Quality score
- Last 12 months of campaign data
- Best/worst performing campaigns, ad sets, ads
- Existing custom audiences and lookalikes
- Account spending limits
- Billing status

**What this replaces:**
- Company doc: Entire Section 5 (Technical Infrastructure — 5 subsections, 15+ tables)
- Campaign doc: Section 8 (Tracking & Attribution), Section 13 (Pre-launch Checklist — tracking portion)

---

### Block 11: Creative Assets (after strategy, not during onboarding)

**Not asked during onboarding.** Assets are requested AFTER strategy generation, when the agent knows exactly what it needs.

```
To build your campaigns, I need:

Required:
□ 3 product images (1080x1080 or larger)
□ 1 lifestyle image (1080x1350)

Recommended:
□ 1 short video (15-30 sec, vertical)
□ 2 additional product angles

[Upload assets]  [I only have some of these]
```

**What this replaces:**
- Product doc: Entire Section 8 (Creative Assets — photography table, video table, UGC table, creative guidelines)
- Campaign doc: Section 6.3 (Creative Assets for Campaign)

**Why after strategy:** The strategy produces a creative brief that specifies exactly what formats and angles are needed. Asking for assets before strategy means users upload random files. Asking after means the request is specific and the user knows exactly what to provide.

---

### Block 12: Document Upload (optional, any time)

```
Have any of these? Upload and I'll extract what I need.

[Brand guidelines PDF]
[Pitch deck / investor deck]
[Past campaign report]
[Customer list CSV]
```

**What this replaces:**
- Company doc: Section 2.5 (Brand Guidelines)
- Any structured data the user has already prepared

**How the agent uses uploads:**
- Brand guidelines → Extracts colors, fonts, voice rules, logo usage, photography style. Applies as constraints to creative strategy.
- Pitch deck → Extracts positioning, market size, competitive landscape, business model. Supplements website scrape.
- Past campaign report → Extracts performance benchmarks, winning strategies, failed approaches. Supplements API import.
- Customer list → Creates Custom Audiences and Lookalike seeds. Hashed client-side before upload.

---

## Multi-Product Handling

Most businesses sell more than one thing. The agent handles this without making the user repeat inputs per product.

### How product data is collected

| Scenario | How it works | User effort |
|----------|-------------|-------------|
| **E-commerce with platform** (Shopify, WooCommerce, etc.) | Agent connects to platform API, pulls entire catalog — names, prices, categories, images, inventory | 0 — automatic |
| **Website with products listed** | Agent scrapes all products during Block 1 | 0 — automatic |
| **Marketplace seller** (Amazon, Flipkart) | Agent connects to seller account, pulls catalog | 0 — automatic |
| **Small catalog, no platform** (5-20 products) | Agent scrapes what it can, user confirms/corrects in Block 2 | 30 seconds |
| **No product data available** (weak website, physical-only store) | User uploads CSV or manually enters top categories + price ranges in Block 2 (Path C) | 2 minutes |

### How margins work with multiple products

The agent doesn't ask margin per SKU. It asks per **category**:

```
I found 3 product categories:
- Cricket gear (₹500 - ₹15,000) — margin: [  ]%
- Running shoes (₹2,000 - ₹12,000) — margin: [  ]%
- Gym equipment (₹1,000 - ₹50,000) — margin: [  ]%

Or: ○ Roughly the same across all (~[  ]%)
```

This gives the agent enough to calculate break-even ROAS and target CPA per category, which drives campaign budget allocation.

### How the agent decides what to advertise

The user does NOT choose which products to advertise. The agent decides based on:

| Signal | Agent decision |
|--------|---------------|
| Budget is small (₹10-15K/mo) | Brand awareness + 1-2 top categories only |
| Budget is medium (₹30-50K/mo) | Brand + category campaigns + hero products |
| Budget is large (₹1L+/mo) | Full funnel — brand, categories, products, retargeting |
| High-margin category exists | Push that category harder in ad spend |
| Seasonal relevance | Auto-promote relevant categories (cricket gear during IPL) |
| Product getting clicks but no sales | Agent flags it, suggests offer or pauses |
| New product added to catalog | Agent evaluates and suggests testing budget |

### Campaign layering for multi-product businesses

The agent builds campaigns in layers. The user sees one strategy — the agent manages the layers:

- **Layer 1: Brand** — promotes the business overall (always on, low budget)
- **Layer 2: Category** — promotes product categories based on season/margin/demand
- **Layer 3: Product** — promotes hero products with highest margin or best performance
- **Layer 4: Retargeting** — re-engages visitors with products they viewed

Which layers are active depends on budget, business type, and performance data. The agent manages this — the user approves the strategy.

---

## What the Agent Does NOT Ask the User

These are handled automatically:

| Category | How the agent handles it |
|----------|------------------------|
| Brand voice & tone | Extracted from website copy analysis |
| Brand colors & fonts | Extracted from website CSS / logo |
| Product catalog | Scraped from website or pulled from connected platform |
| Product images | Pulled from catalog or website scrape |
| Competitor list | Researched based on industry and positioning |
| Competitor positioning | Researched from competitor websites and ad library |
| Audience demographics | Researched and built from user's customer description |
| Audience psychographics | Researched based on industry and customer profile |
| Customer pain points | Researched — validated in strategy review |
| Purchase triggers | Researched based on product type and industry |
| Market trends | Researched from industry data |
| Seasonality | Researched from industry data + historical campaigns |
| Industry benchmarks | Loaded from benchmark database |
| Messaging framework | Generated during strategy phase |
| Headlines and hooks | Generated during campaign creation |
| Ad copy variations | Generated during campaign creation |
| Campaign structure | Designed by agent based on strategy |
| Campaign layers | Decided by agent based on budget, catalog size, margins |
| Which products to advertise | Decided by agent based on margins, performance, season |
| Audience targeting parameters | Built by agent from research |
| Bid strategy | Decided by agent based on goal and budget |
| Placements | Decided by agent (Advantage+ default) |
| Testing plan | Created by agent |
| Optimization rules | Set by agent based on targets |
| Reporting cadence | Defaulted, user can adjust |
| UTM parameters | Auto-generated |
| Pre-launch checklist | Automated validation |
| Pixel/tracking status | Detected via API |
| Landing page status | Checked by agent |
| Risk assessment | Assessed by agent |

---

## Summary: Old vs New

| Old Approach | New Approach |
|-------------|-------------|
| 3 separate documents | 1 conversation |
| 2,066 lines | 12 blocks |
| 300+ fields | ~15 user inputs |
| 45-90 minutes of form filling | 8-12 minutes of conversation |
| User provides everything | User provides only what AI can't figure out |
| Static documents | Living data — agent updates as it learns |
| Same for every user | Adaptive — skips questions the scrape already answered |
| E-commerce only | Works for any business type |
| One product assumed | Multi-product handled automatically |

## Complete Input Table

| # | Block | User provides | Format | Time | Required? |
|---|-------|--------------|--------|------|-----------|
| 1 | Website | URL | Text field | 5 sec | Yes |
| 1.5 | Business type | What kind of business | Single select | 5 sec | Yes (agent may auto-detect) |
| 2 | Confirm profile + catalog | Corrections to scraped data, product catalog | Review & edit | 30 sec - 2 min | Yes |
| 3 | Unit economics | Margins, AOV/LTV (adapts by type) | Numbers | 1 min | Yes (can estimate) |
| 4 | Your customer | Who buys, why you | Free text (2 Qs) | 2 min | Yes |
| 5 | Goal & budget | Objective (adapts by type), monthly budget | Select + number | 1 min | Yes |
| 6 | Geography | Where you sell / serve | Select | 30 sec | Yes |
| 7 | Restrictions | What you can't say/do | Checkboxes + text | 1 min | Yes |
| 8 | Offers | What deals you can run (adapts by type) | Checkboxes | 1 min | Yes |
| 9 | Past experience | What worked/didn't | Free text | 1 min | Optional |
| 10 | Ad account | OAuth connection | Button click | 2 min | Yes (Meta) |
| 11 | Creative assets | Images, videos | File upload | 2-5 min | After strategy |
| 12 | Documents | Guidelines, decks, lists | File upload | 30 sec | Optional |

## For Subsequent Campaigns

After the first campaign, the agent already has Blocks 1-10. New campaigns only need:

| Input | Example |
|-------|---------|
| What's different | "Diwali sale, 30% off, Oct 15 - Nov 5" |
| Budget for this campaign | "₹1.5L" |
| New creative assets (if any) | Upload Diwali-themed images |
| New offers (if different) | "30% off sitewide" |

Everything else carries forward from the existing client profile.

---

## Internal Data Model

The agent stores collected information in three internal categories. The user never sees this structure — it's how the agent organizes knowledge.

### Company Context (stable, updated rarely)
- Business identity (name, website, industry, **business type**)
- Brand voice and tone
- Geographic markets
- Compliance and restrictions
- Connected platforms and tracking status

### Product Context (semi-stable, updated when offerings change)
- **Product catalog** (all products, categories, prices — from scrape/platform/upload)
- **Margins per category** (from user input)
- Unit economics and LTV calculations (method varies by business type)
- Available offers
- Creative assets
- Social proof data

### Campaign Context (per-campaign, created by agent)
- Objective and targets (from user goal + agent calculations)
- Strategy document (agent-generated)
- **Campaign layers** (brand / category / product / retargeting — agent decides)
- **Products selected for advertising** (agent decides based on margins, performance, season)
- Campaign structure (agent-built)
- Audience configuration (agent-researched)
- Ad copy and creatives (agent-generated)
- Optimization rules (agent-set)
- Performance data (agent-monitored)

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-30 | Initial spec — replaces three legacy intake documents |
| 1.1 | 2026-01-30 | Added business type detection (Block 1.5), adaptive blocks (3, 5, 8), multi-product handling, product catalog fallback paths, campaign layering |
