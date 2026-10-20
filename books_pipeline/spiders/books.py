import random

import scrapy

from books_pipeline.items import BooksPipelineItem


class BooksSpider(scrapy.Spider):
    name = "books"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["https://books.toscrape.com/"]
    categories_to_select = 7

    def parse(self, response):
        """Discover all categories and randomly select 5–10."""
        links = response.css("ul.nav-list ul li a")

        categories = [
            {
                "name": link.xpath(
                    "normalize-space(string(.))"
                ).get(),
                "url": response.urljoin(link.attrib["href"]),
            }
            for link in links
        ]

        if not categories:
            self.logger.error("No categories were discovered.")
            return

        count = min(self.categories_to_select, len(categories))
        selected = random.sample(categories, count)

        self.category_book_urls = {
            category["url"]: {
                "name": category["name"],
                "urls": [],
            }
            for category in selected
        }

        self.pending_categories = set(
            self.category_book_urls.keys()
        )

        self.logger.info(
            "Discovered %d categories; randomly selected %d.",
            len(categories),
            count,
        )

        for category in selected:
            yield response.follow(
                category["url"],
                callback=self.parse_category,
                meta={"category_url": category["url"]},
            )

    def parse_category(self, response):
        """Collect all available books and sample up to five."""
        category_url = response.meta["category_url"]
        category = self.category_book_urls[category_url]

        links = response.css(
            "article.product_pod h3 a::attr(href)"
        ).getall()

        category["urls"].extend(
            response.urljoin(url) for url in links
        )

        next_page = response.css(
            "li.next a::attr(href)"
        ).get()

        if next_page:
            yield response.follow(
                next_page,
                callback=self.parse_category,
                meta={"category_url": category_url},
            )
            return

        self.pending_categories.discard(category_url)

        if self.pending_categories:
            return

        for category in self.category_book_urls.values():
            available = category["urls"]
            sample_size = min(5, len(available))

            self.logger.info(
                "Category '%s': %d books available; selecting %d.",
                category["name"],
                len(available),
                sample_size,
            )

            selected_books = random.sample(
                available, sample_size
            )

            for url in selected_books:
                yield scrapy.Request(
                    url,
                    callback=self.parse_book,
                    meta={"category": category["name"]},
                )

    def parse_book(self, response):
        """Extract the required fields from a selected book page."""
        item = BooksPipelineItem()

        item["title"] = response.css(
            "div.product_main h1::text"
        ).get()

        item["price"] = response.css(
            "div.product_main p.price_color::text"
        ).get()

        item["availability"] = response.css(
            "div.product_main p.instock.availability"
        ).xpath("normalize-space(string(.))").get()

        item["product_url"] = response.url

        image_path = response.css(
            "div.item.active img::attr(src)"
        ).get()

        item["image_url"] = (
            response.urljoin(image_path)
            if image_path
            else None
        )

        item["category"] = response.meta["category"]

        yield item
