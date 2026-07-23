"""URL解析模块测试"""
import pytest
import sys
import os

# 添加模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from core.parser import col_to_letter, extract_token_from_url


class TestColToLetter:
    """列号转字母测试"""
    
    def test_single_letter(self):
        """测试单字母列"""
        assert col_to_letter(1) == 'A'
        assert col_to_letter(2) == 'B'
        assert col_to_letter(26) == 'Z'
    
    def test_double_letter(self):
        """测试双字母列"""
        assert col_to_letter(27) == 'AA'
        assert col_to_letter(28) == 'AB'
        assert col_to_letter(52) == 'AZ'
        assert col_to_letter(53) == 'BA'
    
    def test_triple_letter(self):
        """测试三字母列"""
        assert col_to_letter(703) == 'AAA'
        assert col_to_letter(728) == 'AAZ'


class TestExtractTokenFromUrl:
    """URL解析测试"""
    
    def test_base_url(self):
        """测试多维表格URL"""
        url = "https://example.feishu.cn/base/TGE4boMuxanzjfsrqpKcrrHgnhb"
        result = extract_token_from_url(url)
        assert result['type'] == 'bitable'
        assert result['token'] == 'TGE4boMuxanzjfsrqpKcrrHgnhb'
    
    def test_sheets_url(self):
        """测试电子表格URL"""
        url = "https://example.feishu.cn/sheets/BULrsDONfhy5wmt4pJLcdUCfnWf"
        result = extract_token_from_url(url)
        assert result['type'] == 'sheet'
        assert result['token'] == 'BULrsDONfhy5wmt4pJLcdUCfnWf'
    
    def test_base_url_with_table(self):
        """测试带table参数的URL"""
        url = "https://example.feishu.cn/base/TGE4boMuxanzjfsrqpKcrrHgnhb?table=tblX1nRl2H8F051h"
        result = extract_token_from_url(url)
        assert result['type'] == 'bitable'
        assert result['token'] == 'TGE4boMuxanzjfsrqpKcrrHgnhb'
        assert result['table_id'] == 'tblX1nRl2H8F051h'
    
    def test_invalid_url(self):
        """测试无效URL"""
        url = "https://example.com/invalid"
        result = extract_token_from_url(url)
        assert result['type'] is None
        assert result['token'] is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
