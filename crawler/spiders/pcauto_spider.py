import scrapy
import re
from ..items import PCautoCarItem, PCautoCommentItem


class PcautoSpider(scrapy.Spider):
    name = 'pcauto'
    allowed_domains = ['price.pcauto.com.cn']
    start_urls = [
        'https://price.pcauto.com.cn/top/sales/s1-t1.html',   # 轿车榜
        'https://price.pcauto.com.cn/top/sales/s2-t1.html',   # SUV榜
    ]

    MAX_COMMENT_PAGES = 5

    # ==================== 工具方法 ====================

    @staticmethod
    def _extract_car_id(url):
        match = re.search(r'sg(\d+)', url)
        return match.group(1) if match else None

    @staticmethod
    def _clean(text):
        return text.strip() if text else ''

    @staticmethod
    def _find_next_url(response):
        """统一查找下一页链接（兼容不同写法）"""
        for xpath in ('//a[@class="next"]/@href',
                      '//a[contains(text(),"下一页")]/@href'):
            url = response.xpath(xpath).get()
            if url:
                return response.urljoin(url)
        return None

    # ==================== 主回调 ====================

    def parse(self, response):
        rows = response.xpath('//tr[td[@class="col2 brand"]]')
        self.logger.info(f"共找到 {len(rows)} 个车型行")

        for row in rows:
            car_link = row.xpath('.//td[@class="col2 brand"]/a/@href').get()
            if not car_link:
                continue

            car_id = self._extract_car_id(car_link)
            if not car_id:
                continue

            car_item = PCautoCarItem()
            car_item['car_id'] = car_id
            car_item['model_name'] = self._clean(
                row.xpath('.//td[@class="col2 brand"]/a/text()').get()
            )
            car_item['brand'] = self._clean(
                row.xpath('.//td[@class="col4 relBrand"]/a/text()').get()
            )
            car_item['price'] = self._clean(
                row.xpath('.//td[@class="col3 price"]/text()').get()
            )
            yield car_item

            yield scrapy.Request(
                f'https://price.pcauto.com.cn/comment/sg{car_id}/t1/p1.html',
                callback=self.parse_comments,
                meta={'car_id': car_id, 'page_num': 1}
            )

        # 销量榜翻页
        next_url = self._find_next_url(response)
        if next_url:
            yield scrapy.Request(next_url, callback=self.parse)

    def parse_car_detail(self, response):
        car_id = self._extract_car_id(response.url)
        if not car_id:
            return

        car_item = PCautoCarItem()
        car_item['car_id'] = car_id
        car_item['model_name'] = self._clean(
            response.xpath('//div[@class="position"]/a[last()]/text()').get()
        )
        car_item['brand'] = self._clean(
            response.xpath('//div[@class="position"]/a[last()-2]/text()').get()
        )
        car_item['price'] = self._clean(
            response.xpath('//em[@class="price"]/text()').get()
        )
        yield car_item

        yield scrapy.Request(
            f'https://price.pcauto.com.cn/comment/sg{car_id}/t1/p1.html',
            callback=self.parse_comments,
            meta={'car_id': car_id, 'page_num': 1}
        )

    def parse_comments(self, response):
        car_id = response.meta['car_id']
        current_page = response.meta.get('page_num', 1)

        if current_page > self.MAX_COMMENT_PAGES:
            self.logger.info(f"车型 {car_id} 已达最大页数 {self.MAX_COMMENT_PAGES}，停止翻页")
            return

        comment_nodes = response.xpath('//div[@class="litDy clearfix"]')
        self.logger.info(f"车型 {car_id} 第 {current_page} 页，共 {len(comment_nodes)} 条评论")

        for node in comment_nodes:
            yield self._build_comment_item(node, car_id)

        # 直接构造下一页 URL
        next_page_num = current_page + 1
        if next_page_num <= self.MAX_COMMENT_PAGES:
            next_url = f'https://price.pcauto.com.cn/comment/sg{car_id}/t1/p{next_page_num}.html'
            yield scrapy.Request(
                next_url,
                callback=self.parse_comments,
                meta={'car_id': car_id, 'page_num': next_page_num}
            )

    # ==================== 评论解析 ====================

    def _build_comment_item(self, node, car_id):
        item = PCautoCommentItem()
        item['car_id'] = car_id

        item['nickname'] = self._clean(
            node.xpath('.//div[@class="txBox"]//p/a/text()').get()
        )

        pub_time = node.xpath('.//div[@class="txBox"]//span/a/text()').get()
        item['publish_time'] = pub_time.replace('发表', '').strip() if pub_time else ''

        item['purchase_price'] = self._clean(
            node.xpath('.//div[@class="line"]/em[contains(text(),"裸车价格")]/following-sibling::i/text()').get()
        )

        item['rating'] = self._extract_rating(node)

        item['advantages'] = self._clean(
            node.xpath('.//div[@class="conLit youdian"]/span/text()').get()
        )
        item['disadvantages'] = self._clean(
            node.xpath('.//div[@class="conLit quedian"]/span/text()').get()
        )

        item['full_comment'] = self._build_full_text(node)
        return item

    @staticmethod
    def _extract_rating(node):
        script = node.xpath('.//script[contains(text(),"new Meter")]/text()').get()
        if not script:
            return 0.0
        match = re.search(r"'score'\s*:\s*'?([\d.]+)'?", script)
        return float(match.group(1)) if match else 0.0

    @staticmethod
    def _build_full_text(node):
        parts = []
        for part in node.xpath('.//div[@class="dianPing"]/div[@class="conLit"]'):
            category = part.xpath('b/text()').get(default='').strip()
            text = part.xpath('span/text()').get(default='').strip()
            if category and text:
                parts.append(f"{category}{text}")
            elif text:
                parts.append(text)
        return '\n'.join(parts)