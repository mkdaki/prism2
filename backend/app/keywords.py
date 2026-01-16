"""
技術キーワードのマスターリスト（E-2-2-1-2）

PoC段階: ソースコード直書き
本番リリース前: UI機能による管理に移行予定
  - GET /keywords: キーワード一覧取得
  - POST /keywords: キーワード追加
  - DELETE /keywords/{keyword}: キーワード削除
  - 管理画面UI

キーワードリストのメンテナンス:
  1. このファイルを編集
  2. コンテナを再ビルド: docker compose build backend
  3. 再起動: docker compose up -d backend
"""

# 技術キーワード（大文字小文字を区別しないマッチング用）
TECH_KEYWORDS = [
    # プログラミング言語
    "Python",
    "Java",
    "PHP",
    "JavaScript",
    "TypeScript",
    "Ruby",
    "Go",
    "Rust",
    "C#",
    "C++",
    "C",
    "Swift",
    "Kotlin",
    "Scala",
    "Perl",
    "Delphi",
    "VBA",
    
    # フロントエンドフレームワーク・ライブラリ
    "React",
    "Vue.js",
    "Vue",
    "Next.js",
    "Nuxt.js",
    "Angular",
    "Svelte",
    "jQuery",
    
    # バックエンドフレームワーク
    "Django",
    "Flask",
    "FastAPI",
    "Laravel",
    "Rails",
    "Ruby on Rails",
    "Spring",
    "Spring Boot",
    "Express",
    "Express.js",
    "NestJS",
    "ASP.NET",
    ".NET",
    
    # CMS・ECプラットフォーム
    "WordPress",
    "Shopify",
    "Wix",
    "Drupal",
    "Joomla",
    "EC-CUBE",
    "UTAGE",
    
    # クラウド・インフラ
    "AWS",
    "Azure",
    "GCP",
    "Google Cloud",
    "Docker",
    "Kubernetes",
    "Terraform",
    "Ansible",
    "Heroku",
    "Vercel",
    "Netlify",
    
    # データベース
    "MySQL",
    "PostgreSQL",
    "MongoDB",
    "Redis",
    "DynamoDB",
    "Oracle",
    "SQL Server",
    "MariaDB",
    "SQLite",
    "Elasticsearch",
    
    # AI・機械学習
    "AI",
    "機械学習",
    "深層学習",
    "ディープラーニング",
    "ChatGPT",
    "GPT",
    "LLM",
    "生成AI",
    "OpenAI",
    "Gemini",
    "Claude",
    "RAG",
    "Dify",
    "LangChain",
    "TensorFlow",
    "PyTorch",
    
    # モバイル
    "iOS",
    "Android",
    "React Native",
    "Flutter",
    "Xamarin",
    
    # ゲーム開発
    "Unity",
    "UE5",
    "Unreal Engine",
    "Unreal",
    "Godot",
    "Cocos2d",
    
    # その他技術・ツール
    "Git",
    "GitHub",
    "GitLab",
    "Bitbucket",
    "Jenkins",
    "CircleCI",
    "GraphQL",
    "REST API",
    "API",
    "WebSocket",
    "gRPC",
    "Node.js",
    "Deno",
    "Bun",
    "Vite",
    "Webpack",
    "Babel",
    
    # 決済・認証
    "Stripe",
    "PayPal",
    "Auth0",
    "Firebase",
    "Supabase",
    
    # コミュニケーション
    "LINE",
    "Slack",
    "Teams",
    "Discord",
    "Zoom",
    
    # データ処理・分析
    "Excel",
    "Pandas",
    "NumPy",
    "Jupyter",
    "Apache Spark",
    "Tableau",
    "Power BI",
    
    # ブロックチェーン・Web3
    "ブロックチェーン",
    "Blockchain",
    "Web3",
    "NFT",
    "Ethereum",
    "Solidity",
    "Bitcoin",
    
    # その他
    "IoT",
    "AR",
    "VR",
    "XR",
    "メタバース",
    "RPA",
    "UiPath",
    "Salesforce",
    "SAP",
    "Figma",
    "Photoshop",
    "Illustrator",
    "SEO",
    "マーケティング",
    "セキュリティ",
    "DX",
    "アジャイル",
    "Scrum",
    "DevOps",
    "SRE",
    "マイクロサービス",
    "サーバーレス",
    "CI/CD",
    "テスト自動化",
    "E2E",
    "Selenium",
    "Playwright",
    "Puppeteer",
    "スクレイピング",
    "クローリング",
    "せどり",
    "EC",
    "ECサイト",
    "SaaS",
    "BtoB",
    "BtoC",
]
