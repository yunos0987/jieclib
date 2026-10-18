# 変更履歴 / Changelog

このファイルは、次のリリース以降の変更を記録します。それ以前の変更は、Git のタグ（`v1.2.0` 〜 `v3.2.0`）と GitHub のリリース・Pull Request（https://github.com/yunos0987/jieclib）を参照してください。

## Unreleased

### 修正 / Fixed

- jier（`jiecc --run`）は、関数を定義より前で呼び出すと `UNDEFINED_SYMBOL` で止まります。前方宣言は PLC ベンダーが対応していないため使わず、呼び出される関数を呼び出し元より前に置くように定義の順序を入れ替えました。本体とシグネチャは変えていません。移動した POU は次のとおりです。
  - `src/stats/descriptive/variance.iec`: `Stats_variance_ddof` を `Stats_variance` の前へ。
  - `src/stats/distributions/core/special_functions.iec`: `Stats_beta_continued_fraction` を `Stats_beta_incomplete` の前へ。
  - `src/container/linkedhashmap/linkedhashmap_template.iec`: `LinkedHashMap_copy` を `LinkedHashMap_upsert` の後へ。
  - `src/hash/crc32.iec`: `CRC32_string` を `CRC32_bytes` の後へ。
  - `src/hash/md5.iec`: `MD5_string` を `MD5_bytes` の後へ。
  - `src/hash/sha1.iec`: `SHA1_string` を `SHA1_bytes` の後へ。
  - `src/hash/sha256.iec`: `SHA256_string` を `SHA256_bytes` の後へ。
  - `src/hash/sha512.iec`: `SHA512_string` を `SHA512_bytes` の後へ。
- `test/array/test_array.iec` に `{#include <array/array.iec>}` を戻しました。コミット 81990e9 で消えていたため、マクロと関数を include より前で使っていました。

### その他 / Other

- サブモジュール `vendor/jiecunit` を JiecUnit v4.2.0 から v5.0.0 に更新しました。v4.2.0 では jier の実行が `JiecTest_currentCycle` の `UNDEFINED_SYMBOL` で止まります。JiecUnit v5.0.0 のテストには Jiecc 8.0.0 以降が必要なため、README.md の必要環境に追記しました。
- 貢献者向けの文書を整理しました。
  - `CODING_RULES.md` の内容を、新しく追加した `CONTRIBUTING.md` に移し、`CODING_RULES.md` を削除しました。あわせて、規約中のコード例などの明らかな誤記を直しました。
  - AI エージェント向けのルールを `AGENTS.md` にまとめました。`CLAUDE.md` は `AGENTS.md` を読み込むだけになりました。
  - `CHANGELOG.md` と `SECURITY.md` を追加しました。
- `scripts/run_tests.py` を追加しました。`src/` のライブラリと `test/` のテストを、各ファイルの先頭コメントに書かれたターゲットでコンパイルし、jier（`jiecc --run`）でテストを実行して合否を判定します。
- GitHub Actions の CI（`.github/workflows/ci.yml`）を追加しました。`main` と `develop` への push と Pull Request で、次を行います。
  - 追跡しているテキストファイルが UTF-8 BOM なし・LF であることの確認。
  - Windows と Linux のそれぞれで最新の Jiecc（Windows は https://www.graviness.com/iec_61131-3/jiecc.zip 、Linux は https://www.graviness.com/iec_61131-3/jiecc.tgz ）を取得し、すべてのライブラリとテストをコンパイル。
  - jier によるテストの実行。現在は、失敗しても CI を失敗にしません。
- `.github/dependabot.yml` を追加し、CI で使う actions の更新を Dependabot で確認するようにしました。
- README.md のテスト方法を、`scripts/run_tests.py` を使う手順に更新しました。
