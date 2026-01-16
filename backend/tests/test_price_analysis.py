"""
価格分析機能のテスト（E-2-2改善タスク1）
"""

import pytest
from app.analysis import extract_price_value, classify_price_range, compare_price_ranges


class TestExtractPriceValue:
    """価格抽出関数のテスト"""
    
    def testExtractPriceValueManYen(self):
        """万円パターン: '80万円/月' → 80.0"""
        assert extract_price_value("80万円/月") == 80.0
        assert extract_price_value("80万円") == 80.0
        assert extract_price_value("120万円/月") == 120.0
    
    def testExtractPriceValueRange(self):
        """範囲パターン: '50-60万円' → 55.0（中央値）"""
        assert extract_price_value("50-60万円") == 55.0
        assert extract_price_value("50-60万円/月") == 55.0
        assert extract_price_value("40~50万円") == 45.0
        assert extract_price_value("40〜50万円") == 45.0  # 全角チルダ
    
    def testExtractPriceValueComma(self):
        """カンマ区切りパターン: '¥800,000' → 80.0"""
        assert extract_price_value("¥800,000") == 80.0
        assert extract_price_value("800,000円") == 80.0
        assert extract_price_value("1,000,000円") == 100.0
        assert extract_price_value("$800,000") == 80.0
    
    def testExtractPriceValueNumber(self):
        """純粋な数値パターン"""
        assert extract_price_value("80") == 80.0
        assert extract_price_value("800000") == 80.0
        assert extract_price_value("1000000") == 100.0
    
    def testExtractPriceValueNone(self):
        """None → None"""
        assert extract_price_value(None) is None
    
    def testExtractPriceValueEmpty(self):
        """空文字 → None"""
        assert extract_price_value("") is None
        assert extract_price_value("   ") is None
    
    def testExtractPriceValueInvalid(self):
        """解析不可文字列 → None"""
        assert extract_price_value("応相談") is None
        assert extract_price_value("要相談") is None
        assert extract_price_value("面談時に提示") is None
        assert extract_price_value("スキルによる") is None
        assert extract_price_value("xxx") is None
    
    def testExtractPriceValueDecimal(self):
        """小数点を含む価格"""
        assert extract_price_value("80.5万円") == 80.5
        assert extract_price_value("50.5-60.5万円") == 55.5
    
    def testExtractPriceValueWithSpaces(self):
        """空白を含むパターン"""
        assert extract_price_value("80 万円 / 月") == 80.0
        assert extract_price_value("50 - 60 万円") == 55.0


class TestClassifyPriceRange:
    """価格帯分類関数のテスト"""
    
    def testClassifyPriceRangeHigh(self):
        """高単価: 80万円以上 → 'high'"""
        assert classify_price_range(80.0) == "high"
        assert classify_price_range(100.0) == "high"
        assert classify_price_range(150.0) == "high"
        assert classify_price_range(80.1) == "high"
    
    def testClassifyPriceRangeMid(self):
        """中単価: 50万円以上80万円未満 → 'mid'"""
        assert classify_price_range(50.0) == "mid"
        assert classify_price_range(60.0) == "mid"
        assert classify_price_range(79.9) == "mid"
        assert classify_price_range(70.0) == "mid"
    
    def testClassifyPriceRangeLow(self):
        """低単価: 50万円未満 → 'low'"""
        assert classify_price_range(49.9) == "low"
        assert classify_price_range(30.0) == "low"
        assert classify_price_range(10.0) == "low"
        assert classify_price_range(0.1) == "low"
    
    def testClassifyPriceRangeUnknown(self):
        """不明: None または 0以下 → 'unknown'"""
        assert classify_price_range(None) == "unknown"
        assert classify_price_range(0.0) == "unknown"
        assert classify_price_range(-10.0) == "unknown"
    
    def testClassifyPriceRangeBoundary(self):
        """境界値のテスト"""
        # 80万円ちょうど → high
        assert classify_price_range(80.0) == "high"
        # 79.99万円 → mid
        assert classify_price_range(79.99) == "mid"
        # 50万円ちょうど → mid
        assert classify_price_range(50.0) == "mid"
        # 49.99万円 → low
        assert classify_price_range(49.99) == "low"


class TestComparePriceRanges:
    """価格帯比較関数のテスト"""
    
    def testComparePriceRangesSuccess(self):
        """正常系: 価格帯の増減が正しく計算される"""
        base_rows = [
            {"UnitPrice": "80万円/月"},   # high
            {"UnitPrice": "100万円"},      # high
            {"UnitPrice": "60万円"},       # mid
            {"UnitPrice": "70万円"},       # mid
            {"UnitPrice": "50万円"},       # mid
            {"UnitPrice": "30万円"},       # low
            {"UnitPrice": "40万円"},       # low
            {"UnitPrice": "応相談"},       # unknown
        ]
        
        target_rows = [
            {"UnitPrice": "90万円"},       # high
            {"UnitPrice": "65万円"},       # mid
            {"UnitPrice": "55万円"},       # mid
            {"UnitPrice": "75万円"},       # mid
            {"UnitPrice": "52万円"},       # mid
            {"UnitPrice": "35万円"},       # low
            {"UnitPrice": "要相談"},       # unknown
        ]
        
        result = compare_price_ranges(base_rows, target_rows)
        
        # base の集計確認
        assert result["base"]["high"] == 2
        assert result["base"]["mid"] == 3
        assert result["base"]["low"] == 2
        assert result["base"]["unknown"] == 1
        
        # target の集計確認
        assert result["target"]["high"] == 1
        assert result["target"]["mid"] == 4
        assert result["target"]["low"] == 1
        assert result["target"]["unknown"] == 1
        
        # 増減の確認
        assert result["changes"]["high"]["diff"] == -1  # 2 → 1
        assert result["changes"]["mid"]["diff"] == 1    # 3 → 4
        assert result["changes"]["low"]["diff"] == -1   # 2 → 1
        assert result["changes"]["unknown"]["diff"] == 0 # 1 → 1
        
        # 増減率の確認（おおよそ）
        assert result["changes"]["high"]["percent"] == -50.0  # (1-2)/2 * 100
        assert result["changes"]["mid"]["percent"] == 33.3    # (4-3)/3 * 100
        assert result["changes"]["low"]["percent"] == -50.0   # (1-2)/2 * 100
    
    def testComparePriceRangesEmpty(self):
        """空データのケース"""
        result = compare_price_ranges([], [])
        
        assert result["base"]["high"] == 0
        assert result["base"]["mid"] == 0
        assert result["base"]["low"] == 0
        assert result["base"]["unknown"] == 0
        
        assert result["target"]["high"] == 0
        assert result["target"]["mid"] == 0
        assert result["target"]["low"] == 0
        assert result["target"]["unknown"] == 0
        
        # すべて 0 なので変化なし
        assert result["changes"]["high"]["diff"] == 0
        assert result["changes"]["high"]["percent"] == 0.0
    
    def testComparePriceRangesAllUnknown(self):
        """すべて unknown のケース"""
        base_rows = [
            {"UnitPrice": "応相談"},
            {"UnitPrice": None},
            {"UnitPrice": ""},
        ]
        
        target_rows = [
            {"UnitPrice": "要相談"},
            {"UnitPrice": "面談時に提示"},
        ]
        
        result = compare_price_ranges(base_rows, target_rows)
        
        assert result["base"]["high"] == 0
        assert result["base"]["mid"] == 0
        assert result["base"]["low"] == 0
        assert result["base"]["unknown"] == 3
        
        assert result["target"]["high"] == 0
        assert result["target"]["mid"] == 0
        assert result["target"]["low"] == 0
        assert result["target"]["unknown"] == 2
        
        assert result["changes"]["unknown"]["diff"] == -1  # 3 → 2
    
    def testComparePriceRangesMissingColumn(self):
        """価格カラムが存在しないケース"""
        base_rows = [
            {"Title": "案件A"},  # UnitPrice なし
            {"Title": "案件B"},
        ]
        
        target_rows = [
            {"Title": "案件C"},
        ]
        
        result = compare_price_ranges(base_rows, target_rows)
        
        # すべて unknown として扱われる
        assert result["base"]["unknown"] == 2
        assert result["target"]["unknown"] == 1
    
    def testComparePriceRangesCustomColumn(self):
        """カスタム価格カラム名のテスト"""
        base_rows = [
            {"Price": "80万円"},
            {"Price": "60万円"},
        ]
        
        target_rows = [
            {"Price": "90万円"},
        ]
        
        result = compare_price_ranges(base_rows, target_rows, price_column="Price")
        
        assert result["base"]["high"] == 1
        assert result["base"]["mid"] == 1
        assert result["target"]["high"] == 1
        assert result["target"]["mid"] == 0
