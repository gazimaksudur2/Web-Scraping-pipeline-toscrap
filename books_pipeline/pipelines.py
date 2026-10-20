import re
import sqlite3


class SQLitePipeline:
    """Store cleaned book records in a SQLite database."""

    def open_spider(self, spider):
        """Create the database table and prepare for this crawl."""
        self.connection = sqlite3.connect("books.db")

        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                price REAL NOT NULL,
                availability INTEGER NOT NULL,
                product_url TEXT NOT NULL,
                image_url TEXT,
                category TEXT NOT NULL
            )
        """)

        # Keep database records aligned with the latest crawl.
        self.connection.execute("DELETE FROM books")
        self.connection.commit()

    def process_item(self, item, spider):
        """Insert one cleaned book record."""
        self.connection.execute(
            """
            INSERT INTO books (
                title, price, availability,
                product_url, image_url, category
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                item["title"],
                item["price"],
                int(item["availability"]),
                item["product_url"],
                item["image_url"],
                item["category"],
            ),
        )

        return item

    def close_spider(self, spider):
        """Commit stored records and close the connection."""
        self.connection.commit()
        self.connection.close()
        

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