# SKU Scraper (IT + PL)

EAN Code Data Scraper for Italy (`IT`) and Poland (`PL`) using free/open-source tools only.

## Features
- Python 3.10+
- Input: single EAN or batch file (one EAN per line)
- Markets:
  - Italy flow: Open Food Facts -> Open Product Data -> Trovaprezzi scrape -> optional Amazon.it placeholder (disabled by default)
  - Poland flow: Open Food Facts -> Allegro scaffold -> Ceneo scrape -> Open Product Data
- Output schema:
  - `ean, product_name, brand, category, price, currency, source, market, scraped_at`
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
- `ENABLE_TROVAPREZZI`, `ENABLE_AMAZON_IT`, `ENABLE_ALLEGRO`, `ENABLE_CENEO`

## Allegro developer registration (free)
1. Register at: https://developer.allegro.pl/
2. Create an app and get `client_id` + `client_secret`
3. Complete OAuth2 device flow to obtain an access token
4. Set env vars before running Polish scraper

## ToS / robots / rate limiting
- Respect robots.txt and Terms of Service for scraped websites.
- Scraping selectors are conservative and may break if page markup changes.
- Randomized polite delays (1–3s) are used for scraping requests.
- Use responsibly and avoid aggressive request rates.

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
