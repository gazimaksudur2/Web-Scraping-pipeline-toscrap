import scrapy


class BooksPipelineItem(scrapy.Item):
    """Store the required fields for a selected book."""

    title = scrapy.Field()
    price = scrapy.Field()
    availability = scrapy.Field()
    product_url = scrapy.Field()
    image_url = scrapy.Field()
    category = scrapy.Field()