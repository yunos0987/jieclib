# 変更履歴 / Changelog

このファイルは、3.4.0 以降の変更を記録します。それ以前の変更は、Git のタグ（`v1.2.0` 〜 `v3.2.0`）と GitHub のリリース・Pull Request（https://github.com/yunos0987/jieclib）を参照してください。

## [Unreleased]

### その他 / Other

- `scripts/lint.py` を追加しました。CONTRIBUTING.md と AGENTS.md の規約のうち、ソースを読んで判定できるもの（キーワードなどの小文字、doc プラグマの書き方・引用符・有無、`continue` と `/* */` の禁止、コメントの英語、テストの `// Fact:`）を検査します。既存の警告（日本語のコメント・doc プラグマ 1,139 件、`// Fact:` のないテスト 273 件）は `scripts/lint_baseline.json` に一覧として記録し、一覧にない警告だけを失敗にします。`scripts/test_lint.py` がその単体テストです。
- 規約に合わせて、既存のソースを直しました。動作は変わりません。
  - 大文字のキーワードと真理値（`OR` 2 か所、`TRUE` 2 か所）と、大文字の標準関数の名前（`COS`・`SQRT`・`SIN`・`LN`・`EXP`・`ASIN` の 18 か所）を小文字にしました。
  - doc プラグマの書き方を `(*{doc ...}*)` に揃えました（`{doc ...}`・`{doc: ...}`・`(*{doc: ...}*)` の 49 か所。6 ファイル）。生成される XML の `Documentation` は変わりません。
- Pull Request のテンプレート（`.github/pull_request_template.md`）を追加しました。CI で確かめられない、Sysmac Studio のシミュレータ（L3）と KV Studio（L4）での実行の結果を書く欄があります。
- CI に次のジョブを追加しました。
  - `ci.yml` の `lint`: `scripts/lint.py` とその単体テストを実行します。
  - `pr-checks.yml`（新しい workflow）の `lint-baseline`: Pull Request が `scripts/lint_baseline.json` に項目を足していたら失敗にします。規則を見直す Pull Request は、ラベル `lint-baseline-reset` で比較を省略します。
  - `pr-checks.yml` の `pr-body`: `src/` を変更した Pull Request の本文に L3 の結果が、keyence を宣言したファイルを変更した Pull Request の本文に L4 の結果が書かれていなければ失敗にします（`scripts/check_pr_body.py`）。宛先が `main` の Pull Request は対象外です。
- `scripts/run_tests.py` を直し、拡張しました。
  - 時間切れのときに、jiecc が起動した子のプロセスが残り、`run_tests.py` が終わらなくなる不具合を直しました。jiecc は、起動したプロセスが実際に処理する子のプロセスを起動するため、時間切れのときは、子を含むプロセスの木ごと終了させます。
  - 既定の `--max-cycles` を 100000 から 2000 に下げました。jier は、テストが終わった後も指定した周期数まで回り続けるため、4.0.0 の「既知の問題」の、エラーで止まらない 29 ファイルは時間切れになっていました。2000 周期では、そのうち 28 ファイルが合格します。残りの `test/string_lib/test_string_lib.iec` は、jier の `find` の振る舞いのため終わりません。測定の結果は `docs/jier_cycles.md` にあります。
  - `[========] Running N tests.` の数と、実行したテストの数が合わないとき（周期数が足りないとき）も、失敗と判定するようにしました。
  - `--output-dir DIR`（生成した XML を残す）と `--paths-from FILE`（対象のパスと周期数をファイルから読む）を追加しました。
- jier で必ず通すテストファイルの一覧 `scripts/jier_required.txt` と、CI の `run-required` ジョブを追加しました。一覧のテストが jier で失敗すると、CI が失敗します。新しく追加するテストファイルは、この一覧に載せます。
- この節（`[Unreleased]`）を設けました。変更は Pull Request ごとにこの節へ書き、リリースのコミットで見出しを `[X.Y.Z] - 日付` に置き換えます。

## [4.0.0] - 2026-11-01

### 互換性に影響する変更 / Breaking changes

- 必要な Jiecc を 5.14 以降（`test/` は 8.0.0 以降）から 9.2.0 以降に変更しました。Jiecc 9.2.0 では、POU の本体直下に ST の文を直接書けるようになったため、`{st}` / `{end}`（マクロ定義内の `${st$}` / `${end$}` を含む）の囲みを、`src/` と `test/` のすべてのソースから取り除きました。
- Jiecc 9.2.0 未満では、`src/sys.iec` などの `{#error}` で前処理が止まります（`JiecLib requires Jiecc 9.2.0 or later.`）。
- GitHub Actions の CI は最新リリースの Jiecc を取得して実行する方式のままです（9.2.0 以降が必要です）。

### 既知の問題 / Known issues

- jier（`jiecc --run`）でテストを実行すると、`test/` の 83 ファイルが失敗します。幅なしの `shl` / `shr` は `UNDEFINED_SYMBOL` で止まり、dint の `max` / `min` は `cannot marshal Python int ... LREAL` で止まります。Jiecc 8.0.0 でも同じ結果になるため、今回の変更による退行ではありません。PLC ベンダーの環境向けのコンパイルには影響しません。このため、CI の run ジョブが失敗しても、ライブラリが壊れているとは限りません。Jiecc の型推論が完成するまで、対応を保留しています。

### その他 / Other

- サブモジュール `vendor/jiecunit` を JiecUnit v5.0.0 から v6.0.0 に更新しました。JiecUnit v6.0.0 は `{st}` / `{end}` を使わず、Jiecc 9.2.0 以降を必要とします。JiecLib の必要な Jiecc のバージョンと揃います。README.md の記述も v6.0.0 に更新しました。

## [3.4.0] - 2026-10-18

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

- `VERSION` ファイルを追加しました。JiecLib のバージョン（`MAJOR.MINOR.PATCH`）を 1 行で記録します。リリースのコミット（`release vX.Y.Z`）でだけ更新します。
- サブモジュール `vendor/jiecunit` を JiecUnit v4.2.0 から v5.0.0 に更新しました。v4.2.0 では jier の実行が `JiecTest_currentCycle` の `UNDEFINED_SYMBOL` で止まります。JiecUnit v5.0.0 のテストには Jiecc 8.0.0 以降が必要なため、README.md の必要環境に追記しました。
- 貢献者向けの文書を整理しました。
  - `CODING_RULES.md` の内容を、新しく追加した `CONTRIBUTING.md` に移し、`CODING_RULES.md` を削除しました。あわせて、規約中のコード例などの明らかな誤記を直しました。
  - AI エージェント向けのルールを `AGENTS.md` にまとめました。`CLAUDE.md` は `AGENTS.md` を読み込むだけになりました。
  - `CHANGELOG.md` と `SECURITY.md` を追加しました。
- `scripts/run_tests.py` を追加しました。`src/` のライブラリと `test/` のテストを、各ファイルの先頭コメントに書かれたターゲットでコンパイルし、jier（`jiecc --run`）でテストを実行して合否を判定します。
- GitHub Actions の CI（`.github/workflows/ci.yml`）を追加しました。`main` への push と、`main`・`develop` を宛先とする Pull Request（および手動実行）で、次を行います。
  - 追跡しているテキストファイルが UTF-8 BOM なし・LF であることの確認。
  - Windows と Linux のそれぞれで最新の Jiecc（Windows は https://www.graviness.com/iec_61131-3/jiecc.zip 、Linux は https://www.graviness.com/iec_61131-3/jiecc.tgz ）を取得し、すべてのライブラリとテストをコンパイル。
  - jier によるテストの実行。現在は、失敗しても CI を失敗にしません。
- `.github/dependabot.yml` を追加し、CI で使う actions の更新を Dependabot で確認するようにしました。
- README.md のテスト方法を、`scripts/run_tests.py` を使う手順に更新しました。
