import scrapy

class PCautoCarItem(scrapy.Item):
    # 车型基本信息
    car_id = scrapy.Field()          # 车型ID，如 "sg3225"
    brand = scrapy.Field()           # 品牌，如 "大众"
    model = scrapy.Field()           # 车型，如 "朗逸"
    category = scrapy.Field()        # 车辆级别，如 "紧凑型"
    price_range = scrapy.Field()     # 价格区间，如 "8.00-15.19万元"
    year = scrapy.Field()            # 年款
    engine = scrapy.Field()          # 发动机参数
    transmission = scrapy.Field()    # 变速箱类型
    fuel_consumption = scrapy.Field()  # 油耗(L/100km)
    rating = scrapy.Field()          # 综合评分

class PCautoCommentItem(scrapy.Item):
    car_id = scrapy.Field()
    nickname = scrapy.Field()        # 车主昵称
    publish_time = scrapy.Field()    # 发布时间
    purchase_price = scrapy.Field()  # 裸车价格/万元
    rating = scrapy.Field()          # 评分(1-5星)
    advantages = scrapy.Field()      # 优点描述
    disadvantages = scrapy.Field()   # 缺点描述
    comment_text = scrapy.Field()    # 完整评论文本