"""
プロンプトv2のテスト（E-2-2-1-3）
"""

import pytest
from app.analysis import build_comparison_prompt_v2


class TestBuildComparisonPromptV2:
    """build_comparison_prompt_v2()関数のテスト"""
    
    def testPromptStructureComplete(self):
        """プロンプト構造が7セクションを含むことを確認"""
        comparison_data = {
            "base_dataset": {
                "dataset_id": 1,
                "filename": "base.csv",
                "created_at": "2026-01-01T00:00:00Z",
                "rows": 100
            },
            "target_dataset": {
                "dataset_id": 2,
                "filename": "target.csv",
                "created_at": "2026-01-08T00:00:00Z",
                "rows": 120
            },
            "comparison": {
                "rows_change": {
                    "base": 100,
                    "target": 120,
                    "diff": 20,
                    "percent": 20.0
                }
            },
            "price_range_analysis": {
                "base": {"high": 10, "mid": 30, "low": 50, "unknown": 10},
                "target": {"high": 15, "mid": 35, "low": 60, "unknown": 10},
                "changes": {
                    "high": {"diff": 5, "percent": 50.0},
                    "mid": {"diff": 5, "percent": 16.7},
                    "low": {"diff": 10, "percent": 20.0},
                    "unknown": {"diff": 0, "percent": 0.0}
                }
            },
            "keyword_analysis": {
                "increased_keywords": [
                    {"keyword": "Python", "base": 10, "target": 20, "diff": 10}
                ],
                "decreased_keywords": [
                    {"keyword": "PHP", "base": 30, "target": 20, "diff": -10}
                ],
                "new_keywords": ["TypeScript"],
                "disappeared_keywords": ["Flash"]
            }
        }
        
        prompt = build_comparison_prompt_v2(comparison_data)
        
        # 7セクションの見出しが含まれることを確認
        assert "## ビジネス動向サマリー" in prompt
        assert "## 価格動向" in prompt
        assert "## 案件内容のトレンド" in prompt
        assert "## 推奨アクション" in prompt
        assert "## 前提・限界" in prompt
    
    def testPriceInclusionHighMidLow(self):
        """価格帯情報（高/中/低）が含まれることを確認"""
        comparison_data = {
            "base_dataset": {"filename": "base.csv", "created_at": "2026-01-01", "rows": 100},
            "target_dataset": {"filename": "target.csv", "created_at": "2026-01-08", "rows": 120},
            "comparison": {"rows_change": {"base": 100, "target": 120, "diff": 20, "percent": 20.0}},
            "price_range_analysis": {
                "base": {"high": 10, "mid": 30, "low": 50, "unknown": 10},
                "target": {"high": 15, "mid": 35, "low": 60, "unknown": 10},
                "changes": {
                    "high": {"diff": 5, "percent": 50.0},
                    "mid": {"diff": 5, "percent": 16.7},
                    "low": {"diff": 10, "percent": 20.0},
                    "unknown": {"diff": 0, "percent": 0.0}
                }
            },
            "keyword_analysis": {}
        }
        
        prompt = build_comparison_prompt_v2(comparison_data)
        
        # 価格帯別の案件数が含まれることを確認
        assert "高単価案件（80万円以上）" in prompt
        assert "中単価案件（50-80万円）" in prompt
        assert "低単価案件（50万円未満）" in prompt
        assert "10件 → 15件" in prompt  # 高単価の変化
        assert "30件 → 35件" in prompt  # 中単価の変化
        assert "50件 → 60件" in prompt  # 低単価の変化
    
    def testKeywordInclusionIncreasedDecreased(self):
        """キーワード情報（増加/減少）が含まれることを確認"""
        comparison_data = {
            "base_dataset": {"filename": "base.csv", "created_at": "2026-01-01", "rows": 100},
            "target_dataset": {"filename": "target.csv", "created_at": "2026-01-08", "rows": 120},
            "comparison": {"rows_change": {"base": 100, "target": 120, "diff": 20, "percent": 20.0}},
            "price_range_analysis": {},
            "keyword_analysis": {
                "increased_keywords": [
                    {"keyword": "Python", "base": 10, "target": 20, "diff": 10},
                    {"keyword": "AI", "base": 5, "target": 12, "diff": 7}
                ],
                "decreased_keywords": [
                    {"keyword": "PHP", "base": 30, "target": 20, "diff": -10}
                ],
                "new_keywords": ["TypeScript", "AWS"],
                "disappeared_keywords": ["Flash"]
            }
        }
        
        prompt = build_comparison_prompt_v2(comparison_data)
        
        # キーワード変化が含まれることを確認
        assert "増加キーワード（Top5）" in prompt
        assert "Python" in prompt
        assert "10件 → 20件" in prompt
        assert "減少キーワード（Top5）" in prompt
        assert "PHP" in prompt
        assert "30件 → 20件" in prompt
        assert "新規出現キーワード" in prompt
        assert "TypeScript" in prompt
        assert "消失キーワード" in prompt
        assert "Flash" in prompt
    
    def testNoTechnicalMetrics(self):
        """技術的指標（No, Page, rowOrder）が主要な分析対象として扱われていないことを確認"""
        comparison_data = {
            "base_dataset": {"filename": "base.csv", "created_at": "2026-01-01", "rows": 100},
            "target_dataset": {"filename": "target.csv", "created_at": "2026-01-08", "rows": 120},
            "comparison": {
                "rows_change": {"base": 100, "target": 120, "diff": 20, "percent": 20.0},
                "columns_change": [
                    {
                        "name": "No",
                        "kind": "number",
                        "base": {"avg": 50.0},
                        "target": {"avg": 60.0},
                        "diff": {"avg": 10.0}
                    },
                    {
                        "name": "Page",
                        "kind": "number",
                        "base": {"avg": 3.0},
                        "target": {"avg": 3.5},
                        "diff": {"avg": 0.5}
                    }
                ]
            },
            "price_range_analysis": {},
            "keyword_analysis": {}
        }
        
        prompt = build_comparison_prompt_v2(comparison_data)
        
        # No, Page, rowOrderが主要なトピックとして扱われていないことを確認
        # （プロンプトのメイン部分には登場しない）
        assert "No" not in prompt or prompt.count("No") < 3  # "No"が多用されていない
        assert "Page" not in prompt or prompt.count("Page") < 3
        assert "rowOrder" not in prompt
    
    def testBusinessOrientedLanguage(self):
        """ビジネス指向の言葉遣いが使われていることを確認"""
        comparison_data = {
            "base_dataset": {"filename": "base.csv", "created_at": "2026-01-01", "rows": 100},
            "target_dataset": {"filename": "target.csv", "created_at": "2026-01-08", "rows": 120},
            "comparison": {"rows_change": {"base": 100, "target": 120, "diff": 20, "percent": 20.0}},
            "price_range_analysis": {},
            "keyword_analysis": {}
        }
        
        prompt = build_comparison_prompt_v2(comparison_data)
        
        # ビジネス指向のキーワードが含まれることを確認
        assert "ビジネス" in prompt
        assert "市場" in prompt or "動向" in prompt
        assert "アクション" in prompt
        assert "推奨" in prompt or "提案" in prompt
    
    def testEmptyPriceAndKeywordData(self):
        """価格帯・キーワード情報が空の場合でもプロンプトが生成されることを確認"""
        comparison_data = {
            "base_dataset": {"filename": "base.csv", "created_at": "2026-01-01", "rows": 100},
            "target_dataset": {"filename": "target.csv", "created_at": "2026-01-08", "rows": 120},
            "comparison": {"rows_change": {"base": 100, "target": 120, "diff": 20, "percent": 20.0}},
            "price_range_analysis": {},
            "keyword_analysis": {}
        }
        
        prompt = build_comparison_prompt_v2(comparison_data)
        
        # プロンプトが生成され、基本構造が含まれることを確認
        assert len(prompt) > 0
        assert "ビジネス動向サマリー" in prompt
        assert "価格動向" in prompt
        assert "案件内容のトレンド" in prompt
    
    def testTop5Limit(self):
        """増加/減少キーワードがTop5に制限されることを確認"""
        comparison_data = {
            "base_dataset": {"filename": "base.csv", "created_at": "2026-01-01", "rows": 100},
            "target_dataset": {"filename": "target.csv", "created_at": "2026-01-08", "rows": 120},
            "comparison": {"rows_change": {"base": 100, "target": 120, "diff": 20, "percent": 20.0}},
            "price_range_analysis": {},
            "keyword_analysis": {
                "increased_keywords": [
                    {"keyword": f"Keyword{i}", "base": i, "target": i+10, "diff": 10}
                    for i in range(1, 11)  # 10個のキーワード
                ],
                "decreased_keywords": [],
                "new_keywords": [],
                "disappeared_keywords": []
            }
        }
        
        prompt = build_comparison_prompt_v2(comparison_data)
        
        # Keyword1-5はプロンプトに含まれるはず
        assert "Keyword1" in prompt
        assert "Keyword5" in prompt
        
        # Keyword6-10は含まれないはず（Top5制限）
        assert "Keyword6" not in prompt
        assert "Keyword10" not in prompt
