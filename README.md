# LawCodex — Finland (Suomi / Finland)

The consolidated Finnish legislation in force (*Ajantasainen lainsäädäntö* / *Uppdaterad
lagstiftning*) from the Finlex open-data service, converted to Markdown. The corpus is in both
official languages: Finnish (`fi/`) and Swedish (`sv/`).

Retrieved: **2026-10-11** (the Finlex archive was last updated on 2026-10-10).

## Contents

| Category | Finnish dir | Swedish dir | fi files | sv files |
|---|---|---|---:|---:|
| Constitution (*Suomen perustuslaki* / *Finlands grundlag*, 731/1999) | `fi/perustuslaki/` | `sv/grundlag/` | 1 | 1 |
| Acts (*laki* / *lag*), including the old codes (*kaari* / *balk*) of 1734 | `fi/lait/<year>/` | `sv/lagar/<year>/` | 1,646 | 1,646 |
| Decrees (*asetus* / *förordning*): presidential decrees, government decrees and ministry decrees | `fi/asetukset/<year>/` | `sv/forordningar/<year>/` | 2,966 | 2,959 |
| Decisions (*päätös* / *beslut*): government, ministry and agency decisions in the consolidated set | `fi/paatokset/<year>/` | `sv/beslut/<year>/` | 552 | 546 |
| Other consolidated instruments (announcements, rules of procedure, budgets, lists, official regulations, notices...) | `fi/muut/<year>/` | `sv/ovriga/<year>/` | 112 | 112 |
| **Total** | | | **5,277** | **5,264** |

Each statute has its own file, `<number>-<slug-of-title>.md`. Files go in a directory named after
the year of the Statute Book of Finland (*Suomen säädöskokoelma*, SK/FFS). For example,
`fi/lait/1889/39-001-rikoslaki.md` is the Criminal Code 39/1889 and `sv/lagar/1734/4-000-rattegangsbalk.md`
is the Code of Judicial Procedure. The number is Finlex's own: old statutes sometimes have suffixes
such as `-000` or `-001`. The year directories hold at most a few hundred files each.

### File format

```markdown
---
title: "Suomen perustuslaki"
identifier: "731/1999"                      # number/year in the Statute Book
eli: "http://data.finlex.fi/eli/sd/1999/731/ajantasa"
type: constitution                          # constitution | act | decree | decision | announcement | ...
jurisdiction: fi
language: fi                                # fi | sv
date: 1999-06-11                            # date issued
entry_into_force: 2000-03-01
last_amended: 2018-10-05                    # Finlex consolidation date (dateConsolidated)
status: in_force
administrative_branch: "Oikeusministeriö"   # responsible ministry, when given
source: "https://www.finlex.fi/fi/lainsaadanto/1999/731"
source_data: "https://opendata.finlex.fi/finlex/avoindata/v1/akn/fi/act/statute-consolidated/1999/731/fin@20180817"
retrieved: 2026-10-11
---
```

The body keeps the statute's structure:

- Parts (*osa*), chapters (*luku* / *kapitel*) and sections (*§*) become nested headings. Cross-headings
  (*väliotsikko* / *mellanrubrik*) also become headings, one level above the sections they introduce.
- Each subsection (*momentti* / *moment*) is a paragraph. Numbered and lettered items (*kohta* /
  *punkt*) are nested bullet lists.
- Finlex shows a marker after each amended provision with the amending statute, e.g.
  `(4.11.2011/1112)`. These markers are kept: after the heading for amended sections and chapters,
  and at the end of the text for amended subsections and items.
- Editorial notes from Finlex (*huomautus*, e.g. "added section enters into force at a time set by
  law") become block quotes.
- The end matter is kept as well: preparatory works (*Esityöt* / *Förarbeten*) and the entry-into-force
  provisions of the amending acts (*Muutossäädösten voimaantulo ja soveltaminen* /
  *Ikraftträdelsestadganden*).
- Simple tables become Markdown tables. Tables with merged cells stay as HTML tables. LaTeX formulas
  stay as `$$…$$` math blocks.
- Images (formulas, signs, maps) and PDF annexes are not copied into the repository. They are linked
  to their URLs in the Finlex open-data API (`…/media/<file>`).

## Source

- **Finlex open data** (*Finlex avoin data*), published by the Finnish Ministry of Justice
  (*oikeusministeriö*) and maintained by the Legal Register Centre (*Oikeusrekisterikeskus*).
  - Download page: https://www.finlex.fi/fi/avoin-data/lataa-aineistoja
  - Bulk archive used: https://www.finlex.fi/files/open-data/archives/statute-consolidated.zip
    (≈4.4 GB, updated daily). It contains Akoma Ntoso 3.0 XML for every temporal version, in Finnish
    and Swedish, plus PDFs and media.
  - API (for single documents and media): https://opendata.finlex.fi/finlex/avoindata/v1/ (see the
    OpenAPI description at https://opendata.finlex.fi/swagger-ui/index.html)
- For each statute and language, the converter uses the most recent consolidated version that has
  text (the latest `dateConsolidated`, then the highest version number).
- The consolidated texts are **not authoritative**: the archive marks them
  `FRBRauthoritative=false`. The legally binding text is the version published in the Statute Book
  of Finland (*Suomen säädöskokoelma* / *Finlands författningssamling*).

### Licence

Finlex open data is published under the **Creative Commons Attribution 4.0 (CC BY 4.0)** licence.
Source: Finlex, Ministry of Justice, Finland. Under the Finnish Copyright Act (404/1961, 9 §), acts,
decrees and other official decisions are also not protected by copyright. The Markdown conversion in
this repository is distributed under the same terms (CC BY 4.0, with attribution to Finlex).

## What is NOT covered

- **Statutes with no consolidated text.** Finlex prepares consolidated texts only for a selected set
  of statutes (about 5,300). The archive also has metadata-only entries (`contentAbsent`) for about
  33,600 statutes still marked as in force: 4,591 acts, 13,268 decrees, 13,052 decisions and 2,656
  others. These are mostly old, budget-related or single-purpose instruments, and amending statutes,
  whose only text is the original Statute Book version (`statute.zip` on the Finlex download
  page). They are not included here because there is no consolidated text to convert.
- **Repealed statutes.** The archive also has the last consolidated text of about 3,600 statutes that
  are no longer in force (`isInForce=false`). They are excluded.
- **Missing language versions.** Some statutes are missing their consolidated text in one
  language. 15 are in Finnish only (9 decrees and 6 decisions, e.g. 198/1970) and 2 are in Swedish
  only (decrees 689/2006 and 1024/2010).
- **Not included:**
  - Translations: English translations (*säädöskäännökset*) and Sámi translations.
  - Authority regulations (*viranomaisten määräyskokoelmat*, e.g. Traficom, Finanssivalvonta).
  - Treaties (*valtiosopimukset*).
  - Government proposals.
  - Case law.
- **Åland.** Provincial legislation of the Åland Islands (*landskapslagar*) is not in Finlex and is
  not included.
- **Images and PDF annexes.** They are linked, not embedded (see above).

## Regenerating

```sh
python3 -m pip install -r scripts/requirements.txt
python3 scripts/fetch.py            # downloads the bulk ZIP to ../_raw/fi/ and extracts the latest XML per statute/language
python3 scripts/convert.py          # writes fi/ and sv/ (and deletes .md files of statutes no longer in force)
```

- `fetch.py --refresh` downloads the archive again even if it is already cached.
- Both scripts take an optional raw-data directory argument. `convert.py` also takes the repository
  directory.
- Set `RETRIEVED=YYYY-MM-DD` to fix the `retrieved:` date.
- Raw downloads are never committed.
