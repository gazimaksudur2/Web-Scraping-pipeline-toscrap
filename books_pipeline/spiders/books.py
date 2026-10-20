import random

import scrapy

from books_pipeline.items import BooksPipelineItem


class BooksSpider(scrapy.Spider):
    name = "books"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["https://books.toscrape.com/"]

    def parse(self, response):
        """Discover categories and inspect their book listings."""
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

        self.category_book_urls = {
            category["url"]: {
                "name": category["name"],
                "urls": [],
            }
            for category in categories
        }

        self.pending_categories = set(
            self.category_book_urls.keys()
        )

        self.logger.info(
            "Discovered %d categories. Inspecting all listings.",
            len(categories),
        )

        for category in categories:
            yield response.follow(
                category["url"],
                callback=self.parse_category,
                meta={"category_url": category["url"]},
            )

    def parse_category(self, response):
        """Collect book URLs across every page of a category."""
        category_url = response.meta["category_url"]
        category = self.category_book_urls[category_url]

        book_links = response.css(
            "article.product_pod h3 a::attr(href)"
        ).getall()

        category["urls"].extend(
            response.urljoin(url) for url in book_links
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

        eligible = [
            category
            for category in self.category_book_urls.values()
            if len(category["urls"]) >= 5
        ]

        if len(eligible) < 5:
            self.logger.error(
                "Only %d eligible categories found.",
                len(eligible),
            )
            return

        count = random.randint(5, min(10, len(eligible)))
        selected = random.sample(eligible, count)

        self.logger.info(
            "Inspected %d categories; %d have at least 5 books. "
            "Selected %d eligible categories.",
            len(self.category_book_urls),
            len(eligible),
            count,
        )

        for category in selected:
            selected_urls = random.sample(category["urls"], 5)

            self.logger.info(
                "Category '%s': collected %d books; selected 5.",
                category["name"],
                len(category["urls"]),
            )

            for url in selected_urls:
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
