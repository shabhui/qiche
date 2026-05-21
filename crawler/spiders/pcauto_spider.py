import scrapy
import re
from urllib.parse import urljoin
from ..items import PCautoCarItem, PCautoCommentItem

class PcautoSpider(scrapy.Spider):
    name = 'pcauto'
    allowed_domains = ['price.pcauto.com.cn']
    start_urls = [
        'https://price.pcauto.com.cn/top/sales/s1-t1.html',   # 轿车榜
        'https://price.pcauto.com.cn/top/sales/s2-t1.html',   # SUV榜
    ]

    def parse(self, response):
        # 调试：保存实际响应内容，方便核对（可选，跑通后可删除）
        with open('debug_sales_real.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        self.logger.info(f"已保存实际页面到 debug_sales_real.html")

        # 最稳健的 XPath：直接定位到包含车型链接的表格行
        rows = response.xpath('//tr[td[@class="col2 brand"]]')
        self.logger.info(f"共找到 {len(rows)} 个车型行")

        for row in rows:
            car_link = row.xpath('.//td[@class="col2 brand"]/a/@href').get()
            if not car_link:
                continue

            car_name = row.xpath('.//td[@class="col2 brand"]/a/text()').get()
            price = row.xpath('.//td[@class="col3 price"]/text()').get()
            brand = row.xpath('.//td[@class="col4 relBrand"]/a/text()').get()

            import re
            car_id_match = re.search(r'sg(\d+)', car_link)
            if not car_id_match:
                continue
            car_id = car_id_match.group(1)

            car_item = PCautoCarItem()
            car_item['car_id'] = car_id
            car_item['model_name'] = car_name.strip() if car_name else ''
            car_item['brand'] = brand.strip() if brand else ''
            car_item['price'] = price.strip() if price else ''
            yield car_item

            comment_url = f'https://price.pcauto.com.cn/comment/sg{car_id}/'
            yield scrapy.Request(
                comment_url,
                callback=self.parse_comments,
                meta={'car_id': car_id, 'page_num': 1}
            )

        # 处理销量榜分页（如果有下一页）
        next_page = response.xpath('//a[@class="next"]/@href').get()
        if not next_page:
            next_page = response.xpath('//a[contains(text(),"下一页")]/@href').get()
        if next_page:
            yield scrapy.Request(response.urljoin(next_page), callback=self.parse)

    def parse_car_detail(self, response):
        # 提取车型 ID
        match = re.search(r'sg(\d+)', response.url)
        if not match:
            return
        car_id = match.group(1)

        car_item = PCautoCarItem()
        car_item['car_id'] = car_id

        # 1. 车型名称：取自面包屑的最后一个 <a> 标签
        model_name = response.xpath('//div[@class="position"]/a[last()]/text()').get()
        car_item['model_name'] = model_name.strip() if model_name else ''

        # 2. 品牌：取自面包屑的倒数第三个 <a> 标签（例如“东风风行”）
        brand = response.xpath('//div[@class="position"]/a[last()-2]/text()').get()
        car_item['brand'] = brand.strip() if brand else ''

        # 3. 价格区间：官方指导价所在的 <em class="price">
        price = response.xpath('//em[@class="price"]/text()').get()
        car_item['price'] = price.strip() if price else ''

        yield car_item

        # 请求评论页
        comment_url = f'https://price.pcauto.com.cn/comment/sg{car_id}/'
        yield scrapy.Request(comment_url, callback=self.parse_comments,
                             meta={'car_id': car_id, 'page_num': 1})

    def parse_comments(self, response):
        car_id = response.meta['car_id']
        current_page = response.meta.get('page_num', 1)
        max_pages = 5  # 每个车型最多抓取5页，可根据需要修改

        if current_page > max_pages:
            self.logger.info(f"Reached max pages ({max_pages}) for car {car_id}, stopping.")
            return

        # 定位每一条评论的根节点
        comment_nodes = response.xpath('//div[@class="litDy clearfix"]')
        self.logger.info(f"Found {len(comment_nodes)} comments for car {car_id} (page {current_page})")

        for node in comment_nodes:
            item = PCautoCommentItem()
            item['car_id'] = car_id

            # 1. 用户名
            nickname = node.xpath('.//div[@class="txBox"]//p/a/text()').get()
            item['nickname'] = nickname.strip() if nickname else ''

            # 2. 发表时间（格式如 "2022-08-10 发表"）
            pub_time = node.xpath('.//div[@class="txBox"]//span/a/text()').get()
            if pub_time:
                pub_time = pub_time.replace('发表', '').strip()
            item['publish_time'] = pub_time

            # 3. 裸车价格（万元）
            price_text = node.xpath(
                './/div[@class="line"]/em[contains(text(),"裸车价格")]/following-sibling::i/text()').get()
            item['purchase_price'] = price_text.strip() if price_text else ''

            # 4. 综合评分（从 meter 脚本中提取）
            meter_script = node.xpath('.//script[contains(text(),"new Meter")]/text()').get()
            rating_val = 0.0
            if meter_script:
                import re
                match = re.search(r"'score'\s*:\s*'?([\d.]+)'?", meter_script)
                if match:
                    rating_val = float(match.group(1))
            item['rating'] = rating_val

            # 5. 优点
            advantages = node.xpath('.//div[@class="conLit youdian"]/span/text()').get()
            item['advantages'] = advantages.strip() if advantages else ''

            # 6. 缺点
            disadvantages = node.xpath('.//div[@class="conLit quedian"]/span/text()').get()
            item['disadvantages'] = disadvantages.strip() if disadvantages else ''

            # 7. 完整评论文本（拼接所有分类）
            all_parts = node.xpath('.//div[@class="dianPing"]/div[@class="conLit"]')
            full_text_list = []
            for part in all_parts:
                category = part.xpath('.//b/text()').get(default='').strip()
                text = part.xpath('.//span/text()').get(default='').strip()
                if category and text:
                    full_text_list.append(f"{category}{text}")
                elif text:
                    full_text_list.append(text)
            item['full_comment'] = '\n'.join(full_text_list)

            yield item

        # 处理翻页
        next_page = response.xpath('//a[@class="next"]/@href').get()
        if not next_page:
            next_page = response.xpath('//a[contains(text(),"下一页")]/@href').get()
        if next_page:
            yield scrapy.Request(
                response.urljoin(next_page),
                callback=self.parse_comments,
                meta={'car_id': car_id, 'page_num': current_page + 1}
            )