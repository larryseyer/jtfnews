# JTF News - Terms of Service Compliance Documentation

**Last Updated:** February 2026
**Version:** 1.0

---

## Our Compliance Approach

JTF News operates with a good-faith effort to comply with all applicable terms of service and copyright law. Our approach prioritizes:

1. **Headlines Only** - We extract only headlines (facts), not full article content
2. **RSS Where Provided** - We use official RSS feeds where publishers make them available, indicating intent for machine consumption
3. **robots.txt Respected** - All scraping respects robots.txt directives
4. **Rate-Limited Access** - 30-minute intervals, 1-second delays between requests
5. **Full Attribution** - Every story includes full source attribution and ownership disclosure
6. **Non-Commercial Use** - No ads, no tracking, nonprofit model
7. **Transformative Use** - AI rewrites to strip editorialization, creating transformative work

---

## Legal Rationale

### Fair Use Factors (17 U.S.C. § 107)

| Factor | JTF News Position |
|--------|-------------------|
| **Purpose and character** | Transformative (AI rewrites); non-commercial; educational |
| **Nature of copyrighted work** | News headlines (factual, low protection) |
| **Amount used** | Headlines only (minimal portion) |
| **Market effect** | Links to sources; encourages traffic; no substitute for full articles |

### Key Precedents

- **AP v. Meltwater (2013)** - Commercial aggregator lost fair use claim. JTF differs: non-commercial, transformative rewriting, minimal extraction
- **Kelly v. Arriba Soft (2003)** - Thumbnails for search = transformative use. JTF extracts headlines for verification, also transformative
- **Perfect 10 v. Amazon (2007)** - Search indexing serves different purpose than source. JTF serves verification purpose

---

## Retained Sources (17 Total)

### Government / Primary Sources (8)

These sources are public records. Government information is generally not copyrightable under U.S. law (17 U.S.C. § 105). Similar public-domain principles apply to other governments' official publications.

| ID | Name | Access Method | Risk Level | Rationale |
|----|------|---------------|------------|-----------|
| `whitehouse` | White House | CSS scrape | None | US Government public records |
| `congress` | Congress.gov | RSS | None | US Government public records; RSS provided |
| `federal_register` | Federal Register | RSS API | None | Designed for machine access; public records |
| `scotus` | Supreme Court | CSS scrape | None | US Government public records |
| `state_dept` | US State Department | RSS | None | US Government public records; RSS provided |
| `pentagon` | US Dept of Defense | RSS | None | US Government public records; RSS provided |
| `uk_parliament` | UK Parliament | Google News RSS | Low | Government body; public proceedings |
| `eu_commission` | European Commission | RSS | None | EU public institution; RSS provided |

### Public Broadcasters (7)

Public broadcasters are funded by public money and generally provide RSS feeds intended for aggregation. Their mission is public service, not commercial exclusivity.

| ID | Name | Access Method | Risk Level | Rationale |
|----|------|---------------|------------|-----------|
| `bbc` | BBC News | Native RSS | Low | UK public broadcaster; RSS provided for aggregation |
| `npr` | NPR | Native RSS | Low | US public nonprofit; RSS provided |
| `france24` | France 24 | Native RSS | Low | French state-funded; RSS provided |
| `dw` | Deutsche Welle | Native RSS | Low | German state-funded; RSS provided |
| `cbc` | CBC News | Native RSS | Low | Canadian public broadcaster; RSS provided |
| `abc_au` | ABC News Australia | Native RSS | Low | Australian public broadcaster; RSS provided |
| `pbs` | PBS NewsHour | Native RSS | Low | US public nonprofit; RSS provided |

### Trusts / Nonprofits (2)

These organizations are owned by charitable trusts with public-interest missions. They provide RSS feeds for aggregation.

| ID | Name | Access Method | Risk Level | Rationale |
|----|------|---------------|------------|-----------|
| `guardian` | The Guardian | Native RSS | Low | Scott Trust ownership; RSS provided; open journalism ethos |
| `irish` | Irish Times | Native RSS | Low | Irish Times Trust ownership; RSS provided |

---

## Removed Sources (13 Total)

The following sources were removed due to ToS concerns or legal risk:

### Wire Services (4) - HIGH RISK

| ID | Reason for Removal |
|----|-------------------|
| `ap` | **AP was the plaintiff in AP v. Meltwater (2013)**, the landmark case ruling news aggregation was NOT fair use. Highest litigation risk. |
| `reuters` | Wire service with licensing model; blocks direct access; Thomson Reuters ownership |
| `afp` | Wire service; accessed via Google News RSS workaround (violates Google ToS) |
| `efe` | Wire service; accessed via Google News RSS workaround |

### Commercial Media (9) - MEDIUM TO HIGH RISK

| ID | Reason for Removal |
|----|-------------------|
| `aljazeera` | Commercial (Qatar state); ToS unreviewed |
| `sky` | Commercial (Comcast); ToS unreviewed |
| `euronews` | Commercial (Alpac Capital); ToS unreviewed |
| `toi` | Commercial (Jain family); ToS unreviewed |
| `globe` | Commercial (Thomson family); ToS unreviewed |
| `straits` | Commercial (Singapore Press Holdings); ToS unreviewed |
| `hindustan` | Commercial (HT Media); ToS unreviewed |
| `independent` | HTML scraping only (no RSS provided); ToS unreviewed; highest technical risk |
| `cspan` | YouTube RSS (third-party platform ToS complexity); nonprofit but reliant on YouTube API |

---

## Takedown Response Protocol

### Policy

Any source requesting removal will be removed within 24 hours. No arguments. No delays.

### Process

1. Receive takedown request via email, letter, or other communication
2. Log request immediately in `data/takedown_log.json`
3. Remove source from `config.json` within 24 hours
4. Send acknowledgment to requester
5. Document in this file under "Takedown History" section

### Contact

For takedown requests or questions:
- Email: [to be configured]
- GitHub Issues: https://github.com/JTFNews/jtfnews/issues

### Takedown History

| Date | Source | Requester | Action |
|------|--------|-----------|--------|
| (none) | - | - | - |

---

## Future Source Addition Process

Before adding any new source:

1. **Verify RSS is officially provided** - Not scraped from HTML
2. **Review ToS** for explicit prohibitions on:
   - Automated access
   - Aggregation
   - Republication
   - Commercial use (even if we're non-commercial, some ToS are broad)
3. **Confirm ownership structure** - Avoid sources with pending litigation against aggregators
4. **Document in this file** with:
   - ToS review date
   - Key terms reviewed
   - Our compliance status
5. **Wait for quarterly review cycle** before activation

---

## Quarterly Audit Schedule

| Quarter | Audit Due | Status |
|---------|-----------|--------|
| Q1 2026 | March 31, 2026 | Pending |
| Q2 2026 | June 30, 2026 | - |
| Q3 2026 | September 30, 2026 | - |
| Q4 2026 | December 31, 2026 | - |

Audits verify:
- All sources still provide RSS feeds
- No ToS changes prohibiting our use
- robots.txt still permits access
- Ownership structures unchanged

---

## Disclaimer

This document represents JTF News's good-faith effort to comply with terms of service and applicable law. It is not legal advice. JTF News has not obtained legal review of this compliance approach. Users and operators should consult their own legal counsel for specific questions.

**Document maintained at:** `docs/ToS_Compliance.md`
**Git tracked:** Yes
