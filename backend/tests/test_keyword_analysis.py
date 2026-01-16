"""
キーワード分析機能のテスト（E-2-2-1-2）
"""

import pytest
from app.analysis import extract_keywords_from_titles, compare_keywords


class TestExtractKeywordsFromTitles:
    """キーワード抽出関数のテスト"""
    
    def testExtractKeywordsSuccess(self):
        """正常系: キーワードが正しく抽出される"""
        rows = [
            {"Title": "Pythonエンジニア募集"},
            {"Title": "Python/Django開発者"},
            {"Title": "AI・機械学習案件"},
            {"Title": "PHP Laravel案件"},
            {"Title": "Next.js フロントエンド"},
        ]
        
        result = extract_keywords_from_titles(rows)
        
        # Pythonが2回出現
        assert result.get("Python") == 2
        # AIが1回出現
        assert result.get("AI") == 1
        # PHPが1回出現
        assert result.get("PHP") == 1
        # Laravelが1回出現
        assert result.get("Laravel") == 1
        # Next.jsが1回出現
        assert result.get("Next.js") == 1
    
    def testExtractKeywordsCaseInsensitive(self):
        """大文字小文字を区別しない"""
        rows = [
            {"Title": "python開発"},
            {"Title": "PYTHON案件"},
            {"Title": "Python募集"},
        ]
        
        result = extract_keywords_from_titles(rows)
        
        # すべて"Python"としてカウント
        assert result.get("Python") == 3
    
    def testExtractKeywordsMultipleInOneTitle(self):
        """1つのTitleに複数のキーワードがある場合"""
        rows = [
            {"Title": "Python/Django/PostgreSQL開発"},
        ]
        
        result = extract_keywords_from_titles(rows)
        
        # すべて1回ずつカウント
        assert result.get("Python") == 1
        assert result.get("Django") == 1
        assert result.get("PostgreSQL") == 1
    
    def testExtractKeywordsSameKeywordMultipleTimes(self):
        """同じキーワードが1つのTitleに複数回出現する場合（1回としてカウント）"""
        rows = [
            {"Title": "Python Python Python開発"},
        ]
        
        result = extract_keywords_from_titles(rows)
        
        # 1回としてカウント
        assert result.get("Python") == 1
    
    def testExtractKeywordsEmptyTitle(self):
        """空のTitleの場合"""
        rows = [
            {"Title": ""},
            {"Title": None},
            {},
        ]
        
        result = extract_keywords_from_titles(rows)
        
        # 何もカウントされない
        assert len(result) == 0
    
    def testExtractKeywordsNoMatch(self):
        """キーワードにマッチしないTitleの場合"""
        rows = [
            {"Title": "一般事務募集"},
            {"Title": "営業職募集"},
        ]
        
        result = extract_keywords_from_titles(rows)
        
        # 何もカウントされない
        assert len(result) == 0
    
    def testExtractKeywordsPartialMatch(self):
        """部分一致でマッチング"""
        rows = [
            {"Title": "【急募】Pythonエンジニア募集中！"},
            {"Title": "TypeScriptができる方"},
        ]
        
        result = extract_keywords_from_titles(rows)
        
        assert result.get("Python") == 1
        assert result.get("TypeScript") == 1


class TestCompareKeywords:
    """キーワード比較関数のテスト"""
    
    def testCompareKeywordsIncreased(self):
        """増加キーワードの検出"""
        base_rows = [
            {"Title": "Python案件"},
            {"Title": "Python開発"},
            {"Title": "PHP案件"},
        ]
        
        target_rows = [
            {"Title": "Python案件"},
            {"Title": "Python開発"},
            {"Title": "Python募集"},
            {"Title": "Python/Django"},
            {"Title": "Python/Flask"},
        ]
        
        result = compare_keywords(base_rows, target_rows, top_n=5)
        
        # base_total/target_totalの確認
        assert result["base_total"] == 3
        assert result["target_total"] == 5
        
        # Pythonが増加（2 → 5）
        increased = result["increased_keywords"]
        python_change = next((k for k in increased if k["keyword"] == "Python"), None)
        assert python_change is not None
        assert python_change["base"] == 2
        assert python_change["target"] == 5
        assert python_change["diff"] == 3
    
    def testCompareKeywordsDecreased(self):
        """減少キーワードの検出"""
        base_rows = [
            {"Title": "PHP案件"},
            {"Title": "PHP開発"},
            {"Title": "PHP/Laravel"},
        ]
        
        target_rows = [
            {"Title": "PHP案件"},
        ]
        
        result = compare_keywords(base_rows, target_rows, top_n=5)
        
        # PHPが減少（3 → 1）
        decreased = result["decreased_keywords"]
        php_change = next((k for k in decreased if k["keyword"] == "PHP"), None)
        assert php_change is not None
        assert php_change["base"] == 3
        assert php_change["target"] == 1
        assert php_change["diff"] == -2
    
    def testCompareKeywordsNew(self):
        """新規出現キーワードの検出"""
        base_rows = [
            {"Title": "Python案件"},
        ]
        
        target_rows = [
            {"Title": "Python案件"},
            {"Title": "ChatGPT案件"},
            {"Title": "LLM開発"},
        ]
        
        result = compare_keywords(base_rows, target_rows, top_n=5)
        
        # 新規キーワード
        new_keywords = result["new_keywords"]
        assert "ChatGPT" in new_keywords
        assert "LLM" in new_keywords
    
    def testCompareKeywordsDisappeared(self):
        """消失キーワードの検出"""
        base_rows = [
            {"Title": "Python案件"},
            {"Title": "PHP開発"},
        ]
        
        target_rows = [
            {"Title": "Python案件"},
        ]
        
        result = compare_keywords(base_rows, target_rows, top_n=5)
        
        # 消失キーワード
        disappeared = result["disappeared_keywords"]
        assert "PHP" in disappeared
    
    def testCompareKeywordsEmpty(self):
        """空データの場合"""
        result = compare_keywords([], [], top_n=5)
        
        assert result["base_total"] == 0
        assert result["target_total"] == 0
        assert len(result["increased_keywords"]) == 0
        assert len(result["decreased_keywords"]) == 0
        assert len(result["new_keywords"]) == 0
        assert len(result["disappeared_keywords"]) == 0
    
    def testCompareKeywordsTopN(self):
        """top_nパラメータの動作確認"""
        base_rows = [{"Title": f"Keyword{i}"} for i in range(20)]
        target_rows = [{"Title": f"Keyword{i} Keyword{i}"} for i in range(20)]
        
        result = compare_keywords(base_rows, target_rows, top_n=3)
        
        # top_n=3なので、最大3件まで
        assert len(result["increased_keywords"]) <= 3
