# SKU Scraper (IT + PL)

EAN Code Data Scraper for Italy (`IT`) and Poland (`PL`) using free/open-source tools only.

## Features
- Python 3.10+
- Input: single EAN or batch file (one EAN per line)
- Markets:
  - Italy flow:
    - EAN mode: Open Food Facts -> Open Product Data -> Trovaprezzi scrape -> optional Amazon.it placeholder
    - Keyword mode: Amazon.it search + eBay.it search (merge or fallback strategy)
  - Poland flow: Open Food Facts -> Allegro scaffold -> Ceneo scrape -> Open Product Data
- Output schema:
  - Base: `ean, product_name, brand, category, price, currency, source, market, scraped_at`
  - Keyword mode extras: `asin, url, image, rating, seller`
- Storage:
  - SQLite (`data/results.db` by default)
  - optional CSV export

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.env .env
```

## CLI usage
Single EAN (Italy):
```bash
python italy/scraper_it.py --ean 8000500310427
```

Batch mode (Italy):
```bash
python italy/scraper_it.py --batch /absolute/path/to/eans.txt --csv data/results_it.csv
```

Keyword mode (Italy, merge Amazon + eBay):
```bash
python italy/scraper_it.py --query "crema anticellulite" --sources amazon_it,ebay_it --strategy merge --sort best_match --limit 10
```

Manual Amazon link mode (Italy, provided search URL):
```bash
python italy/scraper_it.py --search-url "https://www.amazon.it/s?k=crema+anticellulite" --sources amazon_it --strategy fallback
```
`--search-url` is consumed by `amazon_it`; if you also include `ebay_it` with no `--query`, eBay will return no candidates.

Single EAN (Poland):
```bash
python poland/scraper_pl.py --ean 5901234123457
```

Batch mode (Poland):
```bash
python poland/scraper_pl.py --batch /absolute/path/to/eans.txt --csv data/results_pl.csv
```

Allegro setup help:
```bash
python poland/scraper_pl.py --ean 5901234123457 --allegro-help
```

## Config
Environment variables (see `config.example.env`):
- `ALLEGRO_CLIENT_ID`, `ALLEGRO_CLIENT_SECRET`, `ALLEGRO_ACCESS_TOKEN`
- `ENABLE_TROVAPREZZI`, `ENABLE_AMAZON_IT`, `ENABLE_EBAY_IT`, `ENABLE_ALLEGRO`, `ENABLE_CENEO`
- Per-source controls:
  - `AMAZON_IT_TIMEOUT`, `AMAZON_IT_RETRIES`, `AMAZON_IT_BACKOFF_SECONDS`, `AMAZON_IT_RATE_LIMIT_SECONDS`, `AMAZON_IT_PROXY`
  - `EBAY_IT_TIMEOUT`, `EBAY_IT_RETRIES`, `EBAY_IT_BACKOFF_SECONDS`, `EBAY_IT_RATE_LIMIT_SECONDS`, `EBAY_IT_PROXY`

## Allegro developer registration (free)
1. Register at: https://developer.allegro.pl/
2. Create an app and get `client_id` + `client_secret`
3. Complete OAuth2 device flow to obtain an access token
4. Set env vars before running Polish scraper

## ToS / robots / rate limiting
- Respect robots.txt and Terms of Service for scraped websites.
- Scraping selectors are conservative and may break if page markup changes.
- Per-source retry/backoff and rate-limits are configurable via env vars.
- Use responsibly and avoid aggressive request rates.

## Example SKU keyword runs (Amazon.it links)
- SKU001 `Crema Anticellulite Intensiva 250ml`:
  `python italy/scraper_it.py --search-url "https://www.amazon.it/s?k=crema+anticellulite" --sources amazon_it`
- SKU002 `Gel Drenante Rimodellante Corpo 200ml`:
  `python italy/scraper_it.py --search-url "https://www.amazon.it/s?k=gel+drenante+corpo" --sources amazon_it`
- SKU003 `Olio Corpo Anticellulite Naturale 100ml`:
  `python italy/scraper_it.py --search-url "https://www.amazon.it/s?k=olio+anticellulite" --sources amazon_it`
- SKU004 `Crema Rassodante Corpo Effetto Lift 200ml`:
  `python italy/scraper_it.py --search-url "https://www.amazon.it/s?k=crema+rassodante+corpo" --sources amazon_it`
- SKU005 `Trattamento Snellente Notturno 150ml`:
  `python italy/scraper_it.py --search-url "https://www.amazon.it/s?k=crema+snellente+notte" --sources amazon_it`
- SKU006 `Scrub Corpo Sale Marino 300ml`:
  `python italy/scraper_it.py --search-url "https://www.amazon.it/s?k=scrub+sale+marino+corpo" --sources amazon_it`
- SKU007 `Scrub Corpo Zucchero 250ml`:
  `python italy/scraper_it.py --search-url "https://www.amazon.it/s?k=scrub+zucchero+corpo" --sources amazon_it`
- SKU008 `Lozione Corpo Idratante 400ml`:
  `python italy/scraper_it.py --search-url "https://www.amazon.it/s?k=lozione+corpo" --sources amazon_it`
- SKU009 `Crema Corpo AHA Esfoliante 200ml`:
  `python italy/scraper_it.py --search-url "https://www.amazon.it/s?k=crema+corpo+aha" --sources amazon_it`
- SKU010 `Gel Gambe Leggere 200ml`:
  `python italy/scraper_it.py --search-url "https://www.amazon.it/s?k=gel+gambe+leggere" --sources amazon_it`

## Local output
- SQLite DB: `data/results.db`
- Optional CSV: any path passed with `--csv`
- `data/*.db` is gitignored and should not be committed.

## Tests
```bash
pytest
```

## GitHub Pages
A static page is included in `docs/index.html`.
Use repository settings -> Pages -> deploy from branch `main` and folder `/docs`.
