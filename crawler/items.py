import scrapy

class PCautoCarItem(scrapy.Item):
    car_id = scrapy.Field()
    model_name = scrapy.Field()
    brand = scrapy.Field()
    price = scrapy.Field()

class PCautoCommentItem(scrapy.Item):
    car_id = scrapy.Field()
    nickname = scrapy.Field()
    publish_time = scrapy.Field()
    purchase_price = scrapy.Field()
    rating = scrapy.Field()
    advantages = scrapy.Field()
    disadvantages = scrapy.Field()
    full_comment = scrapy.Field()