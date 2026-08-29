# Hanafi Fara'id Estate Workbook

A configurable model of the estate of **Hanif** (d. 20 Jul 2022) and **Khudsia** (d. 28 Oct 2025),
computed under **Sunni Hanafi** inheritance rules, with a Streamlit front end.

> **This is a computational aid, not a fatwa and not legal advice.** Every fiqh position taken
> here is stated openly and is switchable. Take the printed output to a qualified Hanafi mufti
> for the fiqh, and to an Indian succession lawyer for the *Shariat Application Act 1937*,
> partition procedure, and the Karnataka revenue/BDA formalities.

---

## 1. The first and most important step: what the fara'id does *not* touch

Inheritance opens **at the instant of death**, over what the deceased owned **at that instant**.
Everything an owner did while alive is his own affair and cannot be reopened by the heirs.
Sorting the facts into these buckets *before* doing any arithmetic removes most of the argument.

### 1a. OUTSIDE the fara'id — closed, not reviewable

| Ref | Fact | Why it is outside |
|-----|------|-------------------|
| **X1** | Neelsandra sold for ₹41,00,000 in 2015, in the father's presence | The father's own `tasarruf` in his own `mulk`. The corpus left his ownership seven years before death, so it never entered the `tarikah`. Only whatever **remained of the proceeds** on 20 Jul 2022 is estate property. |
| **L2** | ₹28,00,000 given to B2 in 2015 for business | A completed **hiba** — offer, acceptance and `qabd` (delivery) in the donor's lifetime. Valid and **irrevocable** in favour of a descendant. **Hanafi law has no hotchpot/advancement doctrine**, so it is *not* set off against B2's share. Unequal gifting between children is at most *makruh* (hadith of Nu'man b. Bashir) — a moral defect, not a proprietary one. |
| **L3** | B1 living in P3 since 2008 with the parents | Permissive occupation (`'ariyya`) from the living owner. No liability for anything before 20 Jul 2022. |
| **L4** | B2 living in P2 flat 2/1 since Jul 2019 | Same, for the pre-death period. |
| **L5** | Rents collected by B1 from 2015 to 20 Jul 2022 (**₹42.12 L** on these figures) | Collected as the father's `wakil` during his life. A father-to-son account, not an estate account. |
| **—** | P2 flats 2/2, 2/3, 1/4, 1/5 sold to outside owners | Conveyed before death. Neither the flats nor their rents are estate property. |
| **—** | The 35% partner's stake in P1 | Never the deceased's `mulk`; never entered the `tarikah`. |

**The one door that stays open on L5.** If the family can *prove* B1 collected without the
father's consent, those rents convert into a **`dayn`** (debt) owed **to** the `tarikah`, payable
before any shares. That is an allegation with a burden of proof, not a default. The
`include_pre_death_flows` switch models it; keep it **OFF** unless you can prove it.

**The one door that stays open on L2.** The gift stands in law. What the family *may* do is agree
a **`sulh`** (compromise) in which B2 accepts a set-off. That is a negotiated settlement, not an
entitlement of the other four. The `treat_2015_gift_as_advance` switch models it.

### 1b. SUSPENDED (`mawquf`) — vests in principle, cannot be quantified yet

| Ref | Fact | Treatment |
|-----|------|-----------|
| **P6** | Berli Street, 600 sqft, title contested by an SC/ST party, pending in the Supreme Court | Shares vest, but the asset cannot be valued or partitioned until decreed. **Distribute the other five properties now and keep P6 in a separate schedule** with the same 2:1 fractions recorded, to be given effect if and when the decree comes. Excluding it does not prejudice anyone. |

### 1c. INSIDE the fara'id — fully reviewable

- The corpus of **P1–P5** as at 20 Jul 2022 (P1 only to the extent of the 65% share).
- **All rent from 20 Jul 2022 onwards** on every estate property — it accrues on jointly owned
  property and belongs to the heirs in their exact fractions, no matter whose hand collects it.
- **All estate expenditure from 20 Jul 2022** — taxes, maintenance, repairs. A co-owner who
  preserves the common property may recover the others' rateable share.
- The **140 g of gold** — the mother's own `mulk`, so it is her `tarikah`, divisible 2:1.
- Refundable **tenant deposits (₹16,00,000)** — an `amanah` held for tenants and therefore a
  `dayn` of the estate, payable before the shares.

### 1d. CONTESTED — the two live issues

**(i) S1's 30 g bangles.** The Hanafi test is mechanical: a `hiba` is complete only on
`ijab` + `qabul` + **`qabd`** — actual delivery of possession in the donor's lifetime. If S1 held
the bangles as her own from before the death, it is a valid gift and out of the estate. If it was
a spoken intention, an announcement of what she *would* get, or a death-bed direction, it is a
**`wasiyya` to an heir — void in Hanafi law without the unanimous consent of every other adult
heir after the death**. S2 and S3 are refusing that consent, so on the stated facts the 30 g
falls back into the pool. Switch `s1_gold_gift_valid` ON only if `qabd` can be shown.

**(ii) The equal five-way split of the gold.** This departs from the 2:1 rule. It is lawful only
as a **`sulh`** with the free, informed consent of every adult heir. If everyone genuinely agreed,
it is binding and closed. If some heirs did not, it must be redone or compensated in cash.
**Record the consent in writing.**

### 1e. The policy question that moves the most money

**Does an heir occupying joint property owe rent to the others?**

- **Classical Hanafi: no.** A `sharik` in occupation of `musha'` (undivided joint) property owes
  no `ujrat al-mithl` to the co-owners — the benefit (`manfa'ah`) does not bear `daman`. This is
  the app's default, and it is why the switch starts OFF.
- **Indian law: often yes.** A co-owner in exclusive possession can be made to account for
  **mesne profits** (CPC s.2(12)) in a partition suit.
- **Practically:** the family can agree a `sulh` charging notional rent from the date of death.

The switch flips both occupations at once, which keeps it even-handed — B1 in the HSR duplex at
₹50,000/month and B2 in flat 2/1 at ₹15,000/month. Turning it ON roughly **doubles** the
inter-heir settlement and moves B1's position from about **−₹11 L to −₹27 L**.

---

## 2. The share arithmetic

### Stage 1 — Hanif, d. 20 Jul 2022
Heirs: widow + 2 sons + 3 daughters. No surviving parent of the deceased assumed.

| Heir | Basis | Share | /56 |
|---|---|---|---|
| Khudsia (widow) | Qur'an 4:12 — 1/8 because children exist | **1/8** | 7 |
| Suhail (son) | `'asaba bi-ghayrihi`, 2:1 | **1/4** | 14 |
| Jameel (son) | " | **1/4** | 14 |
| Fouzia (daughter) | " | **1/8** | 7 |
| Shabanaz (daughter) | " | **1/8** | 7 |
| Shahnaz (daughter) | " | **1/8** | 7 |

Base 8 for the widow's quota; the 7/8 residue splits into 7 units (2+2+1+1+1) → common base **56**.

### Stage 2 — Khudsia, d. 28 Oct 2025 (`munasakha`)
Her `tarikah` = her undistributed **1/8 of the father's estate** + her **gold**.
Heirs: 2 sons + 3 daughters. No spouse, no fixed sharer — the children take everything as
`'asaba`, base **7**: each son **2/7**, each daughter **1/7**.

### Consolidated

| Heir | From father | Via mother | **Combined** | % |
|---|---|---|---|---|
| Suhail | 1/4 | 1/8 × 2/7 | **2/7** | 28.571% |
| Jameel | 1/4 | 1/8 × 2/7 | **2/7** | 28.571% |
| Fouzia | 1/8 | 1/8 × 1/7 | **1/7** | 14.286% |
| Shabanaz | 1/8 | 1/8 × 1/7 | **1/7** | 14.286% |
| Shahnaz | 1/8 | 1/8 × 1/7 | **1/7** | 14.286% |

**The chain closes on itself.** Because the widow's 1/8 flows back to the same five children in
the same 2:1 proportion, the consolidated split equals a single-stage 2:1 division. That is a
happy coincidence of this particular family, **not a general rule** — it would not hold if the
mother had other heirs, or if an heir had died, disclaimed, or settled between the two deaths.
The two stages still must be run separately for the **income** between 20 Jul 2022 and
28 Oct 2025, where the mother was a live 1/8 stakeholder. The app does exactly that.

---

## 3. Headline numbers (defaults: P6 excluded, notional rent OFF, gold 2:1, as at 28 Aug 2026)

**Corpus**

| | |
|---|---|
| P1 Bommanahalli — 13,004 sqft × ₹18,000 × 65% | ₹15.21 cr |
| P3 HSR Layout | ₹5.00 cr |
| P5 Kanakapura | ₹3.70 cr |
| P2 BismillahNagar (our 10 flats + tower) | ₹2.80 cr |
| P4 Anjanapura | ₹2.50 cr |
| P6 Berli Street | *suspended — sub judice* |
| **Gross corpus** | **₹29.21 cr** |
| less refundable tenant deposits | (₹26.00 L) |
| **Net distributable** | **₹28.95 cr** |

**Per head, corpus only**

| Heir | Share | Corpus entitlement |
|---|---|---|
| Suhail, Jameel | 2/7 each | **₹8.27 cr** each |
| Fouzia, Shabanaz, Shahnaz | 1/7 each | **₹4.14 cr** each |

**Post-death income & expenses accounted** (20 Jul 2022 → 28 Aug 2026)

| | |
|---|---|
| Rent that accrued to the estate | ₹52.12 L |
| Estate expenses (tax, maintenance, repairs) | ₹7.43 L |
| **Net estate income** | **₹44.69 L** |
| Excluded as pre-death or un-charged notional rent | ₹2.09 cr |

**Inter-heir settlement** (default switches) — positive = owed to this heir

| Heir | Net |
|---|---|
| Suhail | **−₹11.22 L** |
| Jameel | −₹0.97 L |
| Fouzia | +₹2.01 L |
| Shabanaz | +₹5.09 L |
| Shahnaz | +₹5.09 L |

Shabanaz and Shahnaz have received **nothing at all** since the father's death while holding 1/7
each. That is the single clearest finding in the model, and it is true on every basis and every
switch setting.

The mother's own position (−₹4.58 L: she drew tower rent exceeding her 1/8) was never settled in
her lifetime, so it rolls into her `tarikah` and re-splits 2:1 among the five — the app does this
automatically and shows it.

---

## 4. Analytics the app produces

| View | What it answers |
|---|---|
| **Overview** | Corpus, liabilities, income, who is up and who is down, concentration risk |
| **Fara'id shares** | Both stages, base 56 and base 7, the consolidation, and a sensitivity table of what would change the shares |
| **Properties & corpus** | Valuation, the 65%/100% carve-outs, the liability waterfall, the full rent roll, cash yield vs imputed rent forgone |
| **Estate ledger** | Every stream cut at each death date, in-scope vs out-of-scope with the reason printed on each row, collector × window and payer × category pivots |
| **Heir statement** | One heir: share, corpus slice per property, flow account, gold position, what they occupy, line-by-line allocation |
| **Gold** | Entitled vs actually taken in grams, and the two contested issues |
| **Scope register** | The §1 segregation as live data — IN / OUT / SUSPENDED / PARTIAL with fiqh reasoning |
| **Settings** | Edit every table online and save back to `config.json` |

### Findings worth acting on

1. **Concentration.** P1 alone is **52%** of the corpus. No equitable partition in kind is
   possible without selling it or loading the other five heavily against it.
2. **The estate is a poor investment held jointly.** Cash rent annualises to about **₹12.69 L**
   on a **₹29.21 cr** corpus — roughly **0.43% gross**, before tax, maintenance and vacancy.
   P1 and P4 are bare land and yield nothing, yet they are **61%** of the value. Holding jointly
   earns well under a fixed deposit *and* generates the rent disputes. That asymmetry is the
   strongest financial argument for selling and distributing.
3. **The gold is generating heat out of all proportion.** It is under 1% of the estate. Settle it
   with a cash adjustment and move on.
4. **The notional-rent switch is worth about ₹16 L** and is the only genuinely contestable fiqh
   question with real money attached. Decide it once, in writing, before valuing anything.
5. **Two heirs have received nothing for four years.** Whatever else is agreed, an interim
   distribution of accumulated rent to S2 and S3 is overdue and is not controversial on any view.

---

## 5. Users and per-user workspaces

Five fixed users, one per heir. Picking a name on the opening screen loads **that person's
own copy** of the configuration. One sibling modelling *"what if we charge notional rent"*
cannot disturb anyone else's view.

| User | Heir | |
|---|---|---|
| `suhail@gmail.com` | B1 | Suhail, son |
| `fouzia@gmail.com` | S1 | Fouzia, daughter |
| `jameel@gmail.com` | B2 | Jameel, son |
| `shabanaz@gmail.com` | S2 | Shabanaz, daughter |
| `shahnaz@gmail.com` | S3 | Shahnaz, daughter |

The list is hardcoded in `auth.py` (`USERS`); `people[].email` in `config.json` mirrors it so
the mapping is visible in the Settings tables.

> ### ⚠️ There is no authentication
> No password is asked for. **Anyone who can reach the app can open any of the five
> workspaces** and read or overwrite them. That is fine on a laptop or a machine the family
> controls; it is not fine on anything reachable from the internet. Workspaces are also
> stored as plain unencrypted JSON on the server's disk.
>
> A Google OAuth version — real sign-in, an allow-list, and per-account isolation — is parked
> in `auth_google.py`. It exposes the same API, so switching back means renaming it over
> `auth.py`, restoring `streamlit[auth]` in `requirements.txt`, and filling in
> `.streamlit/secrets.toml` from `.streamlit/secrets.toml.example`. That module's own setup
> screen walks through the Google Cloud console steps.

### How the state is separated

```
config.json                     the SHARED baseline - the agreed facts
   │
   └── seeded on first open ──► user_data/<name>-<hash>.json          one per user
                                user_data/revisions/<name>-<hash>/    last 25 saves
```

- The first time a user opens the app their workspace is seeded from the shared baseline.
- Every later visit loads **their** saved workspace — policy switches, reckoning basis,
  as-of date, and any edits they made to properties, streams, liabilities or gold.
- **Save my settings** writes to their file only. The shared baseline is never touched.
- Each save snapshots the previous version, so any save can be rolled back from
  **Settings → My workspace → Revision history** (25 kept).
- **Reset to shared baseline** pulls the agreed facts back in, discarding unsaved changes;
  the saved workspace survives until the next Save.
- **Switch user** returns to the picker. Unsaved changes are discarded, and all widget state
  is cleared so nothing carries across.
- Any user can publish their configuration *as* the new shared baseline
  (**Settings → My workspace → Admin**) — that is how agreed corrections to the facts get
  distributed to everyone's next seed.

The selected user is remembered in the URL (`?user=suhail@gmail.com`), so a reload keeps you
where you were and each person can bookmark their own workspace.

`user_data/` is gitignored — **do not commit it**; it holds the family's financial data.

### Changing the users

Edit `USERS` in [`auth.py`](auth.py). Each entry needs an `email`, a display `name`, and the
`heir_id` it maps to (`B1`, `S1`, `B2`, `S2`, `S3`). The heir mapping is what makes the
**Heir statement** page open on that person's own statement. Renaming a user starts them on a
fresh workspace, since the storage filename derives from the address.

## 6. Running it

```bash
pip install -r requirements.txt
```

```bash
cd estate && streamlit run app.py --server.port 8512
```

The opening screen asks which of the five users you are, and shows whether each already has
saved settings.

## 7. Files

| File | Role |
|---|---|
| `config.json` | **The shared baseline.** People, estates and heir classes, properties, rent units, income/expense streams, lifetime acts, gold, liabilities, policy switches. Nothing is hard-coded in the app. |
| `faraid.py` | The Hanafi share calculator — fixed shares, residuary 2:1, `'awl`, `radd`. Raises rather than guessing on unsupported heir classes. |
| `engine.py` | Valuation, ownership windows, the ledger, allocation, settlement, and the scope register. |
| `auth.py` | The five fixed users, the picker screen, and the heir mapping. |
| `auth_google.py` | Parked Google OAuth version of the same API — unused. |
| `.streamlit/secrets.toml.example` | Only needed if you switch back to Google sign-in. |
| `store.py` | Per-user workspace persistence, atomic writes, capped revision history. |
| `app.py` | The Streamlit UI. |
| `user_data/` | Per-user workspaces. **Gitignored — contains financial data.** |

### Extending it

Everything is additive — no code changes needed for new facts:

- **A new event** (a rent change, a new tenant, a repair bill, a one-off receipt) → add a row to
  `streams`. `kind` is `rent` | `notional_rent` | `expense`; `period` is `monthly` | `annual` |
  `oneoff`; a blank `end` means still running. To model a rent *increase*, end the old row and add
  a new one from that date — the ledger handles overlapping windows correctly.
- **A new debt, funeral cost, or wasiyya** → add a row to `estate_liabilities`. It comes off the
  corpus before the shares, in the correct Hanafi order.
- **A change in the heirs** (a death, a new heir class) → edit `estates[].heirs`. The share engine
  recomputes; it supports husband/wife, father, mother, sons, daughters.
- **A property sale or revaluation** → edit `rate_per_sqft` or `lump_value`, or set
  `ownership_share` to carve out a third party.
- **A settled dispute** → flip the relevant policy switch and save. Every number in the app moves
  together and the reasoning printed on each excluded row updates with it.

### Known limits, stated plainly

- The share engine covers spouse + parents + children only. It does **not** model siblings,
  grandparents, grandchildren, `dhawu-l-arham`, or the `mushtaraka`/`akdariyya` cases. It raises
  an error rather than guessing.
- Rents are assumed level from their start date. Real rents escalated; the model will understate
  recent years and overstate early ones. Split the streams by period once you have the actuals.
- The **Jio tower rent before 28 Oct 2025 is an assumption**, not a stated fact — the app flags it
  as `assumed` and it can be switched off in the sidebar. Verify who actually took it.
- Property values are the family's own floor prices, not valuations. For an actual partition you
  need registered valuers, and the ratio between properties matters far more than the absolute
  numbers.
- Indian tax (capital gains on sale, TDS on rent, the treatment of an unpartitioned estate for
  income tax) is entirely outside this model and is not a small consideration on ₹29 cr.
