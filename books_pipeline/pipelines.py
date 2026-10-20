import re


class BooksPipeline:
    """Clean and normalize scraped book data."""

    def process_item(self, item, spider):
        """Normalize text, price, and availability fields."""

        for field in (
            "title",
            "product_url",
            "image_url",
            "category",
        ):
            if item.get(field):
                item[field] = item[field].strip()

        price = re.sub(r"[^\d.]", "", item["price"])
        item["price"] = float(price)

        availability = item["availability"].strip().lower()
        item["availability"] = availability.startswith("in stock")

        return item