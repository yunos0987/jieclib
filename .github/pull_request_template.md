## 変更の内容

<!-- 何を、なぜ変えたか。関係する Issue があれば書く。 -->

## 確認したこと

- [ ] `python scripts/run_tests.py --compile-only` が `All checks passed.` で終わった（L1）
- [ ] 追加・変更したテストを jier で実行した結果を書いた（L2）
- [ ] `python scripts/lint.py` が `Lint passed.` で終わった
- [ ] CHANGELOG.md の `[Unreleased]` 節に変更を書いた（利用者に関係しない変更は不要）
- [ ] README.md・CONTRIBUTING.md・AGENTS.md に、必要な追記をした
- [ ] 文字コードは UTF-8 BOM なし、改行は LF

<!--
L3・L4 の節は、CI の pr-body ジョブが書式を確かめる（scripts/check_pr_body.py）。
- L3 は、src/ を変更した PR で必須。
- L4 は、keyence を宣言したファイル（先頭コメントの $ jiecc の行に -t keyence があるファイル。
  ヘッダーのないファイルは、同じモジュールのファイルの宣言）を変更した PR で必須。
「結果」には、合格・不合格・未実施のどれかを書く。
合格・不合格なら「開発環境と版」と「実行したテストファイル」を、未実施なら「未実施の理由」を書く。
必須でない節は、空のままでよい。宛先が main の PR（リリースの取り込み）は検査しない。
-->

## L3 Sysmac Studio のシミュレータでの実行

- 結果:
- 開発環境と版:
- 実行したテストファイル:
- 未実施の理由:

## L4 KV Studio での実行

- 結果:
- 開発環境と版:
- 実行したテストファイル:
- 未実施の理由:
