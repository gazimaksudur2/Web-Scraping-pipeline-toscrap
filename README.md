# Enterprise Web Scraping Pipeline — Books Data Engineering System

A modular Scrapy application that discovers book categories dynamically from [Books to Scrape](https://books.toscrape.com/), selects a random sample of categories and books, cleans the extracted data, exports it to JSON/CSV/XML, stores it in SQLite, and supports deployment through Scrapyd and Docker.

## Contents

- [Project overview](#project-overview)
- [Features](#features)
- [Technology stack](#technology-stack)
- [Data fields](#data-fields)
- [Architecture](#architecture)
- [Project structure](#project-structure)
- [Environment setup](#environment-setup)
- [Run locally](#run-locally)
- [Output formats](#output-formats)
- [Database configuration](#database-configuration)
- [Docker setup](#docker-setup)
- [Scrapyd deployment and API](#scrapyd-deployment-and-api)
- [Validation](#validation)
- [Design decisions](#design-decisions)
- [Known limitations](#known-limitations)

## Project overview

The project demonstrates an end-to-end web-scraping workflow using Scrapy and Python. It starts from the website homepage, discovers category names and URLs dynamically, randomly selects between five and ten categories from all discovered categories, follows pagination for each selected category, and selects up to five distinct books from each selected category. If a category contains fewer than five books, every available book in that category is selected.

The spider extracts book details and passes every item through Scrapy Item Pipelines for normalization and SQLite insertion. Scrapy Feed Exports produce JSON, CSV, and XML files.

**Target website:** <https://books.toscrape.com/index.html>

## Features

- Dynamic category discovery; category names and URLs are not hardcoded.
- Category pagination handled by following each page's `next` link.
- Random selection of 5–10 categories from all dynamically discovered categories, without filtering by category size.
- Random selection of up to five distinct books per selected category; categories with fewer than five books contribute all available books.
- Extraction of title, numeric price, availability Boolean, product URL, image URL, and category.
- Item cleaning and normalization through a Scrapy pipeline.
- SQLite storage through a second Scrapy Item Pipeline.
- Scrapy Feed Exports configured in `settings.py` for JSON, CSV, and XML.
- Docker image and Docker Compose configuration for Scrapyd.
- Scrapyd deployment and spider execution through its HTTP API.
- Logging for category discovery, selection, and crawling.

## Technology stack

- Python 3.12 (the project was tested with Python 3.12.3)
- Scrapy 2.19.0
- Scrapyd 1.6.0
- scrapyd-client
- SQLite (`sqlite3`, included with Python)
- Docker and Docker Compose

Installed package versions can be reviewed in `requirements.txt`.

## Data fields

Each exported book record contains these six fields:

| Field | Type after processing | Description |
|---|---|---|
| `title` | String | Book title |
| `price` | Float | Price with currency symbols removed |
| `availability` | Boolean | `true` when the availability text begins with “In stock”; otherwise `false` |
| `product_url` | String | Absolute URL of the book detail page |
| `image_url` | String | Absolute URL of the book cover image |
| `category` | String | Dynamically discovered category name |

SQLite stores availability as an integer (`1` or `0`) because SQLite has no separate Boolean storage class.

## Architecture

```text
Books to Scrape homepage
          |
          v
BooksSpider: discover category links dynamically
          |
          v
Randomly select 5–10 categories from all discovered categories
          |
          v
Visit selected category listings and follow pagination
          |
          v
Randomly select min(5, available books) per selected category
          |
          v
Fetch book detail pages and create BooksPipelineItem
          |
          v
BooksPipeline: normalize text, price, availability
          |
          +--------------------+--------------------+
          |                    |                    |
          v                    v                    v
      JSON feed            CSV feed             XML feed
          |
          +--> SQLitePipeline --> books.db

Deployment path: setup.py -> scrapyd-deploy -> Scrapyd API
Container path: Dockerfile + compose.yaml -> Scrapyd service
```

## Project structure

```text
enterprise-web-scraping-pipeline/
├── books_pipeline/
│   ├── __init__.py
│   ├── items.py             # Scrapy item definition
│   ├── middlewares.py       # Generated Scrapy middleware module
│   ├── pipelines.py         # Cleaning and SQLite pipelines
│   ├── settings.py          # Feed exports, pipelines, Scrapy settings
│   └── spiders/
│       ├── __init__.py
│       └── books.py         # Category, pagination, and book crawling
├── .dockerignore
├── .gitignore
├── compose.yaml
├── Dockerfile
├── requirements.txt
├── scrapy.cfg
├── scrapyd.conf
├── setup.py
├── books.json               # Generated JSON export (after a crawl)
├── books.csv                # Generated CSV export (after a crawl)
├── books.xml                # Generated XML export (after a crawl)
└── books.db                 # SQLite database (created/updated by a crawl)
```

Generated exports and the SQLite database are runtime outputs, not source files. The repository's `.gitignore` excludes database files and should also exclude generated exports if you do not want to commit crawl results.

## Environment setup

### Prerequisites

- Linux, macOS, or another environment that supports Python and Scrapy
- Python 3.12 recommended for the tested setup
- pip
- Git (optional but recommended)
- Docker Engine and Docker Compose for container deployment

### Create and activate a virtual environment

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Check the installation:

```bash
python --version
scrapy version
scrapyd-deploy --help
```

If starting from a fresh checkout and using the current Compose bind mount for SQLite, create the database file before starting the container:

```bash
touch books.db
```

## Run locally

Run the spider from the project root with the virtual environment active:

```bash
scrapy list
scrapy crawl books
```

Scrapy discovers categories from the homepage on each run and randomly selects between five and ten of them without checking category size first. It follows pagination for each selected category, then selects `min(5, available books)` distinct books. A category with one to four books contributes all of its books; an empty category contributes no book records.

To write the feed exports explicitly, use:

```bash
scrapy crawl books
```

The `FEEDS` configuration in `books_pipeline/settings.py` writes `books.json`, `books.csv`, and `books.xml` in the current working directory. A new crawl overwrites the prior feed files because the feed configuration enables overwrite.

## Output formats

The following feed exports are configured in `books_pipeline/settings.py`:

- `books.json` — JSON array of book records
- `books.csv` — CSV table with one column per item field
- `books.xml` — XML records generated by Scrapy's XML feed exporter

Check that the files exist after a local crawl:

```bash
ls -lh books.json books.csv books.xml
```

Check record counts and category sampling:

```bash
python - <<'PY'
import collections
import json

with open("books.json", encoding="utf-8") as file:
    records = json.load(file)

print("Total records:", len(records))
print("Records per category:", dict(collections.Counter(row["category"] for row in records)))
PY
```

The total number of records varies between runs because both the selected categories and their available book counts vary. Categories with at least five books contribute five records; categories with fewer than five books contribute their available number. Therefore, the total is not necessarily a multiple of five.

## Database configuration

The SQLite database file is `books.db`, created in the application's working directory. The database table is named `books` and contains:

- `id` — auto-incrementing primary key
- `title` — text
- `price` — real number
- `availability` — integer (`1` or `0`)
- `product_url` — text
- `image_url` — text
- `category` — text

Database inserts are handled by `SQLitePipeline` in `books_pipeline/pipelines.py`, after the cleaning pipeline has normalized the item.

Inspect the database:

```bash
python - <<'PY'
import sqlite3

connection = sqlite3.connect("books.db")
print("Records:", connection.execute("SELECT COUNT(*) FROM books").fetchone()[0])
print("Records per category:")
for row in connection.execute(
    "SELECT category, COUNT(*) FROM books GROUP BY category ORDER BY category"
):
    print(row)
connection.close()
PY
```

**Current behavior:** `SQLitePipeline.open_spider()` deletes existing rows before each crawl, so `books.db` represents the latest crawl rather than a historical archive. Avoid running concurrent spider jobs against the same database file.

## Docker setup

The project includes a `Dockerfile`, `.dockerignore`, `scrapyd.conf`, and `compose.yaml`. The container runs Scrapyd on port `6800`; Compose publishes the API on `127.0.0.1:6800` on the host.

Create `books.db` if it does not already exist, then build and start the service:

```bash
touch books.db
docker compose config
docker compose build
docker compose up -d
docker compose ps
```

View the Scrapyd interface at <http://127.0.0.1:6800/>.

Useful container commands:

```bash
docker compose logs -f scrapyd
docker compose ps
docker compose down
```

`docker compose down` stops and removes the service container and network; the named `scrapyd-data` volume is retained unless explicitly removed.

The host `books.db` file is mounted at `/app/books.db` in the container. The Scrapyd deployment's feed files are currently written in the container's working directory; they are not mounted as host output files by the current Compose configuration. For a deployed crawl, inspect the job log or copy the files from the container if needed, for example:

```bash
docker cp books-scrapyd:/app/books.json ./books.json
docker cp books-scrapyd:/app/books.csv ./books.csv
docker cp books-scrapyd:/app/books.xml ./books.xml
```

## Scrapyd deployment and API

### Deploy the project

The project includes a `setup.py` entry point for Scrapy settings and a `local` target in `scrapy.cfg`:

```ini
[deploy:local]
url = http://127.0.0.1:6800/
project = books_pipeline
```

Start Scrapyd using Docker first, then deploy from the host terminal with the project virtual environment active:

```bash
scrapyd-deploy local
```

A successful response should report `"status": "ok"`. Verify that Scrapyd knows the project and spider:

```bash
curl -s http://127.0.0.1:6800/listprojects.json
curl -s "http://127.0.0.1:6800/listspiders.json?project=books_pipeline"
```

### Schedule a crawl through the API

```bash
curl -s -X POST \
  http://127.0.0.1:6800/schedule.json \
  -d project=books_pipeline \
  -d spider=books
```

The response should contain `"status": "ok"` and a job ID. Check the job state with:

```bash
curl -s "http://127.0.0.1:6800/listjobs.json?project=books_pipeline"
```

When the job is finished, its log URL is included in the response. Logs can also be accessed through the Scrapyd web interface at <http://127.0.0.1:6800/jobs> and <http://127.0.0.1:6800/logs/>.

## Validation

The following checks have been performed during development:

- The homepage returned HTTP 200 and the category selector discovered 50 category links dynamically.
- Category pagination was tested using a multi-page category.
- The earlier implementation was tested with category eligibility filtering and completed a crawl. The sampling policy is being changed so categories are selected randomly from all discovered categories and contribute up to five available books. Re-run local validation after applying that code change.
- A local crawl produced JSON, CSV, and XML exports with matching record counts and all six required fields.
- SQLite storage was checked for matching record counts and category counts for a tested crawl; repeat this check after applying the revised sampling policy.
- Docker and Docker Compose configuration were validated, and the Scrapyd service responded on port 6800.
- The project was deployed to Scrapyd; the API listed the `books` spider and successfully scheduled a crawl.
- A Scrapyd job finished with 35 scraped items, and the job log confirmed that all three feed exporters stored 35 items. The container's SQLite database was also checked and contained 35 records with the expected columns.

Re-run the validation commands after code or configuration changes; the random selection means each crawl can produce a different number of records.

## Design decisions

- **Dynamic discovery:** Category names and links are extracted from the homepage rather than maintained in code.
- **Random category sampling:** Between five and ten categories are sampled randomly from all categories discovered on the homepage; category size does not affect eligibility for selection.
- **Pagination-aware collection:** Each selected category listing is followed until no next-page link remains, so book sampling is not restricted to the first page.
- **Availability-aware book sampling:** Each selected category contributes up to five distinct books. If fewer than five are available, all available books are selected.
- **Separation of responsibilities:** The spider handles navigation and extraction; the item class defines the record structure; pipelines clean values and persist records; settings define feeds and pipeline order.
- **Parameterized SQL:** SQLite inserts use placeholders rather than string-built SQL.
- **Containerized deployment:** Docker packages the runtime, while Scrapyd manages deployed spider versions and API-triggered jobs.

## Known limitations

- Random selection means each crawl can return a different total number of records. The number depends on the 5–10 randomly selected categories and how many books each selected category contains.
- Only the randomly selected categories are crawled for their full listings and pagination; this avoids scanning every category on each run.
- SQLite is configured to replace the previous crawl's rows. It is intended for this assignment's latest-run dataset, not concurrent jobs or historical storage.
- The current Compose configuration persists `books.db` on the host, but feed exports generated by a Scrapyd job are written inside the container unless copied out. A dedicated host-mounted output directory would be a useful improvement.
- The scraper depends on the target website's HTML structure and CSS selectors; a website redesign may require selector updates.
- The target site may return a `robots.txt` 404. The observed crawl still completed, but the site response should be monitored if its behavior changes.
- The project is an educational assignment implementation; production use would benefit from stronger retry/alerting policies, schema-level validation, deduplication, configuration through environment variables, and automated tests.

## License and responsible use

This project was built for educational web-scraping and data-engineering practice against Books to Scrape. Respect the target website's terms, robots policy, and request-rate expectations when adapting the spider to other websites.
