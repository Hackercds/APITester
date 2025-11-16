#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
随机内容生成工具模块
提供各种随机数据生成功能，支持模型分词表生成和测试数据创建
"""

import random
import string
import datetime
import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional, Union, Callable
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RandomGenerator:
    """
    随机数据生成器基类
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        初始化随机生成器
        
        Args:
            seed: 随机种子，如果为None则使用系统随机种子
        """
        if seed is not None:
            random.seed(seed)
    
    def generate(self, *args, **kwargs) -> Any:
        """
        生成随机数据
        由子类实现
        """
        raise NotImplementedError("子类必须实现generate方法")


class TextRandomGenerator(RandomGenerator):
    """
    文本随机生成器
    """
    
    # 常见汉字字符集（简化版，实际使用时可以扩展）
    COMMON_CHINESE_CHARS = '的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动同工也能下过子说产种面而方后多定行学法所民得经十三之进等部度家电力里如水化高自二理起小物现实加量都两体制机当使点从业本去把性好应开它合还因由其些然前外天政四日那社义事平形相全表间样与关各重新线内数正心反你明看原又么利比或但质气第向道命此变边条较技术党者更感直理者很石劳便团量活设及管特件长求老头基资边流路级少图山统接知较将组见计别她手角期根论运农指几九区强放决西被干做必战先回则任取据处队南给色光门即保治北造百规热领七海口东导器压志世金增争济阶油思术极交受联什认六共权收证改清己美再采转更单风切打白教速花带安场身车例真务具万每目至达走积示议声报斗完类八离华名确才科张信马节话米整空元况今集温传土许步群广石记需段研界拉林律叫且究观越织装影算低持音众书布复容儿须际商非验连断深难近矿千周委素技备半办青省列习响约支般史感劳便团量活设及管特件长求老头基资边流路级少图山统接知较将组见计别她手角期根论运农指几九区强放决西被干做必战先回则任取据处队南给色光门即保治北造百规热领七海口东导器压志世金增争济阶油思术极交受联什认六共权收证改清己美再采转更单风切打白教速花带安场身车例真务具万每目至达走积示议声报斗完类八离华名确才科张信马节话米整空元况今集温传土许步群广石记需段研界拉林律叫且究观越织装影算低持音众书布复容儿须际商非验连断深难近矿千周委素技备半办青省列习响约支般史感劳便团量活设及管特件长求老头基资边流路级少图山统接知较将组见计别她手角期根论运农指几九区强放决西被干做必战先回则任取据处队南给色光门即保治北造百规热领七海口东导器压志世金增争济阶油思术极交受联什认六共权收证改清己美再采转更单风切打白教速花带安场身车例真务具万每目至达走积示议声报斗完类八离华名确才科张信马节话米整空元况今集温传土许步群广石记需段研界拉林律叫且究观越织装影算低持音众书布复容儿须际商非验连断深难近矿千周委素技备半办青省列习响约支般史'
    
    # 常见英文单词列表（简化版）
    COMMON_ENGLISH_WORDS = [
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'I',
        'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
        'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
        'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what',
        'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me',
        'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know', 'take',
        'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other',
        'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also',
        'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well', 'way',
        'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us'
    ]
    
    def generate(self, 
                 length: int = 10,
                 charset: str = string.ascii_letters + string.digits,
                 *args, **kwargs) -> str:
        """
        生成随机字符串
        
        Args:
            length: 字符串长度
            charset: 字符集
            
        Returns:
            随机字符串
        """
        return ''.join(random.choice(charset) for _ in range(length))
    
    def generate_chinese(self, length: int = 10) -> str:
        """
        生成随机中文字符串
        
        Args:
            length: 字符串长度
            
        Returns:
            随机中文字符串
        """
        return ''.join(random.choice(self.COMMON_CHINESE_CHARS) for _ in range(length))
    
    def generate_english_sentence(self, min_words: int = 5, max_words: int = 15) -> str:
        """
        生成随机英文句子
        
        Args:
            min_words: 最小单词数
            max_words: 最大单词数
            
        Returns:
            随机英文句子
        """
        word_count = random.randint(min_words, max_words)
        words = [random.choice(self.COMMON_ENGLISH_WORDS) for _ in range(word_count)]
        
        # 首字母大写，添加标点符号
        sentence = ' '.join(words)
        sentence = sentence.capitalize() + random.choice(['.', '!', '?'])
        
        return sentence
    
    def generate_paragraph(self, 
                          min_sentences: int = 3, 
                          max_sentences: int = 8,
                          language: str = 'english') -> str:
        """
        生成随机段落
        
        Args:
            min_sentences: 最小句子数
            max_sentences: 最大句子数
            language: 语言，'english'或'chinese'
            
        Returns:
            随机段落
        """
        sentence_count = random.randint(min_sentences, max_sentences)
        
        if language == 'english':
            sentences = [self.generate_english_sentence() for _ in range(sentence_count)]
        elif language == 'chinese':
            # 中文句子生成：随机长度的中文文本
            sentences = []
            for _ in range(sentence_count):
                sent_length = random.randint(10, 30)
                sentence = self.generate_chinese(sent_length) + random.choice(['。', '！', '？'])
                sentences.append(sentence)
        else:
            raise ValueError(f"不支持的语言: {language}")
        
        return ' '.join(sentences)
    
    def generate_text(self, 
                     min_paragraphs: int = 2,
                     max_paragraphs: int = 5,
                     language: str = 'english') -> str:
        """
        生成随机文本
        
        Args:
            min_paragraphs: 最小段落数
            max_paragraphs: 最大段落数
            language: 语言，'english'或'chinese'
            
        Returns:
            随机文本
        """
        paragraph_count = random.randint(min_paragraphs, max_paragraphs)
        paragraphs = [self.generate_paragraph(language=language) for _ in range(paragraph_count)]
        
        return '\n\n'.join(paragraphs)


class NumberRandomGenerator(RandomGenerator):
    """
    数字随机生成器
    """
    
    def generate(self, 
                 min_value: int = 0, 
                 max_value: int = 100,
                 *args, **kwargs) -> int:
        """
        生成随机整数
        
        Args:
            min_value: 最小值
            max_value: 最大值
            
        Returns:
            随机整数
        """
        return random.randint(min_value, max_value)
    
    def generate_float(self, 
                      min_value: float = 0.0,
                      max_value: float = 1.0,
                      precision: int = 2) -> float:
        """
        生成随机浮点数
        
        Args:
            min_value: 最小值
            max_value: 最大值
            precision: 小数位数
            
        Returns:
            随机浮点数
        """
        value = random.uniform(min_value, max_value)
        return round(value, precision)
    
    def generate_decimal(self, 
                        min_value: int = 0,
                        max_value: int = 100,
                        decimal_places: int = 2) -> str:
        """
        生成随机小数字符串
        
        Args:
            min_value: 整数部分最小值
            max_value: 整数部分最大值
            decimal_places: 小数位数
            
        Returns:
            随机小数字符串
        """
        integer_part = random.randint(min_value, max_value)
        decimal_part = ''.join(random.choice(string.digits) for _ in range(decimal_places))
        
        return f"{integer_part}.{decimal_part}"
    
    def generate_hex(self, length: int = 8) -> str:
        """
        生成随机十六进制字符串
        
        Args:
            length: 长度（字符数）
            
        Returns:
            随机十六进制字符串
        """
        hex_chars = string.hexdigits[:16]  # 只使用小写十六进制字符
        return ''.join(random.choice(hex_chars) for _ in range(length))


class DateRandomGenerator(RandomGenerator):
    """
    日期随机生成器
    """
    
    def generate(self, 
                 start_year: int = 1970,
                 end_year: int = 2030,
                 format: str = '%Y-%m-%d',
                 *args, **kwargs) -> str:
        """
        生成随机日期字符串
        
        Args:
            start_year: 开始年份
            end_year: 结束年份
            format: 日期格式
            
        Returns:
            随机日期字符串
        """
        # 生成随机日期
        start_date = datetime.date(start_year, 1, 1)
        end_date = datetime.date(end_year, 12, 31)
        
        # 计算日期范围的天数
        days_diff = (end_date - start_date).days
        
        # 随机选择天数偏移
        random_days = random.randint(0, days_diff)
        
        # 计算随机日期
        random_date = start_date + datetime.timedelta(days=random_days)
        
        return random_date.strftime(format)
    
    def generate_time(self, format: str = '%H:%M:%S') -> str:
        """
        生成随机时间字符串
        
        Args:
            format: 时间格式
            
        Returns:
            随机时间字符串
        """
        # 生成随机时间
        hours = random.randint(0, 23)
        minutes = random.randint(0, 59)
        seconds = random.randint(0, 59)
        
        random_time = datetime.time(hours, minutes, seconds)
        
        return random_time.strftime(format)
    
    def generate_datetime(self, 
                         start_year: int = 1970,
                         end_year: int = 2030,
                         format: str = '%Y-%m-%d %H:%M:%S') -> str:
        """
        生成随机日期时间字符串
        
        Args:
            start_year: 开始年份
            end_year: 结束年份
            format: 日期时间格式
            
        Returns:
            随机日期时间字符串
        """
        # 生成随机日期
        start_datetime = datetime.datetime(start_year, 1, 1, 0, 0, 0)
        end_datetime = datetime.datetime(end_year, 12, 31, 23, 59, 59)
        
        # 计算时间范围的秒数
        seconds_diff = (end_datetime - start_datetime).total_seconds()
        
        # 随机选择秒数偏移
        random_seconds = random.randint(0, int(seconds_diff))
        
        # 计算随机日期时间
        random_datetime = start_datetime + datetime.timedelta(seconds=random_seconds)
        
        return random_datetime.strftime(format)
    
    def generate_timestamp(self, 
                          start_year: int = 1970,
                          end_year: int = 2030,
                          unit: str = 'second') -> int:
        """
        生成随机时间戳
        
        Args:
            start_year: 开始年份
            end_year: 结束年份
            unit: 时间单位，'second'或'millisecond'
            
        Returns:
            随机时间戳
        """
        # 生成随机日期时间
        start_datetime = datetime.datetime(start_year, 1, 1, 0, 0, 0)
        end_datetime = datetime.datetime(end_year, 12, 31, 23, 59, 59)
        
        # 计算时间范围的秒数
        seconds_diff = (end_datetime - start_datetime).total_seconds()
        
        # 随机选择秒数偏移
        random_seconds = random.randint(0, int(seconds_diff))
        
        # 计算随机时间戳
        random_timestamp = int((start_datetime + datetime.timedelta(seconds=random_seconds)).timestamp())
        
        # 根据单位调整
        if unit == 'millisecond':
            random_timestamp *= 1000
        elif unit != 'second':
            raise ValueError(f"不支持的时间单位: {unit}")
        
        return random_timestamp


class NetworkRandomGenerator(RandomGenerator):
    """
    网络相关随机生成器
    """
    
    # 常见顶级域名
    COMMON_TLDS = [
        'com', 'org', 'net', 'io', 'app', 'dev', 'info', 'biz', 
        'cn', 'jp', 'kr', 'uk', 'us', 'ca', 'au', 'de', 'fr', 'it'
    ]
    
    def generate_ipv4(self) -> str:
        """
        生成随机IPv4地址
        
        Returns:
            随机IPv4地址
        """
        octets = [str(random.randint(0, 255)) for _ in range(4)]
        return '.'.join(octets)
    
    def generate_ipv6(self) -> str:
        """
        生成随机IPv6地址
        
        Returns:
            随机IPv6地址
        """
        hex_chars = string.hexdigits[:16]  # 只使用小写十六进制字符
        groups = []
        
        for _ in range(8):
            group = ''.join(random.choice(hex_chars) for _ in range(4))
            groups.append(group)
        
        return ':'.join(groups)
    
    def generate_domain(self, 
                       min_length: int = 3,
                       max_length: int = 10) -> str:
        """
        生成随机域名
        
        Args:
            min_length: 域名最小长度
            max_length: 域名最大长度
            
        Returns:
            随机域名
        """
        # 生成域名主体
        domain_length = random.randint(min_length, max_length)
        domain_chars = string.ascii_lowercase + string.digits + '-'  # 域名允许的字符
        domain_name = ''.join(random.choice(domain_chars) for _ in range(domain_length))
        
        # 确保域名不以连字符开头或结尾
        domain_name = domain_name.strip('-')
        if not domain_name:  # 如果全是连字符，重新生成
            domain_name = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        
        # 选择顶级域名
        tld = random.choice(self.COMMON_TLDS)
        
        return f"{domain_name}.{tld}"
    
    def generate_email(self, 
                      username_min_length: int = 3,
                      username_max_length: int = 10,
                      domain: Optional[str] = None) -> str:
        """
        生成随机邮箱地址
        
        Args:
            username_min_length: 用户名最小长度
            username_max_length: 用户名最大长度
            domain: 自定义域名，如果为None则随机生成
            
        Returns:
            随机邮箱地址
        """
        # 生成用户名
        username_length = random.randint(username_min_length, username_max_length)
        username_chars = string.ascii_lowercase + string.digits + '_-'  # 用户名允许的字符
        username = ''.join(random.choice(username_chars) for _ in range(username_length))
        
        # 确保用户名不以连字符或下划线开头或结尾
        username = username.strip('_-')
        if not username:  # 如果全是特殊字符，重新生成
            username = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        
        # 生成或使用自定义域名
        if domain is None:
            domain = self.generate_domain()
        
        return f"{username}@{domain}"
    
    def generate_url(self, 
                    protocol: str = 'https',
                    path_depth: int = 2) -> str:
        """
        生成随机URL
        
        Args:
            protocol: 协议，'http'或'https'
            path_depth: 路径深度
            
        Returns:
            随机URL
        """
        # 生成域名
        domain = self.generate_domain()
        
        # 生成路径
        path_parts = []
        for _ in range(path_depth):
            part_length = random.randint(2, 8)
            part = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(part_length))
            path_parts.append(part)
        
        path = '/' + '/'.join(path_parts)
        
        # 随机添加查询参数
        url = f"{protocol}://{domain}{path}"
        
        if random.random() > 0.5:  # 50%概率添加查询参数
            param_count = random.randint(1, 3)
            params = []
            for i in range(param_count):
                key = 'param' + str(i+1)
                value = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(5))
                params.append(f"{key}={value}")
            
            url += '?' + '&'.join(params)
        
        return url


class PhoneRandomGenerator(RandomGenerator):
    """
    手机号随机生成器
    """
    
    # 中国手机号前缀
    CHINA_MOBILE_PREFIXES = [
        '130', '131', '132', '133', '134', '135', '136', '137', '138', '139',
        '150', '151', '152', '153', '155', '156', '157', '158', '159',
        '170', '171', '172', '173', '175', '176', '177', '178',
        '180', '181', '182', '183', '184', '185', '186', '187', '188', '189',
        '191', '193', '195', '196', '197', '198', '199'
    ]
    
    def generate_china_mobile(self) -> str:
        """
        生成随机中国手机号
        
        Returns:
            随机中国手机号
        """
        # 选择前缀
        prefix = random.choice(self.CHINA_MOBILE_PREFIXES)
        
        # 生成剩余8位
        suffix = ''.join(random.choice(string.digits) for _ in range(8))
        
        return prefix + suffix
    
    def generate_telephone(self, 
                          area_code: Optional[str] = None,
                          with_area_code: bool = True) -> str:
        """
        生成随机电话号码
        
        Args:
            area_code: 自定义区号，如果为None则随机生成
            with_area_code: 是否包含区号
            
        Returns:
            随机电话号码
        """
        # 生成区号
        if area_code is None:
            area_code = ''.join(random.choice(string.digits) for _ in range(3, 5))  # 3-4位区号
        
        # 生成电话号码
        phone_number = ''.join(random.choice(string.digits) for _ in range(7, 9))  # 7-8位号码
        
        if with_area_code:
            return f"({area_code})-{phone_number}"
        else:
            return phone_number


class IDCardRandomGenerator(RandomGenerator):
    """
    身份证号随机生成器
    """
    
    # 中国省份代码
    CHINA_PROVINCE_CODES = [
        '11', '12', '13', '14', '15', '21', '22', '23', '31', '32', '33', '34', '35', '36', '37',
        '41', '42', '43', '44', '45', '46', '50', '51', '52', '53', '54', '61', '62', '63', '64', '65',
        '71', '81', '82'
    ]
    
    def generate_china_id_card(self, 
                              birth_year: Optional[int] = None,
                              birth_month: Optional[int] = None,
                              birth_day: Optional[int] = None,
                              gender: Optional[str] = None) -> str:
        """
        生成随机中国身份证号
        
        Args:
            birth_year: 出生年份，如果为None则随机生成
            birth_month: 出生月份，如果为None则随机生成
            birth_day: 出生日期，如果为None则随机生成
            gender: 性别，'male'或'female'，如果为None则随机生成
            
        Returns:
            随机中国身份证号
        """
        # 1. 生成地址码（前6位）
        province_code = random.choice(self.CHINA_PROVINCE_CODES)
        city_code = ''.join(random.choice(string.digits) for _ in range(2))
        district_code = ''.join(random.choice(string.digits) for _ in range(2))
        address_code = province_code + city_code + district_code
        
        # 2. 生成出生日期码（中间8位）
        if birth_year is None:
            birth_year = random.randint(1950, 2005)
        
        if birth_month is None:
            birth_month = random.randint(1, 12)
        
        # 确定每月的天数
        if birth_month in [4, 6, 9, 11]:
            max_days = 30
        elif birth_month == 2:
            # 处理闰年
            if (birth_year % 4 == 0 and birth_year % 100 != 0) or (birth_year % 400 == 0):
                max_days = 29
            else:
                max_days = 28
        else:
            max_days = 31
        
        if birth_day is None:
            birth_day = random.randint(1, max_days)
        
        birth_date = f"{birth_year:04d}{birth_month:02d}{birth_day:02d}"
        
        # 3. 生成顺序码（第15-17位）
        # 第17位奇数表示男性，偶数表示女性
        if gender is None:
            gender = random.choice(['male', 'female'])
        
        sequence_number = random.randint(0, 99)
        gender_code = random.randint(1, 9) if gender == 'male' else random.randint(0, 8) * 2
        
        # 确保性别码为奇数或偶数
        if gender == 'male' and gender_code % 2 == 0:
            gender_code += 1
        elif gender == 'female' and gender_code % 2 == 1:
            gender_code -= 1
        
        sequence_code = f"{sequence_number:02d}{gender_code}"
        
        # 4. 生成前17位
        first_17_digits = address_code + birth_date + sequence_code
        
        # 5. 计算校验码（第18位）
        check_code = self._calculate_id_card_check_code(first_17_digits)
        
        return first_17_digits + check_code
    
    def _calculate_id_card_check_code(self, first_17_digits: str) -> str:
        """
        计算身份证校验码
        
        Args:
            first_17_digits: 身份证前17位
            
        Returns:
            校验码
        """
        # 加权因子
        weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        
        # 校验码映射
        check_codes = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']
        
        # 计算加权和
        total = 0
        for i in range(17):
            total += int(first_17_digits[i]) * weights[i]
        
        # 取模并获取校验码
        check_index = total % 11
        
        return check_codes[check_index]


class TokenRandomGenerator(RandomGenerator):
    """
    令牌随机生成器
    """
    
    def generate_token(self, 
                      length: int = 32,
                      charset: str = string.ascii_letters + string.digits) -> str:
        """
        生成随机令牌
        
        Args:
            length: 令牌长度
            charset: 字符集
            
        Returns:
            随机令牌
        """
        return ''.join(random.choice(charset) for _ in range(length))
    
    def generate_uuid(self) -> str:
        """
        生成随机UUID（简化版，不保证唯一性）
        
        Returns:
            随机UUID
        """
        # 格式：xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        parts = []
        parts.append(''.join(random.choice(string.hexdigits[:16]) for _ in range(8)))
        parts.append(''.join(random.choice(string.hexdigits[:16]) for _ in range(4)))
        parts.append(''.join(random.choice(string.hexdigits[:16]) for _ in range(4)))
        parts.append(''.join(random.choice(string.hexdigits[:16]) for _ in range(4)))
        parts.append(''.join(random.choice(string.hexdigits[:16]) for _ in range(12)))
        
        return '-'.join(parts).lower()
    
    def generate_md5(self, 
                    input_str: Optional[str] = None,
                    length: int = 32) -> str:
        """
        生成随机MD5哈希
        
        Args:
            input_str: 输入字符串，如果为None则随机生成
            length: 输出长度（16或32）
            
        Returns:
            MD5哈希值
        """
        if input_str is None:
            input_str = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))
        
        md5_hash = hashlib.md5(input_str.encode('utf-8')).hexdigest()
        
        if length == 16:
            return md5_hash[8:24]  # 16位MD5
        elif length == 32:
            return md5_hash  # 32位MD5
        else:
            raise ValueError("MD5长度必须是16或32")
    
    def generate_sha256(self, input_str: Optional[str] = None) -> str:
        """
        生成随机SHA256哈希
        
        Args:
            input_str: 输入字符串，如果为None则随机生成
            
        Returns:
            SHA256哈希值
        """
        if input_str is None:
            input_str = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))
        
        return hashlib.sha256(input_str.encode('utf-8')).hexdigest()


class WordListGenerator(RandomGenerator):
    """
    基于分词表的随机文本生成器
    用于生成符合特定模型分词表的随机文本
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        初始化分词表生成器
        
        Args:
            seed: 随机种子
        """
        super().__init__(seed)
        self.word_lists = {
            'chinese_common': self.COMMON_CHINESE_CHARS,
            'english_common': self.COMMON_ENGLISH_WORDS
        }
    
    # 继承TextRandomGenerator的常量
    COMMON_CHINESE_CHARS = TextRandomGenerator.COMMON_CHINESE_CHARS
    COMMON_ENGLISH_WORDS = TextRandomGenerator.COMMON_ENGLISH_WORDS
    
    def load_word_list(self, 
                      name: str,
                      words: Union[str, List[str]],
                      overwrite: bool = False) -> None:
        """
        加载分词表
        
        Args:
            name: 分词表名称
            words: 词列表，可以是字符串（每个字符为一个词）或单词列表
            overwrite: 是否覆盖已存在的分词表
        """
        if name in self.word_lists and not overwrite:
            raise ValueError(f"分词表 '{name}' 已存在")
        
        self.word_lists[name] = words
        logger.info(f"已加载分词表: {name}，包含 {len(words)} 个词")
    
    def load_word_list_from_file(self, 
                                name: str,
                                file_path: str,
                                encoding: str = 'utf-8',
                                delimiter: Optional[str] = None,
                                overwrite: bool = False) -> None:
        """
        从文件加载分词表
        
        Args:
            name: 分词表名称
            file_path: 文件路径
            encoding: 文件编码
            delimiter: 分隔符，如果为None则按行读取
            overwrite: 是否覆盖已存在的分词表
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        words = []
        
        with open(file_path, 'r', encoding=encoding) as f:
            if delimiter is None:
                # 按行读取
                for line in f:
                    word = line.strip()
                    if word:
                        words.append(word)
            else:
                # 使用分隔符读取
                content = f.read()
                words = [word.strip() for word in content.split(delimiter) if word.strip()]
        
        self.load_word_list(name, words, overwrite)
    
    def generate_from_word_list(self, 
                               name: str,
                               word_count: int = 10,
                               separator: str = ' ') -> str:
        """
        基于分词表生成随机文本
        
        Args:
            name: 分词表名称
            word_count: 生成的词数量
            separator: 词之间的分隔符
            
        Returns:
            随机文本
        """
        if name not in self.word_lists:
            raise ValueError(f"分词表 '{name}' 不存在")
        
        word_list = self.word_lists[name]
        if not word_list:
            raise ValueError(f"分词表 '{name}' 为空")
        
        # 生成随机文本
        words = []
        for _ in range(word_count):
            words.append(random.choice(word_list))
        
        return separator.join(words)
    
    def generate_model_input(self, 
                            word_list_name: str,
                            min_length: int = 50,
                            max_length: int = 200,
                            language: str = 'chinese') -> str:
        """
        生成适合大模型输入的随机文本
        
        Args:
            word_list_name: 分词表名称
            min_length: 最小字符数
            max_length: 最大字符数
            language: 语言，'chinese'或'english'
            
        Returns:
            模型输入文本
        """
        # 如果未指定分词表，使用默认分词表
        if word_list_name not in self.word_lists:
            if language == 'chinese':
                word_list_name = 'chinese_common'
            elif language == 'english':
                word_list_name = 'english_common'
            else:
                raise ValueError(f"不支持的语言: {language}")
        
        # 生成文本直到达到长度要求
        result = ""
        target_length = random.randint(min_length, max_length)
        
        while len(result) < target_length:
            # 根据语言选择适当的生成方式
            if language == 'chinese':
                # 中文：生成句子
                sentence_length = random.randint(10, 30)
                sentence = self.generate_from_word_list(
                    word_list_name, 
                    sentence_length, 
                    separator=''
                )
                sentence += random.choice(['。', '！', '？'])
            else:  # english
                # 英文：生成句子
                sentence_word_count = random.randint(5, 15)
                sentence = self.generate_from_word_list(
                    word_list_name, 
                    sentence_word_count,
                    separator=' '
                )
                # 首字母大写，添加标点
                sentence = sentence.capitalize() + random.choice(['.', '!', '?'])
            
            # 添加句子到结果
            if result and random.random() > 0.3:  # 70%概率添加空格或换行
                if language == 'chinese' or random.random() > 0.5:
                    result += ' '
                else:
                    result += '\n'
            
            result += sentence
        
        # 截取到目标长度
        if len(result) > target_length:
            # 尝试在标点处截断
            truncate_pos = target_length
            for i in range(target_length, max(0, target_length - 20), -1):
                if i < len(result) and result[i] in '。！？.!?\n':
                    truncate_pos = i + 1
                    break
            
            result = result[:truncate_pos]
        
        return result
    
    def get_word_list_names(self) -> List[str]:
        """
        获取已加载的分词表名称列表
        
        Returns:
            分词表名称列表
        """
        return list(self.word_lists.keys())
    
    def get_word_list_info(self, name: str) -> Dict[str, Any]:
        """
        获取分词表信息
        
        Args:
            name: 分词表名称
            
        Returns:
            分词表信息
        """
        if name not in self.word_lists:
            raise ValueError(f"分词表 '{name}' 不存在")
        
        word_list = self.word_lists[name]
        
        return {
            'name': name,
            'size': len(word_list),
            'sample_words': word_list[:min(10, len(word_list))],  # 前10个样本
            'type': 'character' if isinstance(word_list, str) else 'word'
        }


class DataGenerator:
    """
    综合数据生成器
    提供各种数据类型的随机生成功能
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        初始化数据生成器
        
        Args:
            seed: 随机种子
        """
        self.text_gen = TextRandomGenerator(seed)
        self.number_gen = NumberRandomGenerator(seed)
        self.date_gen = DateRandomGenerator(seed)
        self.network_gen = NetworkRandomGenerator(seed)
        self.phone_gen = PhoneRandomGenerator(seed)
        self.id_card_gen = IDCardRandomGenerator(seed)
        self.token_gen = TokenRandomGenerator(seed)
        self.word_list_gen = WordListGenerator(seed)
    
    def generate(self, 
                data_type: str,
                *args, **kwargs) -> Any:
        """
        通用生成方法
        根据数据类型调用相应的生成器
        
        Args:
            data_type: 数据类型
            
        Returns:
            随机数据
        """
        # 映射数据类型到生成方法
        type_handlers = {
            # 文本类型
            'string': self.text_gen.generate,
            'chinese': self.text_gen.generate_chinese,
            'sentence': self.text_gen.generate_english_sentence,
            'paragraph': self.text_gen.generate_paragraph,
            'text': self.text_gen.generate_text,
            
            # 数字类型
            'integer': self.number_gen.generate,
            'float': self.number_gen.generate_float,
            'decimal': self.number_gen.generate_decimal,
            'hex': self.number_gen.generate_hex,
            
            # 日期时间类型
            'date': self.date_gen.generate,
            'time': self.date_gen.generate_time,
            'datetime': self.date_gen.generate_datetime,
            'timestamp': self.date_gen.generate_timestamp,
            
            # 网络类型
            'ipv4': self.network_gen.generate_ipv4,
            'ipv6': self.network_gen.generate_ipv6,
            'domain': self.network_gen.generate_domain,
            'email': self.network_gen.generate_email,
            'url': self.network_gen.generate_url,
            
            # 电话类型
            'mobile': self.phone_gen.generate_china_mobile,
            'telephone': self.phone_gen.generate_telephone,
            
            # 身份证类型
            'id_card': self.id_card_gen.generate_china_id_card,
            
            # 令牌类型
            'token': self.token_gen.generate_token,
            'uuid': self.token_gen.generate_uuid,
            'md5': self.token_gen.generate_md5,
            'sha256': self.token_gen.generate_sha256,
            
            # 分词表类型
            'word_list_text': self.word_list_gen.generate_from_word_list,
            'model_input': self.word_list_gen.generate_model_input
        }
        
        # 调用对应的生成方法
        if data_type in type_handlers:
            return type_handlers[data_type](*args, **kwargs)
        else:
            raise ValueError(f"不支持的数据类型: {data_type}")
    
    def generate_dict(self, 
                     schema: Dict[str, Dict[str, Any]],
                     count: int = 1) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        根据模式生成随机字典数据
        
        Args:
            schema: 数据模式字典
                格式: {
                    'field_name': {
                        'type': 'data_type',
                        'args': [...],
                        'kwargs': {...}
                    },
                    ...
                }
            count: 生成的字典数量
            
        Returns:
            单个字典或字典列表
        """
        results = []
        
        for _ in range(count):
            data = {}
            
            for field_name, field_config in schema.items():
                # 获取字段类型和参数
                field_type = field_config.get('type', 'string')
                args = field_config.get('args', [])
                kwargs = field_config.get('kwargs', {})
                
                # 生成字段值
                data[field_name] = self.generate(field_type, *args, **kwargs)
            
            results.append(data)
        
        if count == 1:
            return results[0]
        else:
            return results
    
    def generate_json(self, 
                     schema: Dict[str, Dict[str, Any]],
                     count: int = 1,
                     indent: Optional[int] = 2) -> str:
        """
        根据模式生成随机JSON数据
        
        Args:
            schema: 数据模式字典
            count: 生成的对象数量
            indent: JSON缩进
            
        Returns:
            JSON字符串
        """
        data = self.generate_dict(schema, count)
        return json.dumps(data, ensure_ascii=False, indent=indent)
    
    def generate_csv(self, 
                    schema: Dict[str, Dict[str, Any]],
                    count: int = 10,
                    delimiter: str = ',') -> str:
        """
        根据模式生成随机CSV数据
        
        Args:
            schema: 数据模式字典
            count: 生成的记录数量
            delimiter: CSV分隔符
            
        Returns:
            CSV字符串
        """
        # 生成标题行
        headers = list(schema.keys())
        csv_lines = [delimiter.join(headers)]
        
        # 生成数据行
        for _ in range(count):
            row = []
            for field_name in headers:
                field_config = schema[field_name]
                field_type = field_config.get('type', 'string')
                args = field_config.get('args', [])
                kwargs = field_config.get('kwargs', {})
                
                # 生成字段值并转换为字符串
                value = self.generate(field_type, *args, **kwargs)
                value_str = str(value)
                
                # 如果值包含分隔符或换行符，用引号包围
                if delimiter in value_str or '\n' in value_str or '"' in value_str:
                    value_str = '"' + value_str.replace('"', '""') + '"'
                
                row.append(value_str)
            
            csv_lines.append(delimiter.join(row))
        
        return '\n'.join(csv_lines)
    
    def generate_custom(self, 
                       template: str,
                       placeholders: Optional[Dict[str, Dict[str, Any]]] = None) -> str:
        """
        根据模板生成自定义格式的随机数据
        
        Args:
            template: 模板字符串，使用 {{placeholder}} 格式的占位符
            placeholders: 占位符配置字典
                格式: {
                    'placeholder_name': {
                        'type': 'data_type',
                        'args': [...],
                        'kwargs': {...}
                    },
                    ...
                }
            
        Returns:
            生成的字符串
        """
        if placeholders is None:
            placeholders = {}
        
        # 查找所有占位符
        pattern = r'\{\{([^}]+)\}\}'
        matches = re.findall(pattern, template)
        
        result = template
        
        # 替换每个占位符
        for placeholder in matches:
            placeholder_key = placeholder.strip()
            
            # 检查占位符配置
            if placeholder_key in placeholders:
                config = placeholders[placeholder_key]
                value = self.generate(
                    config.get('type', 'string'),
                    *config.get('args', []),
                    **config.get('kwargs', {})
                )
            else:
                # 如果没有配置，生成随机字符串
                value = self.text_gen.generate(length=10)
            
            # 替换占位符
            result = result.replace(f"{{{{{placeholder}}}}}", str(value))
        
        return result
    
    def load_word_list(self, 
                      name: str,
                      words: Union[str, List[str]],
                      overwrite: bool = False) -> 'DataGenerator':
        """
        加载分词表
        
        Args:
            name: 分词表名称
            words: 词列表
            overwrite: 是否覆盖
            
        Returns:
            数据生成器自身，支持链式调用
        """
        self.word_list_gen.load_word_list(name, words, overwrite)
        return self
    
    def load_word_list_from_file(self, 
                                name: str,
                                file_path: str,
                                encoding: str = 'utf-8',
                                delimiter: Optional[str] = None,
                                overwrite: bool = False) -> 'DataGenerator':
        """
        从文件加载分词表
        
        Args:
            name: 分词表名称
            file_path: 文件路径
            encoding: 文件编码
            delimiter: 分隔符
            overwrite: 是否覆盖
            
        Returns:
            数据生成器自身，支持链式调用
        """
        self.word_list_gen.load_word_list_from_file(
            name, file_path, encoding, delimiter, overwrite
        )
        return self


# 创建全局数据生成器实例
default_generator = DataGenerator()


# 便捷函数
def generate(data_type: str, *args, **kwargs) -> Any:
    """
    便捷函数：生成随机数据
    
    Args:
        data_type: 数据类型
        
    Returns:
        随机数据
    """
    return default_generator.generate(data_type, *args, **kwargs)


def generate_dict(schema: Dict[str, Dict[str, Any]], count: int = 1) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    便捷函数：生成随机字典
    
    Args:
        schema: 数据模式
        count: 生成数量
        
    Returns:
        字典或字典列表
    """
    return default_generator.generate_dict(schema, count)


def generate_json(schema: Dict[str, Dict[str, Any]], count: int = 1) -> str:
    """
    便捷函数：生成随机JSON
    
    Args:
        schema: 数据模式
        count: 生成数量
        
    Returns:
        JSON字符串
    """
    return default_generator.generate_json(schema, count)


def generate_csv(schema: Dict[str, Dict[str, Any]], count: int = 10) -> str:
    """
    便捷函数：生成随机CSV
    
    Args:
        schema: 数据模式
        count: 生成数量
        
    Returns:
        CSV字符串
    """
    return default_generator.generate_csv(schema, count)


def generate_custom(template: str, placeholders: Optional[Dict[str, Dict[str, Any]]] = None) -> str:
    """
    便捷函数：生成自定义格式数据
    
    Args:
        template: 模板字符串
        placeholders: 占位符配置
        
    Returns:
        生成的字符串
    """
    return default_generator.generate_custom(template, placeholders)


def load_word_list(name: str, words: Union[str, List[str]], overwrite: bool = False) -> None:
    """
    便捷函数：加载分词表
    
    Args:
        name: 分词表名称
        words: 词列表
        overwrite: 是否覆盖
    """
    default_generator.load_word_list(name, words, overwrite)


def load_word_list_from_file(name: str, file_path: str, **kwargs) -> None:
    """
    便捷函数：从文件加载分词表
    
    Args:
        name: 分词表名称
        file_path: 文件路径
    """
    default_generator.load_word_list_from_file(name, file_path, **kwargs)


def generate_model_input(word_list_name: str = 'chinese_common', **kwargs) -> str:
    """
    便捷函数：生成模型输入
    
    Args:
        word_list_name: 分词表名称
        
    Returns:
        模型输入文本
    """
    return default_generator.generate('model_input', word_list_name, **kwargs)


# 示例用法
if __name__ == "__main__":
    print("=== 随机内容生成工具示例 ===")
    
    # 创建数据生成器
    generator = DataGenerator(seed=42)  # 设置种子以获得可重复的结果
    
    # 示例1: 基本数据类型生成
    print("\n示例1: 基本数据类型生成")
    print(f"随机字符串: {generator.generate('string', length=15)}")
    print(f"随机中文: {generator.generate('chinese', length=10)}")
    print(f"随机整数: {generator.generate('integer', min_value=100, max_value=999)}")
    print(f"随机浮点数: {generator.generate('float', min_value=0.1, max_value=1.0, precision=4)}")
    print(f"随机日期: {generator.generate('date', format='%Y-%m-%d')}")
    print(f"随机邮箱: {generator.generate('email')}")
    print(f"随机手机号: {generator.generate('mobile')}")
    
    # 示例2: 结构化数据生成
    print("\n示例2: 结构化数据生成")
    user_schema = {
        'id': {'type': 'integer', 'kwargs': {'min_value': 1000, 'max_value': 9999}},
        'username': {'type': 'string', 'kwargs': {'length': 8}},
        'email': {'type': 'email'},
        'age': {'type': 'integer', 'kwargs': {'min_value': 18, 'max_value': 80}},
        'register_date': {'type': 'date'},
        'token': {'type': 'token', 'kwargs': {'length': 32}}
    }
    
    user_data = generator.generate_dict(user_schema)
    print("用户数据:")
    for key, value in user_data.items():
        print(f"  {key}: {value}")
    
    # 示例3: 模型输入生成
    print("\n示例3: 模型输入生成")
    # 生成适合中文模型的随机输入
    chinese_input = generator.generate('model_input', 
                                      word_list_name='chinese_common',
                                      min_length=50,
                                      max_length=100,
                                      language='chinese')
    print(f"中文模型输入:\n{chinese_input}")
    
    # 生成适合英文模型的随机输入
    english_input = generator.generate('model_input',
                                      word_list_name='english_common',
                                      min_length=50,
                                      max_length=100,
                                      language='english')
    print(f"英文模型输入:\n{english_input}")
    
    # 示例4: 自定义格式生成
    print("\n示例4: 自定义格式生成")
    template = "INSERT INTO users (id, name, email, created_at) VALUES ({{id}}, '{{name}}', '{{email}}', '{{created_at}}');"
    placeholders = {
        'id': {'type': 'integer', 'kwargs': {'min_value': 1, 'max_value': 1000}},
        'name': {'type': 'string', 'kwargs': {'length': 10}},
        'email': {'type': 'email'},
        'created_at': {'type': 'datetime'}
    }
    
    sql_insert = generator.generate_custom(template, placeholders)
    print(f"SQL插入语句:\n{sql_insert}")
    
    # 示例5: CSV数据生成
    print("\n示例5: CSV数据生成")
    csv_schema = {
        'product_id': {'type': 'string', 'kwargs': {'length': 8, 'charset': string.ascii_uppercase + string.digits}},
        'product_name': {'type': 'chinese', 'kwargs': {'length': 6}},
        'price': {'type': 'decimal', 'kwargs': {'min_value': 10, 'max_value': 999, 'decimal_places': 2}},
        'stock': {'type': 'integer', 'kwargs': {'min_value': 0, 'max_value': 1000}},
        'category': {'type': 'string', 'kwargs': {'charset': string.ascii_lowercase, 'length': 5}}
    }
    
    csv_data = generator.generate_csv(csv_schema, count=3)
    print(f"CSV数据:\n{csv_data}")
    
    print("\n随机内容生成工具示例完成")