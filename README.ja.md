<p align="center">
  <a href="README.md">English</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/record-index/main/docs/assets/logo-wide.png" alt="record-index — query the record instead of reading it" width="820">
</p>

# レコードインデックス

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/record-index/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/record-index/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/record-index/"><img src="https://img.shields.io/badge/landing%20page-live-2ea043" alt="Landing page"></a>
</p>

マークダウン形式の意思決定記録を対象とした、管理されたSQLite+FTS5マップ。これにより、セッションは記録全体を読む代わりに、記録に対して**クエリ**を実行できる。そして、そのクエリが指し示した40行のみを読み込むことで、600行すべてをざっと読む必要がなくなる。

**[ランディングページとハンドブック →](https://mcp-tool-shop-org.github.io/record-index/)**

The markdown stays canonical. The index is derived, regenerated on every fold, gated by a
four-leg `verify`, and **wrong by definition the day it is hand-edited**.

## ステータス：抽出済み、テスト済み、まだPyPIには公開されていない

*(このセクションは、2026年8月11日まで「SCAFFOLD ONLY — このリポジトリにはまだツールコードは含まれていない」と記述されていたが、抽出ランディングによってその内容が覆された。そのため、修正を行った。)*

**抽出が完了した。**パッケージは`main`にあり、byte-identityによる検証を経て公開される。facetのツリー内のビルド（19/19）との整合性が確認され、同じコーパス上で**行レベルでの差異はゼロ**である。2つのコンシューマーがこれを使用する。[facet](https://github.com/mcp-tool-shop-org/facet)は、約2,462行のツリー内のコードを宣言とアダプターに置き換え、そのテスト（約140）を通じてパッケージを検証する。もう一つは[armature](https://github.com/mcp-tool-shop-org/armature)で、独自のインデックスを使用して15/15のルールが適用され、47件の判定が行われる。

**パッケージには独自のテストスイートが含まれており、すべての10個のモジュールに対して455件のチェックが行われる。**Python 3.11および3.13でCI環境で実行される。2つのフィクスチャレコードリポジトリを使用してビルドされ、これらのリポジトリは、マーカー、コーパスルート、アークルール、判定語彙、ヘッダー形式など、宣言可能なすべての軸において異なる設定を持つ。そのため、誤った実装があれば、その点が明確になるように設計されている。**依存関係：なし。**標準ライブラリのみ（`sqlite3` + `re` + `json`）を使用し、これは意図的なものであり、偶然ではない。

**4つの既知の欠陥があり、再現され、ツリー内のテストとして`xfail(strict=True)`に記録されている**（隠蔽されていない）。具体的には、`verify()`が診断カウントを2倍にする（ゲート条件には影響しない）、クレームアークパターンは`E`で番号付けされたアークを前提とする、サブルールロケーターは宣言されたヘッダー形式から派生していない、そして4つの宣言フィールドは正直に空にできない。これらの欠陥はいずれも現在の2つのコンシューマーに影響を与えず、すべて次のバージョンで修正される予定である。

**まだPyPIには公開されていない。**`release.yml`は、GitHubリリースが作成されたときにOIDC Trusted Publishingを通じて公開される。プッシュ時には何も公開されない。

## このツールの由来

これは、[`mcp-tool-shop-org/facet`](https://github.com/mcp-tool-shop-org/facet)でビルドおよび強化されたレコードインデックスの抽出である。ここで、以下のすべての規則が定義されている。抽出はフォークではなく、facet独自のルールブックには、4つの名前を持つ1つの関数が5回手動でコピーされており、数か月間名前ベースのgrepでは検出できなかったためである。何千行ものコードを2番目のリポジトリにフォークすることは、そのエラーをさらに3倍にしたことになる。

抽出条件は事前に定義され、測定によって制御される。*インデックスは、2番目のリポジトリが規則を採用した場合に抽出される。* [`mcp-tool-shop-org/armature`](https://github.com/mcp-tool-shop-org/armature)がそのリポジトリである。

## 設計（1つの段落で）

レコードリポジトリは、**ドキュメントの意味を宣言する**。どのファイルにルールが含まれているか、どのヘッダー形式が開くか、判定語彙が何か、どのコーパスを持っているかを定義する。ツールは、**検索の仕組みを提供する**。解析、ランキング、決定性、検証条件などがあり、チューニング値には、そのコーパスと校正された日付が含まれる。規則は、**完全な宣言である**（リポジトリは自身の意味を記述し、他のリポジトリの履歴を省略によって継承することはない）。メカニズムは、**デフォルトにオーバーライドを加えることである**。

すべての語彙は、**認識できなかったものを報告する**。空のテーブルと、6つのアーティファクトをサイレントに破棄したテーブルは、呼び出し元では区別できないが、そのうち正しいのは1つだけである。

## 以前はここに存在していた停止条件とその結末

*(2026年8月11日までは、このセクションで測定された衝突に基づいてビルドが停止されていた。停止条件は現実であり、判定が行われ、ビルドが続行された。削除する代わりに、その過程を残しておくことにした。)*

分類ステップでは、ドキュメントのアークを先頭の`E\d\d`プレフィックスから派生させると、facetに対して**7つのプライマリキーで衝突が発生することが測定された**（`E10-ruling.md`と`E10-offsurface-ruling.md`の両方がアーク`E10`になる）。エクゼキューターは、同じ失敗を記録した名前を持つテストに対してこれを検出し、共同の判定が取り下げられ、再派生され、抽出がゲートを通過して完了した。証拠、覆された回答、およびそれらを置き換えた判定を含む過程は、`armature/docs/dispatches/`（S02アーク）に記録されている。

## ライセンス

MIT — [LICENSE](LICENSE)を参照。
