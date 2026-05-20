import scrapy
import json
import re
from urllib.parse import urljoin
from ..items import PCautoCarItem, PCautoCommentItem

class PcautoSpider(scrapy.Spider):
    name = "pcauto"
    allowed_domains = ["price.pcauto.com.cn", "pcauto.com.cn"]
    # 起始爬取点：可以从销量榜单或车型列表开始
    start_urls = [
        "https://price.pcauto.com.cn/top/sales/s1-t1.html",  # 全国销量榜
        "https://price.pcauto.com.cn/car/list/s2-t1.html",  # 按品牌分组
    ]

    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS': 2,
        'ROBOTSTXT_OBEY': False,
        'DEFAULT_REQUEST_HEADERS': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
    }

    def parse(self, response):
        # 1. 解析销量榜页，提取所有车型详情页链接
        if "top/sales" in response.url:
            car_urls = response.xpath('//a[contains(@href, "/price/sg")]/@href').extract()
            for url in car_urls:
                full_url = urljoin("https://price.pcauto.com.cn", url)
                yield scrapy.Request(full_url, callback=self.parse_car_detail)

        # 2. 解析车型详情页（价格页）-> 提取基本信息，再跳转到评论页
        elif "/price/sg" in response.url:
            car_id = re.search(r'sg(\d+)', response.url).group(1)
            car_item = PCautoCarItem()
            car_item['car_id'] = car_id
            car_item['model'] = response.xpath('//h1/text()').get(default='').strip()
            car_item['brand'] = response.xpath('//div[@class="breadcrumb"]/a[2]/text()').get(default='')
            price_text = response.xpath('//div[@class="price-range"]/text()').get(default='')
            car_item['price_range'] = re.search(r'[\d\.-]+万元', price_text).group() if price_text else ''
            car_item['year'] = response.xpath('//span[@class="year"]/text()').get()
            car_item['engine'] = response.xpath('//td[contains(text(),"发动机")]/following-sibling::td[1]/text()').get()
            car_item['transmission'] = response.xpath('//td[contains(text(),"变速箱")]/following-sibling::td[1]/text()').get()
            car_item['fuel_consumption'] = response.xpath('//td[contains(text(),"油耗")]/following-sibling::td[1]/text()').get()
            car_item['category'] = response.xpath('//td[contains(text(),"级别")]/following-sibling::td[1]/text()').get()
            yield car_item  # 保存车型数据

            # 跳转到评论页
            comment_url = f"https://price.pcauto.com.cn/comment/sg{car_id}/"
            yield scrapy.Request(comment_url, callback=self.parse_comments,
                                 meta={'car_id': car_id})

        # 3. 翻页：处理评论页的分页
        elif "/comment/sg" in response.url:
            car_id = response.meta['car_id']
            # 解析当前页的所有评论
            comment_list = response.xpath('//div[@class="comment-list"]/div')
            for comment_div in comment_list:
                comment_item = PCautoCommentItem()
                comment_item['car_id'] = car_id
                comment_item['nickname'] = comment_div.xpath('.//span[@class="name"]/text()').get()
                comment_item['publish_time'] = comment_div.xpath('.//span[@class="date"]/text()').get()
                price = comment_div.xpath('.//span[@class="price"]/text()').get()
                comment_item['purchase_price'] = re.search(r'[\d\.]+', price).group() if price else ''
                rating_text = comment_div.xpath('.//span[@class="star"]/@class').get()
                comment_item['rating'] = rating_text.count('full') if rating_text else 0
                comment_item['advantages'] = comment_div.xpath('.//div[@class="advantage"]/text()').get()
                comment_item['disadvantages'] = comment_div.xpath('.//div[@class="disadvantage"]/text()').get()
                comment_item['comment_text'] = comment_div.xpath('.//div[@class="content"]/text()').get()
                yield comment_item

            # 提取下一页
            next_page = response.xpath('//a[@class="next"]/@href').get()
            if next_page:
                next_url = urljoin(response.url, next_page)
                yield scrapy.Request(next_url, callback=self.parse_comments,
                                     meta={'car_id': car_id})

    def parse_comments(self, response):
        # 兼容旧版的回调
        car_id = response.meta['car_id']
        comments = response.xpath('//div[@class="comment-item"]')
        for comment in comments:
            yield {
                'car_id': car_id,
                'nickname': comment.xpath('.//div[@class="user"]/text()').get(),
                'comment': comment.xpath('.//div[@class="comment-text"]/text()').get(),
                'rating': comment.xpath('.//div[@class="stars"]/@data-score').get(),
                'date': comment.xpath('.//div[@class="date"]/text()').get(),
            }
        # 翻页逻辑
        next_link = response.xpath('//a[contains(text(),"下一页")]/@href').get()
        if next_link:
            yield scrapy.Request(urljoin(response.url, next_link),
                                 callback=self.parse_comments,
                                 meta={'car_id': car_id})