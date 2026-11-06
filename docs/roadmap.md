# JiecLib 改善計画（v4.0.0 以降）

## 結論

v4.0.0 の時点でリポジトリを見直し、8 項目（No. 3・4・5・6・7・11・12・13）を 15 本の PR に分けて進める。先に検査とテストの土台（フェーズ 1）を作り、その上に機能と文書を足す（フェーズ 2・3）。

| フェーズ | PR | 項目 | 内容 | 依存 | 版 |
|---|---|---|---|---|---|
| 1 | PR-1 | 13 | `scripts/lint.py`（ソースを読む規則）、CI の `lint` ジョブ、CHANGELOG.md の `[Unreleased]` 節、PR のテンプレートとその検査 | なし（最初にマージする） | 4.1.0 |
| 1 | PR-2 | 12・13・3 | `run_tests.py` の時間切れの不具合の修正と拡張（`--output-dir`・`--paths-from`・jier の周期数）、jier で必ず通すテストの CI ジョブ | PR-1 | 4.1.0 |
| 1 | PR-3 | 13 | lint の XML を読む規則（名前・型の制約） | PR-1・PR-2 | 4.1.0 |
| 1 | PR-4 | 3 | `scripts/pou_inventory.py`（テストのない POU の一覧と CI の検査） | PR-3 | 4.1.0 |
| 1 | PR-5 | 3 | `Math_floor` の大きな値の不具合の修正 | PR-2 | 4.1.0 |
| 1 | PR-6 | 3 | `TEST_M` の動作の確認、乱数の分布のテスト、`nextPoisson` の λ の上限 | PR-2 | 4.1.0 |
| 1 | PR-7 | 3 | テストのない 23 個（PR-4 の棚卸しで 28 個）の POU のテスト（モジュールごとに分割してよい） | PR-4 | 4.1.0 |
| 2 | PR-8 | 4 | math の関数の追加（最初に NaN・無限大の調査） | PR-5 | 4.1.0 |
| 2 | PR-9 | 6 | CRC16 とチェックサム | PR-2 | 4.1.0 |
| 2 | PR-10 | 7 | ターゲットの宣言の整理と、README.md の対応表 | PR-1 | 4.1.0 |
| 3 | PR-11 | 11 | `samples/`（利用例）と、そのコンパイル・lint | PR-1・PR-9 | 4.2.0 |
| 3 | PR-12 | 5 | `src/signal/`（信号処理） | PR-6・PR-8・PR-11 | 4.2.0 |
| 3 | PR-13 | 5 | `src/interp/`（補間テーブル） | PR-8 | 4.2.0 |
| 3 | PR-14 | 5 | `src/control/`（PID・ランプ） | PR-12（と D-6 の判断） | 4.2.0 |
| 3 | PR-15 | 12 | Release に XML を添付する workflow | PR-2 | 4.2.0 |

PR-1 は最初にマージする。CHANGELOG.md の `[Unreleased]` 節、PR のテンプレート、lint の基準値を作るので、ほかのすべての PR がこれを前提にする（表の依存の「PR-1」は、この前提を含む）。

作者の判断が要る事項は 13 件ある（6 章。推奨案付き）。そのうち、**着手の前に判断が要る**のは D-6（PID を提供するか。PR-14）の 1 件だけである。D-7（doc プラグマの書き方）と D-12（大文字にしない語の範囲）は、推奨案のとおりに決まった（6 章）。ほかは推奨案で進め、マージの前か、後の PR で変えられる。

この計画の対象外にした項目は次の 3 つ。jier の既存の run ジョブ（全テスト）の必須化、CI の Jiecc の版の固定、名前の接頭辞の統一。ただし、新しく追加するテストだけは jier で必ず通す（1.2 節・PR-2）。

## 1. 前提と方針

### 1.1 共通の方針

- 規約は CONTRIBUTING.md と AGENTS.md に従う。新しい POU は `eno` でエラーを通知し、POU・引数・型に doc プラグマを書く。テストは `TEST_S`（複数の周期にわたるものは `TEST_M`）に、1 関数の事実をまとめる。
- 新しいコードのコメントと doc プラグマは、CONTRIBUTING.md「コーディングスタイル」のとおり英語で書く（既存の日本語の扱いは D-10）。
- PR は `develop` に出し、`develop` を `main` にマージする。版は `release vX.Y.Z` のコミットでだけ上げる（CONTRIBUTING.md「バージョン管理」）。
- 追加・変更は、PR ごとに CHANGELOG.md の `[Unreleased]` 節に書く。この節は PR-1 で作り、リリースのコミットで `[X.Y.Z] - 日付` に置き換える（CONTRIBUTING.md の「変更中の節」にあたる）。
- 新しい関数の名前は、既存のモジュールの接頭辞（`Math_`・`CRC32_` など）に合わせる。新しいモジュールは `Signal_`・`Interp_`・`Control_` を使う。
- 新しいコードの引数・変数・メンバーの名前は、CONTRIBUTING.md の命名規則を守る（1 文字の名前を使わないなど）。既存の公開 API の引数名（`Math_floor` の `x` など）は、名前付きの呼び出し（`Math_floor(x:=2.7)`）を壊すため変えない。
- 新しく追加するファイルのヘッダーは、omron だけを宣言する。keyence などは、そのターゲットの開発環境で確かめた後に追加する（3.6 節の「宣言」の意味）。

### 1.2 検証の段階

| 段階 | 内容 | 方法 | 必須か |
|---|---|---|---|
| L1 | コンパイル | `python scripts/run_tests.py --compile-only`（ヘッダーで宣言した全ターゲット） | 全 PR で必須（CI） |
| L2 | jier での実行 | `python scripts/run_tests.py --run-only <テスト>` | 新しく追加したテストファイルは必須。`scripts/jier_required.txt` に載せ、CI の `run-required` ジョブ（PR-2）で必ず通す。既存のテストファイルに事実を足すときは、新しいファイルに分けて載せる。分けられないときは、そのファイルの jier の出力（集計行まで）を PR に貼る。jier で通らないファイル（2.3 節）なら、L3 の結果で代え、その旨を PR に書く |
| L3 | Sysmac Studio のシミュレータでの実行 | README.md「JiecLibのテスト方法」の手順 | `src/` を変更した PR は必須 |
| L4 | KV Studio での実行 | `vendor/jiecunit/README.md` の KV Studio の手順 | keyence を宣言したファイルを変更した PR は必須 |

- L3・L4 は CI で確かめられないため、結果を PR の本文に、PR のテンプレート（`.github/pull_request_template.md`、PR-1 で追加）の欄で残す。欄は「開発環境と版・実行したテストファイル・結果（合格 / 不合格 / 未実施）」。未実施のときは理由を書き、README.md のターゲットの表（PR-10）では「未確認」のままにする。
- テンプレートの欄は、空のままでも PR を作れる。そこで PR-1 で `pr-body` ジョブ（`pull_request` の event）を追加し、`src/` を変更した PR の本文に L3 の結果が、keyence を宣言したファイルを変更した PR の本文に L4 の結果が（それぞれ合格 / 不合格 / 未実施のどれか。未実施なら理由）書かれていなければ失敗にする。`develop` から `main` へのリリースの取り込みの PR（宛先が `main`）は、個々の PR で記録済みなので対象外にする。検査できるのは書式だけで、内容が本当かは人のレビューで確かめる。
- 新しいコードでは、jier が対応していない書き方（幅を書かない `shl` / `shr`、dint に対する `max` / `min`）を使わない。既存の 83 ファイルのエラー（CHANGELOG.md 4.0.0「既知の問題」）は、この計画では直さない。残りの 29 ファイルの時間切れ（2.3 節）は、PR-2 の周期数の見直しで解消を図る。
- jier はテストが終わった後も、`--max-cycles` で指定した周期数まで回り続ける（2.3 節）。そのため、jier の実行時間は周期数でほぼ決まる。新しいテストは、必要な周期数を `scripts/jier_required.txt` に書き（PR-2）、CI の `--timeout 300`（1 ファイルあたりの秒数）に収める。

### 1.3 PR の完了の条件（全 PR 共通）

1. L1 が通り、`python scripts/lint.py` がエラー 0 件で、警告が基準値（`scripts/lint_baseline.json`）の一覧にないものを含まない（PR-1 の後）。
2. 追加したテストファイルが `scripts/jier_required.txt` に載り、CI の `run-required` ジョブが通る（PR-2 の後）。`src/` を変更した PR は L3 の欄が、keyence を宣言したファイルを変更した PR は L4 の欄も、PR のテンプレートで埋まっていて、`pr-body` ジョブが通る。
3. README.md・CONTRIBUTING.md・AGENTS.md・CHANGELOG.md に、必要な追記がある。
4. 文字コードは UTF-8 BOM なし、改行は LF（CI の `format` ジョブ）。

## 2. 実測した現状

2026-11-05 に、Windows 11 と Jiecc 9.2.0 で、`main`（`1892ca9`）を対象に調べた。

### 2.1 ファイルの数

- `src/` の `.iec` は 126 ファイルある。うち、ヘッダーに `$ jiecc` の行がある（`run_tests.py` がコンパイルする）エントリファイルは 97 ファイル。
- `test/` の `.iec` は 139 ファイルある。うち、`DEFINE_CONFIGURATION` を含む（テストとして実行する）ファイルは 112 ファイル。`TEST_S` は 494 個あり、`TEST_M` は 1 個もない。

### 2.2 ターゲット

- `src/` の 97 ファイルすべてが、omron・keyence・mitsubishi・codesys の 4 ターゲットでコンパイルを通る（エラー 0 件、警告 0 件）。つまり、jiecc のコンパイルが通ることは、ベンダーの環境で使えることを意味しない。ベンダーごとの制約（CONTRIBUTING.md「命名規則」の、キーエンス環境で 1 文字の名前を使えない、など）を jiecc は検査しない。
- ヘッダーで宣言しているターゲットは、ソースとテストで食い違っている。

  | 対象 | ソースのヘッダー | テストのヘッダー |
  |---|---|---|
  | array | `array.iec` と `sort.iec` は keyence と omron、残り 8 ファイルは omron | 9 ファイルとも omron |
  | math | 2 ファイルとも omron | `test_floor` と `test_atan2` は keyence と omron、`test_math` は omron |
  | container | ヘッダーなし（テンプレートのみ） | 12 ファイルとも keyence と omron |
  | random | 4 ファイル中 3 ファイル（lfsr32 以外）は keyence と omron | 5 ファイル中 3 ファイルは keyence と omron |
  | string_lib | 3 ファイルとも keyence と omron | keyence と omron |
  | `src/` 直下（`sys.iec`・`sys_conv.iec` など） | ヘッダーなし | `test/test_sys.iec` と `test/test_sys_conv.iec` は keyence と omron |
  | 上記以外のモジュール | omron | omron |

- mitsubishi を宣言したファイルは 1 つもない。`src/sys.iec` に「Mitsubishi は完全には対応しない（特に関数の `var_in_out`）」とあり、`src/sys_conv.iec` の `_MITSUBISHI` の分岐は `// TODO:` のまま。`src/sys_config.iec` には `_CODESYS` の分岐もある。

### 2.3 jiecc の挙動で計画に影響するもの

- `jiecc --preprocess-only` は `-o` を無視して標準出力に書く。Windows では標準出力のエンコーディングが cp932 になるため、cp932 で表せない文字（`≈`・`²`・`–` など）を含むファイルは、`'cp932' codec can't encode character` のエラーで必ず失敗する。`PYTHONUTF8=1` と `PYTHONIOENCODING=utf-8` では回避できなかった。コンパイル（`-o` で XML を出力）はこの問題が起きない。このため、lint と POU の棚卸しは、前処理の出力ではなく、コンパイルした XML を読んで行う。
- コンパイルした XML（名前空間 `www.iec.ch/public/TC65SC65BWG7TF10`）には、POU（`Function` / `FunctionBlock` / `Program`）、変数（`Variable`）、構造体のメンバー（`DataTypeDecl` の下の `Member`）、可変長配列（`VariableLength`）、ST の本体（`ST`）が入る。POU を定義したソースのファイル名は入らない。include したファイルの POU（`sys.iec` の `Console_*` など）は、それを include したすべての XML に入る。
- PP29（doc プラグマの引用符）は、閉じていない引用符（例: `doesn't`）でだけ警告が出る。`'='` のように対になっていれば出ない。jiepp は doc プラグマの中の `'` と `"` の両方を文字列の始まりとして読み、文字列の中では `$` が次の 1 文字をエスケープする。文字列の外の `$'` はエスケープにならない（`$27` と書く）。警告なので、コンパイルは通る。doc プラグマの中の閉じていない `/*` は、エラー PP20 でコンパイルが止まる（PR-1 の実装時に確かめた）。
- AGENTS.md の PP30 の例（`//   {#define NAME(...)`）は、Jiecc 9.2.0 ではエラー PP23 になり、コンパイルが止まる。L1 で必ず検出できるので、lint の規則にはしない。
- jier で全 112 のテストファイルを実行すると（`run_tests.py --timeout 600`。`--max-cycles` は既定の 100000）、83 ファイルが CHANGELOG.md の記載どおりのエラーで止まった（`cannot marshal Python int ... LREAL` が 62、`shr` の `UNDEFINED_SYMBOL` が 15、`shl` が 6）。残りの 29 ファイルは、すべて 600 秒の制限を超えた。うち 23 ファイルは時間切れとして集計され、6 ファイル（`test/container/arraylist/test_arraylist.iec` など）は、次の不具合で `run_tests.py` が終わらず、集計されていない。合格したファイルは 0 件。
- `run_tests.py` の時間切れの処理に不具合がある（Windows で確認）。jiecc.exe は、起動したプロセスが、実際に処理するプロセスを子として起動する 2 段の構成になっている。`subprocess.run(..., timeout=...)` は、時間切れのときに起動したプロセスだけを kill する。そのため、子のプロセスは残って動き続け、標準出力のパイプを開いたままにするので、`run_tests.py` は子が終わるまで待ち続ける。計測では、600 秒の制限を過ぎた 6 つの子のプロセスが、1 時間以上動き続けた。Linux で同じことが起きるか、CI の `run` ジョブ（Windows）がこれで `timeout-minutes: 120` まで止まっているかは、確かめていない。
- 時間切れの原因は周期数にある。`test/math/test_floor.iec` を単独で実行すると、`--max-cycles 1000` では 10 秒で合格する（`[ PASSED ] 1 tests.`）が、`--max-cycles 100000` では 280 秒を超えても終わらない。jier は、テストが終わった後も指定した周期数まで回り続けるとみられる。CI の `run` ジョブは `--timeout 300` と既定の周期数で実行するので、エラーで止まらない 29 ファイルも時間切れで失敗しているはずである（CI の記録は確かめていない）。

### 2.4 テスト

- jier（`jiecc --run`）で `Math_floor` を実行すると、`Math_floor(1.0e19)` が `-8.446744073709552e+18`、`Math_floor(-1.0e19)` が `8.446744073709552e+18`、`Math_floor(1.0e300)` が `0.0`、`Math_floor(-1.0e300)` が `-1.0` を返す。`trunc` で `lint` に変換してから戻すため、`|x| >= 2^63` で正しくない。`4.5e15` と `9.0e18` は正しい。
- 乱数の分布（`src/random/*_template.iec`）のテストは、引数のエラー、`prob = 0 / 1` などの端の値、Python で求めた 1 つの値だけを確かめている。平均・分散などの統計的な性質は確かめていない。
- `nextPoisson`（`src/random/poisson_template.iec`）は、`EXP(-lambda)` を下限にして乱数の積を求める方法（Knuth の方法）で、λ に上限がない。λ が約 745 を超えると `EXP(-lambda)` が 0 にアンダーフローし、積が 0 になるまでループして、λ と関係のない値を返す。1 回の呼び出しで約 λ 回ループするので、λ が大きいとタスク周期も圧迫する。
- `MersenneTwister_next` と `Xorshift32_next` は、`bits` の範囲（doc プラグマでは 1〜32）を検査せず、`shr(x, 32 - bits)` を計算する。
- math のテストは `test_floor`（`EXPECT` 47 個）と `test_atan2`（`EXPECT` 70 個）、string_lib のテストは全 API を扱う 27 個の `TEST_S` があり、量は足りている（以前の見直しで「薄い」と書いたのは誤り）。
- `// Fact:` コメントのない `TEST_S` は、494 個中 273 個ある。
- POU の棚卸し: 全エントリファイルとテストを omron でコンパイルした XML の `Function` / `FunctionBlock` は 1,231 種類（名前で数える）。`vendor/jiecunit` と `test/` のソースで定義した名前と、`JiecTest_` で始まる名前（JiecUnit がマクロで生成する）を除くと 1,121 種類、そのうち名前に `private` も `_static_` も含まない公開 POU は 1,055 種類。ただしこの除き方では、JiecLib の `src/` と JiecUnit の `vendor/jiecunit/` が同じ名前で定義する POU（`Console_initialize`・`Console_print`・`Console_puts`・`mean`・`bool_to_string`・`time_to_string_sec` など）まで除いてしまう。PR-4 では、`src/` のソースで定義した名前（とテンプレートの具体化）を基準に数える。
- container の 11 種のテンプレートは、どの操作（`append`・`upsert` など）も、少なくとも 1 つの具体化でテストから呼ばれている。
- container 以外で、テストから直接呼ばれていない公開 POU は 26 個。うち 3 個（`string_to_string`・`udint_to_udint`・`uint_to_uint`）は、`sys_conv.iec` の型変換のマクロが使う恒等変換なので対象外にする。残りの 23 個は次のとおり。

  | モジュール | POU |
  |---|---|
  | array（dint 版。lreal 版はテストがある） | `Array_bubblesort_dint`・`Array_bubblesort_n_dint`・`Array_mergesort_n_dint`・`Array_quicksort_n_dint`・`Array_copy_x_dint`・`Array_isRegular_dint`・`Array_isRegular2d_dint`・`Array_isRegular2d_x_dint` |
  | random | `MersenneTwister_next`・`Xorshift32_next`（ビット数を指定する版） |
  | stats（`stats.iec` の基本統計。接頭辞がない） | `sampleSize`・`median`・`sampleVariance`・`standardDeviation`・`standardError`・`geometricMean`・`harmonicMean`・`coefficientOfVariation` |
  | stats（`inference/tests/test_core.iec`） | `Stats_p_value_t_two_tailed`・`Stats_p_value_normal_two_tailed`・`Stats_p_value_chi_square_right` |
  | encoding | `hex_nibble`（`hex.iec` の内部の補助関数だが、名前が `private_` で始まらない） |
  | `src/sys.iec` | `Console_print`（`print` マクロから呼ばれる） |

### 2.5 規約の検査の現状

CONTRIBUTING.md と AGENTS.md の規約のうち、機械的に判定できるものの違反件数（ソースを読んで数えた。コメントと文字列リテラルの中は除く）:

| 規則 | 件数 | 内訳 |
|---|---|---|
| キーワード（`if`・`or` など）が大文字 | 2 | `test/linalg/eigenvalue/test_eigenvector.iec:60` の `OR` 2 個 |
| 真理値のリテラルが大文字 | 2 | `src/array/sort_template.iec:338,351` の `while TRUE do` |
| 標準関数の名前が大文字 | 18 | `COS` 5・`SQRT` 5・`SIN` 4・`LN` 2・`EXP` 1・`ASIN` 1（`linalg/`・`random/poisson_template.iec` など） |
| 型の名前が大文字 | 0 | 大文字の `STRING` は約 100 行で使われているが、すべて `{#define STRING ...}`（14 ファイル、18 行）で定義したマクロ |
| doc プラグマの閉じていない引用符（PP29） | 0 | 対になったアポストロフィ（`'='` など）は 6 か所あるが、警告は出ない |
| `src/` の POU の直前に doc プラグマがない | 0 | `test/` のヘルパー関数（`hashmap_dint.iec` の `Dint_hash_for_hashmap_test` など）だけに 23 件ある |
| `continue` を使っている | 0 | |
| `/* */` のコメント | 0 | |
| 可変長配列（`array[*]`）を `var_in_out` 以外で使っている | 0 | XML の `VariableLength` で判定 |
| 構造体を返す関数 | 0 | XML の `ResultType` で判定（構造体は 129 種類） |

doc プラグマの書き方は 4 通りある。

| 書き方 | 出現数 | ファイル数 |
|---|---|---|
| `(*{doc ...}*)` | 1,196 | 111 |
| `{doc ...}` | 35 | 4（`math/atan2.iec`・`math/floor.iec`・`string_lib/string_lib.iec`・`container/hashmap/hashmap_template.iec`） |
| `{doc: ...}` | 13 | 2（`string_lib/string_lib.iec`・`string_lib/equivalence.iec`） |
| `(*{doc: ...}*)` | 1 | 1（`encoding/base64.iec`） |

`(*{doc ...}*)` 以外の書き方は、合わせて 49 か所、6 ファイルにある。`sys_conv.iec` のマクロの本体にある 2 か所（`(*${doc ...$}*)`）は、マクロの中でエスケープした `(*{doc ...}*)` の形で、正しい（最初の計測では `{doc ...}` と数えていた。PR-1 の実装時に直した）。

doc プラグマの言語: CONTRIBUTING.md は「コメントや doc プラグマ内では、英語を使用すること」と定めているが、`src/` の doc プラグマ 1,245 か所のうち 890 か所（75 ファイル）が、ASCII 以外の文字（日本語）を含む。`//` のコメントも、`src/` の 75 か所（21 ファイル）と `test/` の 172 か所（20 ファイル）が日本語を含む。`(* *)` のコメントは、`src/` の 2 か所（2 ファイル）が日本語を含む。

名前の制約の違反件数（omron でコンパイルした XML の `Function` / `FunctionBlock` の `Variable` と、`Member`。テンプレートの具体化を含み、POU 名と変数名の組で重複を除く）:

| 規則 | keyence を宣言したファイルの XML にあるもの | それ以外（omron だけのファイル） |
|---|---|---|
| 1 文字の変数名 | 50 | 573 |
| `h` / `H` で始まり `_` を含まない変数名 | 5（`Array_reverse_*` の `hi` など） | 65 |
| `^[rRtTcC]\d+$` の変数名 | 0 | 26（`Matrix_norm_spectral` の `t11`、`Stats_gamma` の `c0` など） |
| 1 文字の構造体メンバー | 0 | 1（`Stats_welford_state` の `n`） |
| `left` / `right` / `len` / `cmp` / `dec` の変数名 | 0 | 0 |
| `p_` / `P_` で始まる変数名 | 0 | 0 |
| 64 バイトを超える POU 名 | 0 | 0（最長は 59 バイトの `HashMap_LHMITLHSITdint_collision_static_robinhood_probedist`） |

keyence を宣言したファイルの 55 件には、公開 API の引数（`String_at` の `p`、`Array_bubblesort_n_lreal` / `Array_bubblesort_n_dint` の `n`、テストで keyence を宣言した `Math_floor` の `x`）が含まれる。CONTRIBUTING.md は、1 文字の名前などを「キーエンス環境の制約」として禁止している。規則が実際の制約より広いか、宣言が KV Studio で確かめられていないかの、どちらかである（D-1）。

### 2.6 NJ/NX の標準命令との重なり

NJ/NX シリーズ コマンドリファレンスマニュアル 基本編（SBCA-468）には、項目 4・5 と役割が重なる命令がある（ページは同マニュアルのもの）。

| 計画の POU | 重なる標準命令 | 違い |
|---|---|---|
| `Math_round` / `Math_trunc` / `Math_ceil` | `Round`・`TRUNC`・`RoundUp`（データ型変換命令） | 標準命令は整数を返す。計画の関数は `lreal` を返し、整数の範囲を超える値でも使える |
| `Math_fmod` | `FMod` | omron 以外のターゲットでも同じ名前で使える |
| `Signal_deadband` | `Band`（2-343） | 同上 |
| `Interp_linear1d` | `ScaleTrans`（2 点の直線変換のみ） | 計画の関数は多点の折れ線 |
| `Control_pid` | `PIDAT`・`PIDAT_HeatCool`（2-676・2-703） | 標準命令はオートチューニング付きの 2 自由度 PID。計画の関数は簡素な PID で、他ベンダーでも同じ書き方で使える |
| `Control_ramp` | `AC_StepProgram`（2-784） | 標準命令はプログラムパターン（多段）。計画の関数は 1 段のランプ |

JiecLib で提供する価値は、ベンダーをまたいで同じ書き方で使えることと、テストで振る舞いを確かめられることにある。omron でしか使わない利用者には、標準命令を勧める旨を README.md に書く。

## 3. 項目ごとの計画

### 3.1 項目 13: 規約の lint を CI に入れる（PR-1・PR-3）

#### 目的

CONTRIBUTING.md と AGENTS.md の規約のうち、機械的に判定できるものを CI で検査する。レビューでの見落としをなくし、後のフェーズで追加するコードにも同じ基準を当てる。

#### 設計

- `scripts/lint.py` を追加する。標準ライブラリだけを使う（外部の依存を増やさない）。
- 既定の対象は `src/`・`test/`・`samples/`（PR-11 の後）。`vendor/` と `scripts/lint_testdata/` は対象外。引数でファイルやディレクトリを絞れるようにする（`run_tests.py` と同じ書き方）。
- 2 層に分ける。
  - ソースを読む規則（PR-1）: jiecc は要らない。`.iec` を直接読む。
  - XML を読む規則（PR-3）: `--xml-dir DIR` で、`run_tests.py --compile-only --output-dir DIR`（PR-2）が出力した XML を読む。テンプレートが生成した POU・変数の名前も検査できる。前処理の出力は使わない（2.3 節）。
- XML の規則は、規則ごとに読むターゲットを決める。`keyence-names` は `DIR/keyence/` の XML（keyence を宣言したファイルのコンパイル結果）を、ほかの規則は `DIR/omron/` の XML を読む。同じ POU が複数の XML に入るので（2.3 節）、POU 名と変数名の組で重複を除いてから報告する。報告には、その POU が見つかった XML の 1 つを書く。（PR-3 では、`keyence-names` 以外の規則を全ターゲットの XML に当てた。下の「PR-3 の実装で計画から変えたこと」）
- `--xml-dir` を指定したのに、ヘッダーから予想される XML がないとき（コンパイルの失敗など）は、エラーにする（読まずに通らない）。
- 出力は `<path>:<line>: error: <rule-id>: <message>` の 1 行 1 件にする（`run_tests.py` の `error: ` の判定と揃える）。XML の規則は行番号が分からないため、`<xml>: error: <rule-id>: <POU 名>.<変数名>: <message>` とする。
- 終了コードは、エラーがあれば 1、なければ 0。
- 警告は基準値で管理する。`scripts/lint_baseline.json` に、今ある警告の一覧（規則・ファイル・POU 名などの位置を表す文字列。行番号は入れない。行が動くたびに変わるため）を書く。一覧にない警告が 1 件でも出たら、終了コード 1 にする。件数ではなく一覧で比べるので、1 つの PR で別の違反を直しながら新しい違反を入れても検出できる。
- 一覧から消えた（直った）警告があれば、一覧から消すよう促すメッセージを出す（`--update-baseline` で一覧を書き直せる。書き直しで増えることはない）。
- 基準値を増やす変更を止める: `lint` ジョブは、`pull_request` の event では、PR の `scripts/lint_baseline.json` と、PR のブランチと宛先のブランチの分岐点（`git merge-base`）のコミットの同じファイルを比べ、PR の方に増えた項目があれば失敗にする（`python scripts/lint.py --check-baseline-against <merge-base のコミット>`）。宛先のブランチの最新と比べると、PR のブランチが古いときに、宛先で減った分が「増えた」と見えて誤って失敗するため。宛先のブランチ名（`github.base_ref`）は `env:` で渡す。PR のブランチの基準値のファイルがない、または JSON として読めないときは、エラーで失敗にする。分岐点のコミットにファイルがないとき（PR-1 自身）は、比較を省略する。基準値は規則ごとの節に分け、分岐点のファイルにない規則の節を新しく足すこと（PR-3 の `keyence-names` など、新しい規則を入れる PR）は「増えた」とみなさない。すでにある節の項目が増えたときだけ失敗にする。これで、基準値を増やして警告を通すことはできない。
- 規則そのものを見直す PR（規則の実装を変え、同時に一覧を作り直す PR）だけは、ラベル `lint-baseline-reset` を付けると、基準値の比較を行わない。ラベルは作者だけが付ける運用にし、PR の本文に理由を書く（付けた人の確認は、仕組みではなくレビューで行う）。
- 2 本の PR が同時に一覧を減らすと、JSON が衝突する。一覧は 1 行 1 項目で、並び順を固定して出力し、衝突を手で直しやすくする。
- ファイルの先頭のコメントなどで規則を一時的に外す仕組みは作らない。外す必要が出たら、規則そのものを見直す。

#### 規則

| ID | 層 | 重さ | 内容 | 根拠 | 既存の違反（2.5 節） |
|---|---|---|---|---|---|
| `keyword-case` | ソース | エラー | キーワード（`if`・`or` など）、真理値のリテラル（`true` / `false`）、基本型の名前（`lreal` など）が小文字である。標準関数の名前（`sin`・`exp` など）を含めるかは D-12。`{#define}` で定義したマクロの名前、コメント、文字列リテラル、doc プラグマの本文は対象外 | AGENTS.md | 4（D-12 で標準関数を含めるなら 22） |
| `doc-apostrophe` | ソース | エラー | doc プラグマの中の引用符（`'`・`"`）が閉じている（閉じていないと PP29 の警告。判定は 2.3 節の jiepp の読み方に合わせる） | AGENTS.md・2.3 節 | 0 |
| `doc-missing` | ソース | エラー | `src/` の POU の直前に doc プラグマがある。`test/` は対象外 | CONTRIBUTING.md「ドキュメント」 | 0 |
| `doc-style` | ソース | エラー | doc プラグマを `(*{doc ...}*)` の形で書く（D-7） | 2.5 節 | 49 |
| `doc-language` | ソース | 警告（基準値で管理） | doc プラグマとコメント（`//`・`(* *)`）に、ASCII 以外の文字を使わない | CONTRIBUTING.md「コーディングスタイル」 | doc プラグマ 890、コメント 249（D-10） |
| `no-continue` | ソース | エラー | `continue` を使わない | CONTRIBUTING.md（オムロン環境） | 0 |
| `no-c-comment` | ソース | エラー | `/* */` のコメントを使わない | CONTRIBUTING.md | 0 |
| `test-fact` | ソース | 警告（基準値で管理） | `TEST_S` / `TEST_M` の中に `// Fact:` がある | CONTRIBUTING.md「テスト」 | 273 |
| `target-consistency` | ソース | エラー（PR-10 で追加） | 同じ対象のソースとテストで、宣言したターゲットが一致する（対応の定義は 3.6 節） | 2.2 節 | 3 か所の食い違い |
| `pou-name-length` | XML | エラー | POU 名が 64 バイト以内 | CONTRIBUTING.md（キーエンス環境） | 0 |
| `reserved-name` | XML | エラー | `left` / `right` / `len` / `cmp` / `dec` を変数・メンバーの名前に使わない | CONTRIBUTING.md | 0 |
| `omron-p-prefix` | XML | エラー | 要素名が `p_` / `P_` で始まらない | CONTRIBUTING.md（オムロン環境） | 0 |
| `varlen-array-inout` | XML | エラー | 可変長配列を `var_in_out` でだけ使う | CONTRIBUTING.md | 0 |
| `no-struct-return` | XML | エラー | 関数の戻り値に構造体を使わない | CONTRIBUTING.md（オムロン環境） | 0 |
| `keyence-names` | XML | 警告（基準値で管理）。D-1 の結論が出たらエラーにする | keyence を宣言したファイルで、1 文字の名前、`h` / `H` で始まり `_` を含まない名前、`^[rRtTcC]\d+$` の名前を使わない | CONTRIBUTING.md（キーエンス・三菱環境） | 55（PR-3 の実装で数えると 54） |

- `keyence-names` は、CONTRIBUTING.md の理由のとおりキーエンス（と三菱）環境の制約なので、keyence（または mitsubishi）を宣言したファイルのコンパイル結果にだけ当てる。omron だけのライブラリに当てると、既存の公開 API の引数名（`Math_floor` の `x` など）を変えることになり、名前付きの呼び出しを壊す。
- ただし、keyence を宣言したファイルにも 55 件（PR-3 の実装で数えると 54 件）の違反があり、公開 API の引数を含む（2.5 節）。規則と宣言のどちらが正しいかが決まるまで（D-1）、`keyence-names` は警告にし、基準値の一覧（PR-3 の実装で数えた 54 件）で新しい違反を止める。
- 名前の規則は、XML の `Variable` 要素（引数・局所変数・外部変数を含む）と `Member` 要素に当てる。CONTRIBUTING.md の「要素名」が局所変数を含むかも、D-1 で確かめる。
- PP30・PP23（コメント中のディレクティブ）は、コンパイルが止まるので規則にしない（2.3 節）。
- エイリアス型（CONTRIBUTING.md で禁止）は、XML での表し方を PR-3 で確かめてから規則にする。

#### 作業

PR-1:

1. `scripts/lint.py` にソースの規則を実装する。コメント（`(* *)`・`//`）、文字列リテラル（`'...'`・`"..."`、`$` のエスケープを含む）、doc プラグマの本文を取り除く処理を共通にする。`{doc ...}`・`{doc: ...}`・`(*{doc ...}*)`・`(*{doc: ...}*)` のすべてを doc プラグマとして扱う。
2. 基準値の仕組み（`scripts/lint_baseline.json`、`--update-baseline`、`--check-baseline-against`）を実装する。
3. `scripts/test_lint.py`（`unittest`）を追加する。規則ごとに、違反する入力と違反しない入力を 1 つ以上用意する。入力は `scripts/lint_testdata/` に置く（`run_tests.py` の対象外なので、コンパイルされない。lint の既定の対象にも入らない）。
4. 既存の違反を直す。
   - `keyword-case`: 4 か所（`OR` 2 個、`TRUE` 2 個）を小文字にする。D-12 で標準関数を含めると決めたら、18 か所も小文字にする。
   - `doc-style`: D-7 で揃えると決めたら、49 か所（6 ファイル）を `(*{doc ...}*)` に書き換える。書き換えの前後で、全エントリファイルの XML の `Documentation` 要素が変わらないことを、スクリプトで比べて確かめる。
   - 警告の規則（`doc-language`・`test-fact`）は直さず、今の警告の一覧を基準値にする。
5. CHANGELOG.md に `[Unreleased]` 節を作る。CONTRIBUTING.md の「バージョン管理」の「変更中の節」を、`[Unreleased]` 節と書き直す。
6. `.github/pull_request_template.md` を追加する（1.2 節の L3・L4 の欄と、1.3 節の確認の項目）。
7. `ci.yml` に `lint` ジョブを追加する（`ubuntu-latest`、`format` ジョブと同じく submodule は不要。宛先のブランチと比べるため、`actions/checkout` は `fetch-depth: 0`）。`python scripts/test_lint.py`、`python scripts/lint.py`、`pull_request` の event では `--check-baseline-against` を実行する。`pull_request` の `types` に `labeled` と `unlabeled` を加え、ラベルを付け外ししたときにも再実行されるようにする。PR のラベルの一覧（`github.event.pull_request.labels`）は `env:` で渡し、`lint-baseline-reset` があれば比較を省略する。ラベルを誰が付けたかは仕組みでは確かめられないので、レビューで確かめる。
8. `ci.yml` に `pr-body` ジョブを追加する（1.2 節）。
   - event は `pull_request` の `types: [opened, edited, synchronize, reopened]` にする（本文を直したときにも再実行されるように。既定の種別には `edited` が入らない）。
   - PR の本文は、`run:` に `${{ }}` で直接埋め込まず、`env:` で渡して Python で読む（本文によるコマンドの注入を防ぐ）。
   - 変更したファイルは、`git diff --name-only <merge-base> HEAD` で調べる（`fetch-depth: 0`）。`src/` の下のファイルがあれば L3 を要求する。変更したファイル（`src/`・`test/`・`samples/` の `.iec`）のヘッダーを `run_tests.py` の `_header_targets` で読み、keyence を宣言したものがあれば L4 も要求する。ヘッダーのないファイル（テンプレートなど）は、3.6 節の対象の対応づけで、そのテストのヘッダーを見る。
9. CONTRIBUTING.md の「テストの実行」と、AGENTS.md の「テスト」に、`python scripts/lint.py` の実行と、基準値の扱いを追記する。

PR-3:

1. `scripts/lint.py --xml-dir DIR` に XML の規則を実装する。POU は `Function` / `FunctionBlock` 要素、変数は `Variable` 要素、構造体のメンバーは `DataTypeDecl` の下の `Member` 要素から読む。
2. JiecUnit の POU（`vendor/jiecunit` のソースで定義され、`src/` のソースで定義されていない名前と、`JiecTest_` で始まる名前）と、テストのプログラム（`Program` 要素）は対象外にする。
3. `ci.yml` の `compile` ジョブで、`run_tests.py --compile-only --output-dir out` の後に `python scripts/lint.py --xml-dir out` を実行する（コンパイルを 2 回しない）。
4. 既存のコードで実行する。エラーの規則の違反は今 0 件で、`keyence-names` の 55 件（PR-3 の実装で数えると 54 件）は基準値にする。D-1 の結論が出たら、規則か宣言（または名前）を直して、エラーに切り替える。公開 API の引数名を変える直し方は、名前付きの呼び出しを壊すので、次のメジャー版に回す。

#### PR-1 の実装で計画から変えたこと

PR-1 は、ブランチ `feature/lint` で実装した（マージの前）。D-7・D-12 は、推奨案のとおりに決まり、その形で実装した。

- `lint-baseline`（基準値の比較）と `pr-body` のジョブは、`ci.yml` ではなく、新しい workflow の `.github/workflows/pr-checks.yml` に置いた。`ci.yml` の `pull_request` に `edited`・`labeled`・`unlabeled` を足すと、本文やラベルを変えるたびに `compile`・`run` のジョブ（最長 60 分・120 分）も再実行されるため。`ci.yml` の `lint` ジョブは、`scripts/test_lint.py`・`scripts/test_check_pr_body.py`・`scripts/lint.py` を実行する。
- PR の本文の検査は、`scripts/check_pr_body.py` にした（単体テストは `scripts/test_check_pr_body.py`）。ヘッダーのないファイルは、3.6 節の対応づけのうち、同じ対象の `src/` と `test/` の宣言の和集合を使う（テンプレートは keyence を宣言したエントリファイルからも include されるので、テストの宣言だけでは足りない）。
- `doc-apostrophe` は、`'` だけでなく `"` も見る（2.3 節）。
- `doc-language` は、`//` のコメントに加えて `(* *)` のコメントも見る（CONTRIBUTING.md は、すべてのコメントを英語と定めている）。基準値の項目は「ファイル: 最初の日本語の行」で、同じファイルに同じ行が複数あれば `#2` などを付ける。
- 構文の解析に失敗したとき（閉じていないコメント・文字列・プラグマ、コードに残った `*)`）を、エラーの規則 `parse` にした。jiecc は入れ子のコメントを受け付けないので、入れ子は `parse` で検出する。
- 基準値を作り直すオプションを `--reset-baseline` とした（`lint-baseline-reset` のラベルを付ける PR で使う）。

#### PR-3 の実装で計画から変えたこと

PR-3 は、ブランチ `feature/lint-xml`（`feature/run-tests` の上）で実装した（マージの前）。

- XML の規則は `scripts/lint_xml.py` に分け、`lint.py --xml-dir` から呼ぶ。
- エイリアス型は、XML の `DataTypeDecl` の `UserDefinedTypeSpec` が `xsi:type="DirectlyDerivedTypeSpec"` になると確かめたので、エラーの規則 `no-alias-type` にした（既存の違反は 0 件）。
- `xml-missing` を規則にした。ヘッダーから予想される XML がない、または読めないときのエラーである（設計の「読まずに通らない」）。
- 名前の規則は、全ターゲットの XML（keyence の XML を含む）に当てる。`keyence-names` だけは、keyence と mitsubishi の XML に当てる。
- CONTRIBUTING.md は、`h` / `H` の規則と `^[rRtTcC]\d+$` の規則を「変数名」、1 文字の規則を「要素名」に当てている。そこで、構造体のメンバーには 1 文字の規則だけを当てる（container の `HashMap_*_Entry_t` のメンバー `hash` の 21 件は違反にしない）。
- `keyence-names` の既存の違反は 54 件（1 文字 50 件、`hi` 4 件）で、2.5 節の 55 件（`h` で始まるもの 5 件）と 1 件違う。2.5 節の数え方は記録が残っていないため、差の理由は確かめていない。基準値は、実装した規則で数えた 54 件にした。
- 基準値で、`--xml-dir` を付けない実行（CI の `lint` ジョブや、手元での `--update-baseline`）は、`keyence-names` の節を変えない。古い項目の通知（`note: ... no longer occurs`）は、`--xml-dir` を付けて、パスを指定せずに全体を検査したときだけ出す。
- `scripts/lint_testdata/xml/` に、jiecc でコンパイルした XML を置く（jiecc のない `lint` ジョブで規則を試験するため）。`run-required` ジョブでは、jiecc でコンパイルし直して、置いた XML と同じ結果になることを確かめる（jiecc の XML の形が変わったことに気づくため）。
- CI の `compile` ジョブは、コンパイルが失敗しても XML の検査を行う（`if: !cancelled()`）。失敗したファイルの XML は `xml-missing` として報告される。

#### 完了の条件

- `python scripts/test_lint.py` が通り、全規則に違反の例と違反しない例がある。
- 既存コードで `python scripts/lint.py`（PR-3 の後は `--xml-dir` 付き）がエラー 0 件で、基準値の一覧にない警告が 0 件になり、CI の `lint` ジョブと `compile` ジョブが通る。
- 違反を 1 つ足したコードで、CI が失敗することを確かめる（警告の規則も含む）。`lint_baseline.json` に項目を足した PR で、`lint` ジョブが失敗することを確かめる。L3 の欄が空の PR で、`pr-body` ジョブが失敗することを確かめる。

#### リスク

- 簡易な字句解析なので、誤検出が出うる。誤検出は規則の実装を直して対処し、例外の仕組みは作らない。

### 3.2 PR-2: `run_tests.py` の拡張（項目 12・13・3 の共通部品）

#### 目的

- コンパイルした XML を残せるようにする。lint の XML の規則（PR-3）、POU の棚卸し（PR-4）、Release への XML の添付（PR-15）が使う。
- 新しく追加するテストを、jier で必ず通す仕組みを作る（1.2 節の L2）。

#### 設計

- `--output-dir DIR`: 指定したときは、XML を一時ディレクトリではなく `DIR/<target>/<ソースの相対パス>.xml` に出力する。例: `DIR/omron/src/string_lib/string_lib.xml`、`DIR/keyence/test/math/test_floor.xml`。README.md の XML の生成コマンドと同じく、拡張子 `.iec` を `.xml` に置き換える。
  - ディレクトリは `os.makedirs(..., exist_ok=True)` で作る（並列で呼ばれるため）。
  - コンパイルに失敗したときは、その XML を消す（不完全な XML を後の道具が読まないように）。
  - `DIR` の中の古い XML は消さない。CI では毎回空のディレクトリを使う。
  - 指定しないときは、今と同じ（一時ディレクトリに出力して消す）。
  - `--run-only` と一緒に指定したときは、エラーにする（XML を出力しないため）。
- `--paths-from FILE`: 対象のパスを、1 行 1 項目のファイルから読む。
  - 1 行は `<リポジトリからの相対パス> [<max-cycles>]`。パスの区切りは `/` だけを受け付け、`\` を含む行はエラーにする（Windows と Linux で同じファイルを使うため）。
  - `#` で始まる行と空行は無視する。
  - ファイルがない、または書かれたパスが存在しないときは、エラーにする（綴りの誤りを見逃さない）。
  - 有効な行が 0 件のときだけ、「対象なし」として終了コード 0 で終わる。`--paths-from` を使わずに対象が 0 件になったとき（既存の `nothing to check`）は、今と同じく終了コード 1 のままにする。
- 周期数: jier はテストが終わった後も `--max-cycles` まで回り続けるため（2.3 節）、実行時間は周期数で決まる。`--paths-from` の行の `<max-cycles>` で、ファイルごとに周期数を指定できるようにする（省略時は `--max-cycles` の値）。`TEST_S` だけのファイルは、テストの数と JiecUnit の初期化に要る周期数があれば足りる。
- 時間切れの処理を直す（2.3 節の不具合）。`subprocess.run` の `timeout` をやめ、`subprocess.Popen` で起動し、時間切れのときはプロセスの木ごと終了させる。Windows では `taskkill /T /F /PID <pid>`、Linux では `start_new_session=True` で起動して `os.killpg` を使う。終了させた後に、子のプロセスが残っていないことを確かめてから結果を返す。
- 周期数が足りないときに、一部のテストが実行されないまま合格と判定されないようにする。集計の行が出ないときは、今と同じく失敗と判定する。それに加えて、`run_tests.py` の合否の判定に、JiecUnit の開始の行（`[========] Running N tests.`）の N と、集計の行（`[========] N tests ran.`）の N が一致することを加える。テストを足したのに周期数を直し忘れたときも、これで検出できる。
- 既定の周期数（今は 100000）を下げるかは、エラーで止まらない 29 ファイル（2.3 節）で合格に必要な周期数を測ってから決める（D-13）。下げると、既存の `run` ジョブで時間切れになっているファイルが、時間内に終わるようになる。（PR-2 で測り、2000 に下げた。下の「PR-2 の実装の結果と、計画から変えたこと」）
- `scripts/jier_required.txt`: jier で必ず通すテストファイルの一覧。新しく追加したテストファイルは、必要な周期数と一緒にここに載せる（1.3 節）。
- `ci.yml` に `run-required` ジョブを追加する。`run_tests.py --run-only --paths-from scripts/jier_required.txt --timeout 300` を、Windows と Linux で実行する。`continue-on-error` を付けない（既存の `run` ジョブは今のまま参考扱い）。

#### 作業

1. 時間切れの処理を直す（プロセスの木ごと終了させる）。測定（作業 3）はこの修正の後に行う。修正の前に測ると、時間切れのファイルで `run_tests.py` が止まるため。
2. `compile_item` の出力先を、`--output-dir` に従って決める。`--paths-from` と、行ごとの周期数を追加する。合否の判定に、開始の行と集計の行のテストの数の一致を加える。
3. 周期数を測る。対象は、エラーで止まらない 29 ファイル（2.3 節。エラーで止まる 83 ファイルは、周期数に関係なく失敗する）。各ファイルを `--max-cycles` 1000・2000・4000・8000・16000 の順に実行し、集計行が出て、開始の行とテストの数が一致する最初の値を記録する。1 回の実行は 1000 周期あたり約 5 秒なので、全体で 1〜2 時間に収まる。16000 でも集計行が出ないファイルは、原因を調べて PR に書く。
4. 測定の結果を `docs/jier_cycles.md`（ファイルごとの必要な周期数と、測定した日・Jiecc の版・OS）に残す。D-13 の判断を受けて、`run_tests.py` の既定の `--max-cycles` を変える。
5. `scripts/jier_required.txt`（最初は、コメントだけで空）と、`run-required` ジョブを追加する。`jier_required.txt` に載せるファイルの周期数は、`docs/jier_cycles.md` と同じ方法で測った値にする。
6. `run_tests.py` の docstring、CONTRIBUTING.md の「テストの実行」、AGENTS.md の「テスト」と「既知の落とし穴」（jier が周期数まで回り続けること）に追記する。CHANGELOG.md 4.0.0 の「既知の問題」は過去の版の記録なので書き換えず、`[Unreleased]` 節に、時間切れの原因と既定の周期数の変更を書く。

#### PR-2 の実装の結果と、計画から変えたこと

PR-2 は、ブランチ `feature/run-tests` で実装した（マージの前）。

- 周期数の測定（`docs/jier_cycles.md`）: エラーで止まらない 29 ファイルのうち、28 ファイルが 1000 周期で合格した。2000 周期以上が必要なファイルはなかった。D-13 は推奨案（最大値の 2 倍）で実装し、既定の `--max-cycles` を 2000 にした。残りの `test/string_lib/test_string_lib.iec` は、1000 周期でも 900 秒で終わらない。jier の `find(s, '')` が 0 以外を返すため、`String_remove(..., '', -1)` のループが終わらない。
- エラーで止まるファイルは 83 件で、2.3 節の内訳（62・15・6）と同じだった。
- `--paths-from` と、引数でのパスの指定は、同時に使えない（エラー）。`--paths-from` のパスはリポジトリのルートからの相対パスで読む。テストを実行するときは、テストファイルを含まない行もエラーにする（`--run-only` で黙って何も実行しないことを防ぐ）。
- `run-required` ジョブは、`scripts/test_run_tests.py`（`run_tests.py` の単体テスト）も実行する。時間切れでプロセスの木ごと終了させる処理を、Windows と Linux の両方で確かめるため。
- 時間切れの処理は、Ctrl+C で中断したときも、起動中の jiecc のプロセスの木を終了させる。
- 時間切れの確認（`--timeout 5`）は、Windows では jiecc で確かめた（約 6 秒で終わり、jiecc のプロセスは残らなかった）。Linux では、jiecc の代わりに、子のプロセスを起動する Python のスクリプトで、単体テストとして確かめた（WSL の Ubuntu 24.04）。Linux の jiecc での確認は、CI の `run-required` ジョブで行う。

#### 完了の条件

- `python scripts/run_tests.py --compile-only --output-dir out src/string_lib` で `out/omron/src/string_lib/string_lib.xml` と `out/keyence/src/string_lib/string_lib.xml` ができる。わざとコンパイルを失敗させたファイルの XML は残らない。
- `--output-dir` を付けないときの出力が今と変わらない。
- `jier_required.txt` が空のとき、`run-required` ジョブが何も実行せずに通る。失敗するテストを載せると、ジョブが失敗する。存在しないパスや `\` を含む行を載せると、ジョブが失敗する。
- `--timeout 5` で jier を実行したとき、`run_tests.py` が約 5 秒で時間切れと判定して終わり、jiecc のプロセスが 1 つも残らないことを、Windows と Linux で確かめる。
- `docs/jier_cycles.md` に 29 ファイルの必要な周期数（終わらないファイルは、その原因）があり、既定の `--max-cycles` が D-13 の判断どおりに変わっている。
- 周期数が足りないとき（集計行が出ない、または開始の行とテストの数が合わない）に、`run_tests.py` が失敗と判定することを、周期数をわざと小さくして確かめる。

### 3.3 項目 3: テストの不足を埋める（PR-4〜PR-7）

#### 目的

テストのない公開 POU と、見つかった不具合（`Math_floor`・`nextPoisson`・`next(bits)`）をテストで押さえる。

#### PR-4: POU の棚卸し

1. `scripts/pou_inventory.py` を追加する。`run_tests.py --compile-only --output-dir`（omron）の XML とソースを読み、次を出す。
   - ライブラリの POU: XML の `Function` / `FunctionBlock` のうち、名前が `src/` のソースで定義されているもの、または `src/` のテンプレートの具体化であるもの。具体化は、テンプレートが生成する名前の形（`HashMap_<名前>_<操作>` など）で判定し、形の一覧をスクリプトに持つ。`test/` のソースで直接定義したヘルパー関数は除く。
   - テストから呼ばれている名前: テストの XML の `Program` 要素の `ST` 本体から、コメントと文字列リテラルを除いた識別子。
   - テストのない公開 POU: 名前に `private` も `_static_` も含まず、テストから直接呼ばれていないもの。テンプレートは、具体化ごとではなく操作ごとにまとめる（`HashMap_dint_copy` と `HashMap_record_copy` は `HashMap_*_copy` として、どれか 1 つの具体化が呼ばれていれば「テストあり」）。試作では、こうしないと container だけで 441 個が「テストなし」と出た。
2. 除く名前の一覧（恒等変換の `uint_to_uint` など）と、「テストなしと認めた POU」の一覧を、`scripts/pou_inventory_allow.txt` に持つ。1 行は `<POU 名またはテンプレートの形> <理由>` で、理由が空の行はエラーにする。
3. `--check` を付けると、次のときに終了コード 1 にする。
   - 一覧にないテストなしの公開 POU がある。
   - どの分類（`src/` のソースの定義・テンプレートの形・JiecUnit・`test/` のヘルパー・除く名前）にも当てはまらない POU が XML にある（「未分類」）。テンプレートの形の一覧が漏れたとき、新しいテンプレートの具体化を黙って見逃さないため。
   - 一覧に、もう存在しない POU や、テストができた POU が残っている（一覧を減らし忘れない）。
4. CI の `compile` ジョブで、PR-3 の lint の後に、同じ `out` の XML を使って実行する（PR-3 が `--output-dir` を `compile` ジョブに足した後に入れる）。PR-4 の時点では、2.4 節の 23 個を「テストなしと認めた POU」に入れておき、PR-7 で 1 個ずつ外す。

#### PR-4 の実装で計画から変えたこと

PR-4 は、ブランチ `feature/pou-inventory`（`feature/lint-xml` の上）で実装した（マージの前）。

- テンプレートの形は、スクリプトに一覧を持たず、`src/` のマクロのうち名前を作るもの（`{#define _HASHMAP_COPY_(T) HashMap_@@T@@_copy}` など、240 個）から求める。一覧を直し忘れることがなくなる。それでも当てはまらない名前は「未分類」として `--check` が失敗する。
- テンプレートの中で別のテンプレートを具体化した名前（hash set の中の `HashMap_HSIT<名前>_clear` など）は、`HashMap_HSIT*_clear` と `HashMap_*_clear` の両方の形に当てはまる。最も一般的な形（固定の文字が最も少ない形）を操作とする。こうしないと、内部で使う具体化が、テストのない操作として 39 個出た。
- 「ライブラリの POU」は、`src/` のエントリファイルの XML にある POU とした。array のように `src/` が具体化したテンプレートの POU（`Array_bubblesort_dint` など）は、1 つずつテストが要る。テストでだけ具体化するもの（container など）は、操作ごとにまとめる。
- テストのない公開の POU は 31 個だった。2.4 節の 26 個（23 個と恒等変換 3 個）に加えて、`stats.iec` の `mean`・`sum`・`variance`・`skewness`・`kurtosis` の 5 個がある。`mean` は、テストに名前付き引数 `mean:=`（`MersenneTwister_nextGaussian` の引数）があるため、識別子を数える方法では「呼ばれている」と誤って判定される。ほかの 4 個の差の理由は、2.4 節の数え方の記録が残っていないため確かめていない（テストのプログラムの本体で、これらは呼ばれていない）。PR-7 の対象は、この 5 個を加えた 28 個になる。
- テストから呼ばれているかは、計画どおり、テストのプログラム（`Program`）の本体だけで判定する。テストの補助関数の中からの呼び出しは数えない。判定するのは、呼び出しの形（`名前(`。`.` の後のメンバーは除く）と、プログラムの変数の型の名前（ファンクションブロックはインスタンスで使うため）である。ファンクションブロックは、その型の変数を宣言しただけで（インスタンスを呼ばなくても）テストありとみなす。変数や名前付き引数の名前は数えない。
- 分類は、`src/` の XML にある POU を最初にライブラリの POU とし、`src/` で定義した名前をテンプレートの具体化と取り違えないようにした。

#### PR-5: `Math_floor` の修正

1. `|x| >= 2^52`（`4503599627370496.0`）のときは、`x` をそのまま返す。この範囲の `lreal` は必ず整数なので、`trunc` を通す必要がない。
2. テストを、jier で通る新しいテストファイル（`test/math/test_floor_large.iec`）に書き、`scripts/jier_required.txt` に載せる。既存の `test_floor.iec` は jier で確かめられない場合がある（2.3 節）。値は `±4.5e15`・`±9.0e18`・`±1.0e19`・`±1.0e300`、`2^52` ちょうどと、その前後の値。
3. NaN と無限大は、この PR では扱わない。PR-8 の調査の後、PR-8 でテストを足す。負の 0（`Math_floor(-0.0)` は、修正の前から +0.0 を返す。Python の `math.floor` は -0.0 を返す）も、PR-8 で扱う。

#### PR-6: `TEST_M` の確認と、乱数の分布のテスト

1. 最初に、`TEST_M` を使う小さなテスト（周期ごとに値を積み上げて、`CURRENT_CYCLE()` で 20 周期目に確かめる）を作り、jier と Sysmac Studio のシミュレータの両方で動くことを確かめる。動かなければ、PR-6 の残りと、`TEST_M` を使う PR-12・PR-14 の設計を見直す。
2. 対象は `nextGaussian` / `nextExponential` / `nextPoisson` / `nextBernoulli` / `nextIntInRange` / `nextRealInRange`。各生成器（Mersenne Twister・Xorshift32・LCG・LFSR32）のうち、その API があるもの（README.md の API 対応表）すべて。
3. 固定のシードで N 個生成し、次の許容幅で確かめる。シードが固定なので結果は決まっており、偶然で失敗することはない。許容幅は、実装の誤り（係数の取り違えなど）を検出する目的で決める。
   - 標本平均: 理論値 ± 5σ/√N（σ は理論的な標準偏差）。
   - 標本分散: 理論値 ± 5σ²√((κ − 1)/N)。κ は尖度で、テストごとにコメントに書く（正規分布 3、指数分布 9、Poisson 3 + 1/λ、一様分布 1.8）。
   - `nextBernoulli(prob)`: 真の回数が N·prob ± 5√(N·prob·(1 − prob)) の範囲にある（二項分布の標準誤差）。正規近似を使うので、N·prob·(1 − prob) が 25 以上になる prob（例: N = 10,000 なら 0.01〜0.99）で確かめる。prob = 0 と 1 は、既存のテストの端の値の確認で足りる。
   - `nextIntInRange`: 値ごとの出現回数のカイ二乗統計量が、自由度 df のカイ二乗分布の両側の臨界値（下側確率 1.0e-6 と上側確率 1.0e-6 の分位点。scipy で求めてテストに数値で書く）の間にある。下側も確かめるのは、出現回数が均等すぎる周期的な偏り（LCG の下位ビットなど）を検出するため。df が小さいと正規近似（df ± 5√(2df)）は使えないので、近似ではなく分位点を使う。各値の期待度数は 5 以上にする。全値が範囲内にあることも確かめる。
4. `nextPoisson` のテストの λ は 30 以下にする。λ の上限を設け、上限を超えたら `eno := false` にする修正を同じ PR で行う。上限の値は D-11。
5. N 個の生成を 1 周期で行うと、PLC のタスク周期を超えるおそれがある。`TEST_M` を使い、1 周期あたりの個数を決めて周期に分ける（たたき台は 500 個 × 20 周期）。1 周期あたりの個数は、Sysmac Studio のシミュレータでの実行時間を測って決め、PR に書く。
6. 期待値（理論値）は、テストのコメントに式で書く。

#### PR-6 の実装の結果と、計画から変えたこと

PR-6 は、ブランチ `feature/random-dist`（`feature/floor-large` の上）で実装した（マージの前）。

- `TEST_M` の確認（`test/test_jiecunit_test_m.iec`）: jier では、20 周期にわたって変数を保ち、`CURRENT_CYCLE()` が 0 から数えることを確かめた。21 周期で合格し、20 周期では集計行が出ずに失敗する。`scripts/jier_required.txt` に載せた。Sysmac Studio のシミュレータでの確認（L3）は、まだ行っていない。PR-12・PR-14 の前に、作者が行う。
- **分布のテストは jier で実行できない。** 4 つの生成器（`mersenne_twister.iec`・`xorshift32.iec`・`lcg.iec`・`lfsr32.iec`）は、どれも幅なしの `shl` / `shr` を使う（2.3 節）。そこで、1.2 節の L2 の例外（jier で通らないファイルは L3 の結果で代える）にあたる。`test/random/test_random_distribution.iec` は `jier_required.txt` に載せず、L3 で確かめる。
- その代わりに、生成器と分布の関数を Python で再現し、同じシードでテストの統計量を求めた。再現は、既存のテストの参照値（MT のシード `0xCAFEBABE` の `nextDouble`、Xorshift32 のシード `0x92D68CA2` の `nextUint32` と `nextDouble`、LCG の `nextUint32`）と、MT19937 の標準の値（シード 5489 の最初の出力 3499211612）に一致した。16 通りすべてで、統計量は許容幅の半分以内だった（最大は Gaussian の分散の 0.46）。さらに PR-7 で、`src/` の写しで生成器の `shr` / `shl` を `shr_dword` などに置き換え、その写しで jier を実行して、7 件のテストがすべて合格することを確かめた（約 14 分）。この実行で、`LFSR32_init` の呼び出しの誤りが見つかり、直した。
- 対象は、計画の 6 つの API と、その API を持つ生成器の組（16 通り）。LFSR32 は `nextIntInRange` だけを持つ。
- scipy は手元の環境になかった（外部の依存を増やさない）。カイ二乗分布の分位点は、正則化不完全ガンマ関数を Python の標準ライブラリで実装して求め、表の値（自由度 9 の上側 0.05・0.001 と下側 0.001）と一致することを確かめた。自由度 9 で、下側 1.0e-6 は 0.22838484007344917、上側 1.0e-6 は 44.81093787068782。
- テストのパラメーター: N = 10,000（500 個 × 20 周期）、`nextIntInRange(0, 9)`、`nextRealInRange(-2, 6)`、`nextBernoulli(0.3)`、`nextGaussian(10, 2)`、`nextExponential(0.5)`、`nextPoisson(4)`。1 周期あたりの個数（500）は、シミュレータでの実行時間を測って見直す（L3）。
- λ の上限は D-11 の推奨値（500）で実装した。500 は受け付け、500.001 と 1000 は `eno := false` になることを、同じファイルの `test_nextPoisson_lambda_limit` で確かめる（これも L3）。

#### PR-7: テストのない POU のテスト

1. PR-4 の一覧を、モジュールごとの PR に分けて減らす。対象は 2.4 節の 23 個（PR-4 の棚卸しで、`stats.iec` の 5 個を加えた 28 個になった。上の「PR-4 の実装で計画から変えたこと」）。
   - array（8 個）: dint 版のソート・コピー・正規性の判定。lreal 版のテストと同じ事実を、dint の値で確かめる。
   - random（2 個）: `MersenneTwister_next(bits)`・`Xorshift32_next(bits)`。`bits` = 1・16・32 で、結果が `2^bits` 未満であることと、参照実装の値と一致することを確かめる。参照値は、既存のテストのコメントにある方法（シード `0xCAFEBABE` の参照値）と同じ方法で求める。Python の `random.seed` は Mersenne Twister を `init_by_array` で初期化するので、`init_genrand` を使う既存の実装と値が違う点に注意する。範囲外（0、33）で `eno := false` にする修正を同じ PR で行う（振る舞いの変更なので、CHANGELOG.md の「修正」に書く）。
   - stats（11 個）: `stats.iec` の基本統計 8 個は、`descriptive/` の同じ計算のテストと同じ入力で、同じ値になることを確かめる。`Stats_p_value_*` の 3 個は、scipy の値と比べる。p 値が 1.0e-3 以上なら `EXPECT_NEAR`（許容誤差 1.0e-4 以下。CONTRIBUTING.md のテストの個別の規定）、それより小さいなら `EXPECT_NEAR_REL`（相対誤差）を使う。絶対誤差では、小さい p 値の誤りを見逃すため。
   - encoding（1 個）: `hex_nibble` は内部の補助関数なので、テストを書くのではなく、名前を `private_hex_nibble` に変えることを検討する（D-9）。変えるまでは「テストなしと認めた POU」に理由付きで残す。
   - `src/sys.iec`（1 個）: `Console_print` は、`print` マクロで書いた文字列がコンソールの行に入ることのテストを、新しいファイル `test/test_sys_console.iec` に書く（既存の `test/test_sys.iec` は jier で確かめられないため）。
2. 新しいテストファイルは `scripts/jier_required.txt` に載せる。既存のテストファイルに事実を足すときは、そのファイルが jier で通らない場合がある。その場合は、新しいテストを別のファイルに分ける。
3. テストの書き方は規約（`// Fact:`・AAA 形式）に従う。期待値は Python（標準ライブラリ、numpy・scipy）で求め、求め方をコメントに書く。
4. 既存のテストを規約の書き方に揃える作業は、別の PR にする（`test-fact` の警告の基準値を下げて進み具合を測る）。

#### PR-7 の実装の結果と、計画から変えたこと

PR-7 は、ブランチ `feature/untested-pous`（`feature/random-dist` の上）で、1 つの PR にまとめて実装した（マージの前）。`scripts/pou_inventory_allow.txt` に残るのは、`hex_nibble`（D-9）と恒等変換 3 個だけになった。

| ファイル | 対象 | jier |
|---|---|---|
| `test/array/test_array_dint.iec` | dint 版のソート 4 個とコピー 1 個 | 通る（`jier_required.txt` に載せた） |
| `test/array/test_array_isregular_dint.iec` | dint 版の正規性の判定 3 個 | 通らない（`Array_isRegular` が dint の `max` を使う） |
| `test/random/test_random_bits.iec` | `MersenneTwister_next(bits)`・`Xorshift32_next(bits)` | 通らない（幅なしの `shl` / `shr`） |
| `test/stats/test_stats_basic.iec` | `stats.iec` の基本統計 13 個 | 通らない（`Array_isRegular` の `max`） |
| `test/stats/inference/tests/test_p_values.iec` | `Stats_p_value_*` の 3 個 | 通る（載せた） |
| `test/test_sys_console.iec` | `Console_print` | 通る（載せた） |

- jier で通らない 3 ファイルは、1.2 節の例外として L3 で確かめる。ただし、手元の確認として、`src/` の写しで `Array_isRegular` の `max` を `if` 文に、random の `shr` / `shl` を型付きの `shr_dword` などに置き換え、その写しで jier を実行して、3 ファイルとも合格することを確かめた（リポジトリの `src/` は変えていない）。同じ方法で、PR-6 の `test_random_distribution.iec` も実行した。その実行で、`LFSR32_init` を仮引数なしで呼び、省略できる引数（`poly`）を省いていた誤りが見つかったので、仮引数付きの呼び出しに直した。
- `stats.iec` の基本統計は、計画の 8 個に PR-4 で見つかった 5 個（`mean`・`sum`・`variance`・`skewness`・`kurtosis`）を加えた 13 個。それぞれ、呼び出している `Stats_*` 関数と同じ値になることと、Python の値に一致することを確かめる。歪度と尖度の式（scipy の `bias=False`）は、既存のテストの期待値を再現することを確かめた。
- p 値の期待値は、scipy がないので、標準ライブラリで正則化不完全ベータ関数（t 分布）と正則化不完全ガンマ関数（カイ二乗分布）を実装して求めた。既知の値（z = 1.959964、t = 2.228139（自由度 10）、x = 3.841459（自由度 1）で p = 0.05）を再現する。
- `next(bits)` は、`bits` が 1〜32 の範囲外のとき `eno := false` を返し、生成器の状態を変えないようにした。
- `Console_print` は、`print` マクロ（グローバルのコンソールに書く）ではなく、ローカルの `Console_t` に対して直接呼んで確かめた。グローバルのコンソールには JiecUnit もテストの経過を書くので、行の位置が前のテストの出力で変わり、期待値を決められないためである。

#### 完了の条件

- PR-4: `pou_inventory.py --check` が CI で通る。テストのない POU・未分類の POU・理由のない行・古い行のそれぞれを 1 つ足したとき、`--check` が失敗することを確かめる。
- PR-5: `test_floor_large.iec` が `run-required` ジョブで通り、L3 の結果が PR にある。
- PR-6: `TEST_M` の確認の結果（jier と Sysmac Studio のシミュレータのそれぞれで合格か）と、1 周期あたりの個数と、そのときの 1 周期の実行時間（シミュレータで測った値）が PR にある。分布のテストと、λ の上限を超えたときに `eno` が false になるテストが `run-required` ジョブで通る。
- PR-7: `pou_inventory_allow.txt` の「テストなしと認めた POU」が、理由の書かれたもの（`hex_nibble` など）だけになり、追加したテストが `run-required` ジョブで通り、L3 の結果が PR にある。

### 3.4 項目 4: math の関数の追加（PR-8）

#### 目的

PLC のプログラムでよく使うのに、IEC 61131-3 の標準関数にない数値関数をそろえる。

#### 特殊な値の調査（PR-8 の最初に行う）

NaN と無限大を、各環境の ST で作れるか（`0.0 / 0.0` など）と、比較の結果（NaN の `x <> x` が真になるか）を、jier・Sysmac Studio のシミュレータ・KV Studio で調べる。結果を PR に書き、次のどちらかにする。

- どの環境でも同じ結果になる: NaN は NaN を返し、無限大はそのまま返す（Python の `math` と同じ）。`Math_floor` を含めてテストを書く。
- 環境によって違う、または作れない: NaN と無限大の振る舞いは「未定義」と doc プラグマに書き、テストしない。

#### 関数の仕様

1 関数 1 ファイル（`src/math/<名前>.iec`）にし、`src/math/floor.iec` と同じ構成にする。引数名は CONTRIBUTING.md の命名規則に従い、1 文字にしない。

| 関数 | シグネチャ | 仕様 | エラー |
|---|---|---|---|
| `Math_ceil` | `(value: lreal): lreal` | 天井関数。`-Math_floor(-value)` と同じ結果 | なし |
| `Math_trunc` | `(value: lreal): lreal` | 0 方向への切り捨て。`|value| >= 2^52` はそのまま返す | なし |
| `Math_round` | `(value: lreal): lreal` | 四捨五入（0.5 は 0 から遠い方へ）。`t := Math_trunc(value)` とし、`|value - t| >= 0.5` なら `t` に符号を付けた 1 を足す。`value + 0.5` を切り捨てる方法は、`0.49999999999999994` で 1 を返すので使わない | なし |
| `Math_roundHalfEven` | `(value: lreal): lreal` | 偶数丸め（0.5 ちょうどは偶数の方へ） | なし |
| `Math_roundTo` | `(value: lreal; digits: dint): lreal` | `Math_round(value * 10^digits) / 10^digits`。`10^digits` は、`expt` を使わず、10 の整数べきの定数表から取る（`1.0e0`〜`1.0e15` は `lreal` で正確に表せる）。2 進数で表せない値は、見た目の 10 進数どおりには丸まらない（例: `1.015` は `1.015 * 100 = 101.49999999999999` になり、`digits = 2` で `1.01`）。この振る舞いを doc プラグマに書く。テストの期待値は、Python の `round` ではなく、この定義で求める | `digits` が -15〜15 の範囲外 |
| `Math_clamp` | `(value, lower, upper: lreal): lreal` | `value` を `[lower, upper]` に収める | `lower > upper` |
| `Math_lerp` | `(start_value, end_value, ratio: lreal): lreal` | `ratio = 1.0` のときは、分岐して `end_value` をそのまま返す。それ以外は `start_value + (end_value - start_value) * ratio`（`ratio = 1` で計算すると、`start_value = 1e20`、`end_value = 1` で `end_value` にならない） | なし |
| `Math_sign` | `(value: lreal): lreal` | -1.0 / 0.0 / 1.0 | なし |
| `Math_hypot` | `(x_value, y_value: lreal): lreal` | `sqrt(x^2 + y^2)`。大きい方の絶対値で割ってから計算し、桁あふれを避ける | なし |
| `Math_fmod` | `(dividend, divisor: lreal): lreal` | 浮動小数点の剰余。結果の符号は `dividend` と同じで、結果は正確（C の `fmod` と同じ値）。`dividend - trunc(dividend / divisor) * divisor` は、商の丸め誤差で値がずれ（`fmod(5.3, 0.1)` の正しい値は `0.09999999999999953`）、`|dividend / divisor| >= 2^63` で `lint` があふれるので使わない。`|dividend| < |divisor|` なら `dividend` をそのまま返す。そうでなければ、`|divisor|` を 2 倍ずつ大きくして `|dividend|` を超えない最大の値を求め、引き算と半分にすることを繰り返す方法（各段の引き算は正確）で求める。2 倍にするかどうかは `scaled <= |dividend| * 0.5` で判定する（`scaled * 2` を計算してから比べると、`|dividend|` が `lreal` の最大値に近いときに無限大にあふれるため）。ループの回数は、両者の指数の差（最大で約 2,100 回）。この上限を doc プラグマに書き、最大の回数のときの実行時間を L3 で測って PR に書く | `divisor = 0` |
| `Math_gcd` | `(num_a, num_b: lint): lint` | 最大公約数。負の数は絶対値で扱う。`gcd(0, 0) = 0` | どちらかが `lint` の最小値（絶対値が表せない） |
| `Math_lcm` | `(num_a, num_b: lint): lint` | 最小公倍数。どちらかが 0 なら 0 | 結果が `lint` を超える |
| `Math_isClose` | `(value_a, value_b: lreal; rel_tol: lreal := 1.0e-9; abs_tol: lreal := 0.0): bool` | Python の `math.isclose` と同じ判定。最初に `value_a = value_b` なら真を返す（無限大どうしの比較のため）。NaN の扱いは特殊な値の調査に従う | `rel_tol < 0` または `abs_tol < 0` |

- エラーのとき、戻り値は既定値（`lreal` は 0.0、`bool` は false）にする（既存の関数と同じ。CONTRIBUTING.md「異常系の実装においては、戻り値を設定する必要はない」）。
- 名前と引数名は D-4。

#### 作業

1. 特殊な値の調査（上記）。
2. 丸めの関数（`ceil`・`trunc`・`round`・`roundHalfEven`・`roundTo`）を追加する。
3. `clamp`・`lerp`・`sign`・`hypot`・`fmod` を追加する。
4. `gcd`・`lcm`・`isClose` を追加する。
5. 各関数のテストを、関数ごとのテストファイル（`test/math/test_<名前>.iec`）に書き、`test/math/test_math.iec` にまとめて登録し、`scripts/jier_required.txt` に載せる。期待値は Python の `math` モジュール（`roundTo` は上の定義）で求めてコメントに書く。境界値（0、負の 0、0.5 ちょうど、`2^52` 前後、`lint` の最大値・最小値）を必ず含める。`fmod` は `fmod(5.3, 0.1)`・`fmod(1.0e300, 3.0)`・`lreal` の最大値を割られる数にした場合・`|dividend| < |divisor|` の場合・非正規化数（例: 最小の非正規化数を m として `fmod(3m, 2m) = m`）を含める。期待値は Python の `math.fmod` で求め、実装の後に jier でも同じ値になることを確かめてコメントに残す。
6. README.md の math の表に追加する。2.6 節の標準命令との違いも書く。
7. 2〜4 は、1 つの PR が大きくなりすぎるなら、PR を分けてよい。

#### PR-8 の実装の結果と、計画から変えたこと

PR-8 は、ブランチ `feature/math-functions`（`feature/untested-pous` の上）で、1 つの PR にまとめて実装した（マージの前）。名前と引数名は D-4 の推奨案（上の表）のとおり。

- 特殊な値の調査（jier だけ。Sysmac Studio のシミュレータと KV Studio は、この環境では調べられない）: `0.0 / 0.0` と `1.0 / 0.0` は、`DIVISION_BY_ZERO` のエラーで止まり、NaN も無限大も作れない。`1.0e308 * 10.0` は無限大になる。`sqrt(-1.0e308)`・`ln(0.0)`・`exp(1000.0)` は、NaN にも無限大にもならない値を返す。環境によって作り方が違う（少なくとも jier では 0 除算で作れない）ので、計画の 2 つ目の案にした。全関数の doc プラグマに「NaN と無限大の結果は未定義」と書き、テストしない。L3・L4 の環境で振る舞いを調べ直す余地はある。
- ファイル名は、関数名をスネークケースにした（`Math_roundHalfEven` は `round_half_even.iec`）。
- `Math_roundTo` で `digits` が負のときは、`10^digits`（`1.0e-2` など。2 進数で正確に表せない）を掛けるのではなく、`10^-digits` で割ってから丸め、`10^-digits` を掛ける。
- `Math_gcd`・`Math_lcm` は、整数の `abs` を使わない（jier が、dint の `max` と同じく、整数の `abs` で `cannot marshal Python int ... LREAL` のエラーになるため）。`if` 文で符号を反転する。
- `Math_fmod` のアルゴリズムは、実装の前に Python で同じ手順を書き、20 万組の乱数（指数 -300〜300）と計画の値で `math.fmod` と完全に一致することを確かめた。jier でも、計画の全部の値（`lreal` の最大値と最小の非正規化数を含む）が `math.fmod` と一致した。
- 13 個のテストファイルはすべて jier で通り、`scripts/jier_required.txt` に載せた（1000 周期）。

#### 完了の条件

- 全関数のテストが `run-required` ジョブで通り、L3 の結果が PR にある。

### 3.5 項目 6: CRC16 とチェックサム（PR-9）

#### 目的

Modbus RTU・シリアル通信・機器の電文でよく使う誤り検出の符号を追加する。今は CRC32 だけある。

#### 設計

- `src/hash/crc16.iec` を追加する。CRC16 は電文に数値として付けることが多いので、数値（`word`）を返す関数を基本にし、16 進の文字列にする関数も用意する。
- `CRC32_bytes` には作業用の配列 `work` の引数があるが、入力をコピーするだけなので、CRC16 では設けない（呼び出し側の負担を減らす）。
- 計算はテーブルを使わないビット単位の方法にする（256 要素の定数表を持たない）。性能が問題になれば、後でテーブル版を足す。
- 引数 `crc_init` で、計算を続けられるようにする。2 つの配列にまたがる電文は、1 つ目の結果を 2 つ目の `crc_init` に渡す。3 種とも最終 XOR がないので、この方法で続けられる。

| 関数 | シグネチャ | 内容 |
|---|---|---|
| `CRC16_modbus` | `(dat: array[*] of byte (var_in_out); offset: dint := 0; length: dint := -1; crc_init: word := 16#FFFF): word` | CRC-16/MODBUS（多項式 `16#8005`、入出力を反転、最終 XOR なし） |
| `CRC16_ccittFalse` | 同上（`crc_init` の既定値 `16#FFFF`） | CRC-16/CCITT-FALSE（多項式 `16#1021`、反転なし） |
| `CRC16_xmodem` | 同上（`crc_init` の既定値 `16#0000`） | CRC-16/XMODEM（多項式 `16#1021`、反転なし） |
| `CRC16_toHex` | `(crc: word): string[4 + 1]` | 4 桁の 16 進文字列（CRC32 に合わせて小文字） |

- `src/hash/checksum.iec` を追加する。

| 関数 | 内容 |
|---|---|
| `Checksum_sum8` | 8 ビットの和（桁あふれは捨てる） |
| `Checksum_xor8` | 全バイトの XOR |
| `Checksum_lrc` | Modbus ASCII の LRC（8 ビットの和の 2 の補数）。対象は、ASCII の 16 進文字を 2 進のバイトに戻した後のバイト列であることを doc プラグマに書く |

- 引数（`dat`・`offset`・`length`）とエラー（`offset` / `length` が配列の範囲外）は、`CRC32_bytes` と同じにする。

#### テストの期待値（Python で計算して確かめた値）

| 入力 | 関数 | 期待値 |
|---|---|---|
| ASCII `123456789` | `CRC16_modbus` | `16#4B37` |
| 同上 | `CRC16_ccittFalse` | `16#29B1` |
| 同上 | `CRC16_xmodem` | `16#31C3` |
| 同上 | `Checksum_sum8` | `16#DD` |
| 同上 | `Checksum_xor8` | `16#31` |
| 同上 | `Checksum_lrc` | `16#23` |
| Modbus RTU の電文 `01 03 00 00 00 0A` | `CRC16_modbus` | `16#CDC5`（電文には下位バイト `C5`、上位バイト `CD` の順で付ける） |

ほかに、長さ 0（`crc_init` をそのまま返す）、`offset` と `length` で一部だけを対象にする場合、`123456789` を `1234` と `56789` に分けて `crc_init` で続けた結果が全体の結果と同じになること、範囲外のエラーを確かめる。

#### 作業

1. `crc16.iec` と `checksum.iec`、テスト（`test/hash/test_crc16.iec`・`test/hash/test_checksum.iec`）を追加し、`test/hash/test_hash.iec` に登録し、`scripts/jier_required.txt` に載せる。
2. README.md の hash の節に追加する。電文への付け方（下位バイトが先）を例で書く。

#### PR-9 の実装の結果と、計画から変えたこと

PR-9 は、ブランチ `feature/crc16`（`feature/math-functions` の上）で実装した（マージの前）。

- ビットのずらしは、`shr` / `shl` ではなく、整数の割り算（`/ 2`）と掛け算（`* 2`・`* 256` と `mod 65536`）で行う。jier が幅なしの `shr` / `shl` を実行できないためで、これでテストを jier で実行でき、`scripts/jier_required.txt` に載せた（`test_crc16.iec`・`test_checksum.iec`）。
- `offset` と `length` の範囲の判定（`CRC32_bytes` と同じ規則）は、内部の関数 `private_CRC16_range` にまとめ、チェックサムの 3 関数も使う。
- 上の表の全期待値に加えて、`offset` の付いた配列（下限が 10）、`crc_init` での継続（3 種とも）、長さ 0（配列の末尾を含む）、範囲外のエラーを確かめる。jier で全部合格した。

#### 完了の条件

- 上の表の全期待値のテストが `run-required` ジョブで通り、L3 の結果が PR にある。

### 3.6 項目 7: 対応ターゲットを明記する（PR-10）

#### 目的

利用者が、ライブラリごとに使えるターゲットを判断できるようにする。今の README.md は「Sysmac Studio が対象」と書いているが、実際はヘッダーで keyence を宣言したライブラリがあり、宣言はソースとテストで食い違っている（2.2 節）。

#### 設計

- 対応の段階を 2 つに分ける。
  - **宣言**: ヘッダーの `$ jiecc` の行に `-t <target>` がある。CI はこのターゲットでコンパイルする（L1）。lint の `keyence-names` もこの宣言に従う。
  - **確認済み**: そのターゲットの開発環境（Sysmac Studio・KV Studio など）でテストを実行して通った。根拠は PR のテンプレートの L3・L4 の欄（1.2 節）で、README.md の表に、確かめた開発環境の版と日付を書く。根拠のないものは「未確認」とする。
- jiecc のコンパイルはどのターゲットでも通るので（2.2 節）、「コンパイルが通る」ことは宣言の根拠にしない。
- 対象の対応づけ（`target-consistency` と表の単位）:
  - `src/<module>/` 以下のエントリファイルと、`test/<module>/` 以下のテストファイルを、同じ対象として扱う（例: `src/stats/inference/tests/` も `stats` に入る）。
  - `src/` 直下のファイル（`sys.iec`・`sys_conv.iec` など）は、対象 `sys` として、`test/` 直下の `test_sys.iec`・`test_sys_conv.iec` と対応づける。
  - ソースにヘッダーがない対象（container のテンプレート、`sys`）は、テストのヘッダーを宣言とみなす。
  - 対象ごとに、ソースの宣言の和集合とテストの宣言の和集合が同じであることを確かめる。
- ヘッダーの解釈は、`run_tests.py` の `_header_targets` を import して使う（解釈を 2 か所に持たない）。

#### 作業

1. 2.2 節の食い違いを、作者に確認して直す（D-2）。array（ソースは keyence、テストは omron のみ）、math（ソースは omron のみ、テストは keyence）、`sys`（テストだけが keyence）。
2. `scripts/target_table.py` を追加する。ヘッダーから、対象ごとの宣言の表（Markdown）を出力する。README.md の表の部分を `<!-- target-table:begin -->` と `<!-- target-table:end -->` で囲み、`--check` で README.md と一致するかを確かめる。CI の `lint` ジョブで `--check` を実行する。
3. 確認済みの列は、PR の L3・L4 の記録から、手で書く。PR-10 の時点では、作者が過去に確かめた範囲を聞いて埋め、分からないものは「未確認」にする。以降、L3・L4 を行った PR は、この列も更新する。
4. lint に `target-consistency` を追加する。
5. 三菱の扱いを決めて反映する（D-3）。
   - 対応しない場合（推奨）: README.md に未対応と明記し、`sys_conv.iec` の `// TODO:` を「未対応」のコメントに変える。`sys.iec` の注記と合わせる。
   - 対応する場合: 対応する範囲を決め、ヘッダーに `-t mitsubishi` を足す。`sys.iec` の注記にある `var_in_out` の制約を先に調べる。この計画の工数には含めない。
6. README.md の「概要」の「Sysmac Studio を対象」の記述を、表を指す文に直す。CODESYS の扱い（`sys_config.iec` に分岐がある）も表に書く。

#### 完了の条件

- README.md にターゲットの表があり、CI がヘッダーとの一致を検査する。
- 宣言の食い違いが 0 件で、`target-consistency` が通る。
- 三菱の扱いが README.md に書かれ、`// TODO:` が残っていない。

### 3.7 項目 11: 利用例（PR-11）

#### 目的

テンプレート（container・項目 5 の signal）の具体化の仕方を、テストを読まなくても分かるようにする。今の README.md の取り込みの手順は、string_lib の 1 例だけである。

#### 設計

- ディレクトリ名は、JiecUnit（`vendor/jiecunit/samples/`）に合わせて `samples/` にする（D-5）。
- 1 例 1 ディレクトリにし、`.iec` と短い `README.md`（目的・XML の生成コマンド・Sysmac Studio での使い方）を置く。
- 各 `.iec` の先頭に、ほかのエントリファイルと同じ `$ jiecc` の行を書く。

#### 作業

1. `scripts/run_tests.py` の探索（`_discover`）に `samples/` を加え、`src/` と同じく、ヘッダーに `$ jiecc` の行があるファイルをコンパイルする。lint の既定の対象にも `samples/` を加える。
2. 例を追加する。
   - `samples/hashmap_string_to_dint/`: `hashmap_template.iec` の具体化（`test/container/hashmap/hashmap_dint.iec` を元に、各マクロの意味をコメントで説明する）と、プログラムからの使い方。
   - `samples/ringbuffer_recent_values/`: `ringbuffer_template.iec` で直近 N 件の値を保持する。
   - `samples/random_process_variation/`: Mersenne Twister で工程の変動（正規分布）を作る。
   - `samples/modbus_crc/`: CRC16 で電文に CRC を付ける（PR-9 の関数を使う）。
3. README.md の目次と「取り込む方法」から `samples/` へリンクする。
4. PR-12・PR-14 は、それぞれの PR で `samples/moving_average/`・`samples/pid_loop/` を追加する（PR-13 の補間は、README.md の使用例で足りるので追加しない）。

#### PR-11 の実装の結果と、計画から変えたこと

PR-11 は、ブランチ `feature/samples`（`feature/crc16` の上）で実装した（マージの前）。PR-10 は作者の判断（D-1〜D-3）を待つので、先に PR-11 を実装した。

- 各例は、1 つのプログラム（`program`）で、入力と出力を内部変数（`var`）にした。Sysmac Studio のプログラムは、入出力の引数を持たないためである。利用者は、ウォッチウィンドウやほかのプログラムから変数を設定する。
- `scripts/pou_inventory.py` は、`samples/` の XML を読まない（利用例はライブラリではないので、テストを求めない）。lint（ソースと XML）は、`samples/` も検査する。
- `modbus_crc` の電文の組み立てと応答の確認は、同じコードをテストに写して jier で実行し、`01 03 00 00 00 0A C5 CD` になることと、1 バイトを変えた応答を誤りと判定することを確かめた。ほかの 3 例は、コンパイルと lint だけで確かめた（L3 は作者が行う）。
- 生成した XML（`samples/**/*.xml`）を `.gitignore` に加えた。

#### 完了の条件

- 全例が CI でコンパイルでき、lint を通り、README.md からたどれる。
- 少なくとも 1 例を、Sysmac Studio に取り込んで動かし、PR のテンプレートの L3 の欄に書く。

### 3.8 項目 5: FA 向けの機能（PR-12〜PR-14）

#### 目的

FA の制御プログラムで毎回書かれがちな部品を、テスト付きで、ベンダーをまたいで同じ書き方で使えるように提供する。NJ/NX には役割が重なる標準命令がある（2.6 節）。

#### 共通の設計

- 状態を持つものは `function_block` にする。内部にバッファを持つもの（移動平均・メディアン）は、container と同じくテンプレートにし、容量をマクロで指定する。
- 周期に依存するもの（`Signal_lowPass`・`Signal_rateLimiter`・`Control_pid`・`Control_ramp`）は、サンプリング周期を引数 `sample_time: lreal`（秒）で受け取る。タスク周期を内部で仮定しない。
- 引数の誤り（容量 0、`sample_time <= 0`、上限 < 下限、`x_table` が昇順でないテーブル）は `eno := false` で通知する。エラーのときの出力は、次のとおり。
  - `function_block`: 出力は前回の値を保ち、内部の状態も更新しない。
  - `function`（`Signal_deadband`・`Interp_linear1d`・`Interp_linear2d`）: 戻り値は既定値（0.0）になる（状態を持たないので、前回の値は保てない）。
- 初期化は、入力 `reset: bool` が真のときに内部状態を初期値に戻す形で統一する。
- 状態を持つもののテストは `TEST_M` で周期を進めながら確かめる（PR-6 の確認の後）。期待値は Python（numpy・scipy）で同じ入力から求め、求め方をコメントに書く。

#### PR-12: `src/signal/`

| POU | 種類 | 仕様 |
|---|---|---|
| `Signal_movingAverage` | テンプレート（`function_block`） | 単純移動平均。容量 N はマクロ。満たされるまでは、入った個数の平均を出す |
| `Signal_lowPass` | `function_block` | 一次遅れ。`alpha = sample_time / (time_constant + sample_time)` |
| `Signal_median` | テンプレート（`function_block`） | メディアンフィルタ。N は奇数に限る（偶数はエラー） |
| `Signal_deadband` | `function` | 不感帯。NJ/NX の `Band` と同じ出力の定義（範囲内は 0、範囲外は境界からの差） |
| `Signal_rateLimiter` | `function_block` | 変化率の上限（上昇・下降を別に指定） |
| `Signal_hysteresis` | `function_block` | オン・オフの閾値を別に持つ比較 |

#### PR-12 の実装の結果と、計画から変えたこと

PR-12 は、ブランチ `feature/signal`（`feature/samples` の上）で実装した（マージの前）。

- ファイルは、`src/signal/signal.iec`（関数 1 個とファンクションブロック 3 個。ヘッダーのあるエントリファイル）と、テンプレート 2 個（`moving_average_template.iec`・`median_template.iec`）。テンプレートが作る名前は `Signal_movingAverage_<名前>`・`Signal_median_<名前>`（array のテンプレートと同じく、名前を末尾に付ける）。
- ファンクションブロックは、関数と同じく `_PROLOGUE_OF_FUNCTION_()` で `en` / `eno` を宣言する（`src/` で初めてのファンクションブロック）。
- 容量の誤り（移動平均の 0 以下、メディアンの偶数）は、実行時の `eno` ではなく、`{#error}` でコンパイルを止める。容量はマクロなので、コンパイルの時点で分かる。jiecc でエラーになることを確かめた。
- `Signal_lowPass`・`Signal_rateLimiter` は、`reset` の直後（と最初の呼び出し）に出力を入力に合わせる。
- 移動平均は、呼び出しのたびに保持している値の和を計算し直す（丸め誤差がたまらない）。メディアンは、保持している値を挿入ソートで並べる。
- テストは `test/signal/test_signal.iec` の 1 ファイル（6 個）。`Signal_lowPass` と `Signal_rateLimiter` は `TEST_M` で周期を進めて確かめ、時間に依存しないほかの 4 個は、1 周期の中で何度も呼んで確かめる。jier で通り、`scripts/jier_required.txt` に載せた。
- 利用例 `samples/moving_average/` を追加した。

#### PR-13: `src/interp/`

| POU | 種類 | 仕様 |
|---|---|---|
| `Interp_linear1d` | `function` | `x_table`・`y_table`（`var_in_out`、`array[*] of lreal`）と、使う点の数 `count: dint := -1`（-1 は配列の全要素）による折れ線の線形補間。PLC のテーブルは末尾を使わないことが多いので、`count` で使う範囲を決める。1 回の走査で、`x_table` の先頭 `count` 点が狭義の昇順であることの確認と、区間の探索を行う（O(count)。PLC のテーブルの大きさ（数十〜数百点）を想定し、点の数が大きいときの計算時間を doc プラグマに書く）。範囲外は引数 `extrapolate: bool` で、端の値で止めるか外挿するかを選ぶ。`var_in_out` なので、定数の配列はそのまま渡せない（変数に入れて渡す）ことを doc プラグマに書く |
| `Interp_linear2d` | `function` | 2 次元テーブルの双線形補間。軸の点の数を引数で受け取る。範囲外は端の値で止める |

#### PR-13 の実装の結果と、計画から変えたこと

PR-13 は、ブランチ `feature/interp`（`feature/signal` の上）で実装した（マージの前）。

- 2 つの関数は `src/interp/interp.iec` の 1 ファイルにまとめ、区間の探索と昇順の確認を内部の関数 `private_Interp_segment` で共通にした（1 回の走査）。
- `Interp_linear1d` は、`x_table` と `y_table` の下限が違う場合と、`count` がどちらかの配列の要素数を超える場合も、エラーにする。`Interp_linear2d` は、軸の点の数を `x_count`・`y_count`（-1 は全要素）で受け取り、`table` の下限が軸の下限と違う場合をエラーにする。
- テスト `test/interp/test_interp.iec` は、手で確かめられる値（折れ線の点と、双線形補間で正確に再現される `f(x, y) = 10x + y/10`）で、範囲内・点の上・範囲外（外挿の有無）・`count`・下限が 0 でない配列・エラーを確かめる。jier で通り、`scripts/jier_required.txt` に載せた。
- 計画どおり、利用例は追加せず、README.md に使用例を書いた。

#### PR-14: `src/control/`

| POU | 種類 | 仕様 |
|---|---|---|
| `Control_pid` | `function_block` | 並列形の PID。出力の上下限、アンチワインドアップ（上下限に達したら積分を止める）、手動・自動の切替（切替時に出力が飛ばない）、微分は測定値に対して行う（微分の先行）。不完全微分のフィルタ（時定数）を持つ |
| `Control_ramp` | `function_block` | 目標値へ、指定した変化率で近づける |

- PID を提供するかどうかと形式（並列形か標準形（ISA）か）は、作者の判断を待つ（D-6）。判断が出るまで PR-14 には着手しない。
- `Control_pid` のテストは、一次遅れの対象（`Signal_lowPass` で模擬）を組み合わせ、ステップ応答の値と、出力が飽和したときに積分が止まることを確かめる。

#### 作業の順序

signal → interp → control の順に、モジュールごとに PR を分ける。各 PR で、README.md の節と、新しいテストファイルの `scripts/jier_required.txt` への登録を行う。PR-12・PR-14 は `samples/` の例も追加する（3.7 節）。

#### 完了の条件

- 全 POU のテストが `run-required` ジョブで通り、L3 の結果が PR にある。
- README.md に、NJ/NX の標準命令との違い（2.6 節）を書く。

### 3.9 項目 12: Release に XML を添付する（PR-15）

#### 目的

利用者が Jiecc を用意しなくても、取り込み用の XML をダウンロードできるようにする。

#### 現状

GitHub の Release は 8 件（`v4.0.0`・`v3.4.0` など）あり、添付ファイルは 0 件である。作り方の記録はない（GitHub の画面で作ったとみられる）。

#### 設計

- 作者が Release を作る手順は変えない。`.github/workflows/release.yml` を追加し、`release` の `published` の event と、`workflow_dispatch`（入力: タグ名。作り直しに使う）で動かす。
- ジョブを 2 つに分け、権限を分ける。
  - `build` ジョブ（`permissions: contents: read`）:
    1. タグを checkout する（`actions/checkout` の `ref` に、`release` の event ではそのタグ、`workflow_dispatch` では入力のタグを指定する）。
    2. タグ名と `VERSION` を比べ、`v` + `VERSION` と一致しなければ失敗にする。タグ名は、`run:` の中に `${{ }}` で直接埋め込まず、`env:` で環境変数として渡す（細工したタグ名でのコマンドの注入を防ぐ）。
    3. `setup-jiecc` で Jiecc を取得し、`run_tests.py --compile-only --output-dir out src` で `src/` の XML を作る。
    4. ターゲットごとに zip にまとめる（`jieclib-<version>-omron.zip`・`jieclib-<version>-keyence.zip`）。zip の中は `src/` からの相対パスにする。使った Jiecc の版（`jiecc --version`）と、取り込みの注意（下記）を書いたテキストを同梱する。
    5. zip を artifact として保存する。
  - `upload` ジョブ（`permissions: contents: write`）: `build` の artifact を取り、`gh release upload <tag> <files> --clobber` で添付する。`env: GH_TOKEN: ${{ github.token }}` を指定する。ダウンロードした Jiecc は、このジョブでは実行しない（書き込みの権限を持つトークンを、版を固定していない外部のバイナリに触れさせない）。
- 各 XML は、include したファイルの POU（`sys.iec` の `Console_*` など）を含む（2.3 節）。そのため、複数の XML を 1 つのプロジェクトに取り込むと、同じ POU の定義が重なる。Sysmac Studio での振る舞いを PR-15 で確かめ（L3）、取り込みの注意として同梱のテキストと README.md に書く。
- XML に入る作成日時（`ContentHeader` の `creationDateTime`）や改行が、Windows と Linux で変わるかを確かめ、Release の XML は Linux で作ると決める。

#### 作業

1. `release.yml` を追加する。actions は、`ci.yml` と同じくコミットの SHA で固定する。
2. CONTRIBUTING.md の「バージョン管理」に、Release を公開すると XML が添付されることを追記する。README.md の「Sysmac StudioでJiecLib内のライブラリを取り込む方法」に、Release から XML を取る方法を追記する。
3. 動作は、フォークのリポジトリで確かめる。成功の経路は、`VERSION` と一致するタグ（フォークの `VERSION` に合わせた `v4.0.0` など）で、失敗の経路は、一致しないタグ（`v0.0.0-test`）で確かめる。

#### 完了の条件

- Release を公開すると、ターゲットごとの zip が添付される。
- `VERSION` と食い違うタグでは失敗し、何も添付しない。
- 取り込みの注意が README.md と zip にある。

#### リスク

- CI の Jiecc は版を固定していない（最新版を取得する）。添付した XML がどの版で作られたかは、同梱したテキストで分かるようにする。版の固定そのものは、この計画の対象外。

## 4. 依存関係

```
PR-1 ──┬──> PR-2 ──┬──> PR-3 ──> PR-4 ──> PR-7
       │           ├──> PR-5 ──> PR-8 ──┬──> PR-12 ──> PR-14 (D-6 も必要)
       │           │                    └──> PR-13
       │           ├──> PR-6 ──────────────> PR-12
       │           ├──> PR-9 ──> PR-11 ───> PR-12
       │           └──> PR-15
       ├──> PR-3
       ├──> PR-10
       └──> PR-11
```

- PR-1 は最初にマージする（結論を参照）。
- PR-2 は、新しいテストを `scripts/jier_required.txt` に載せる仕組みを作るので、テストを追加する PR（PR-5・PR-6・PR-9 など）の前に入れる。
- PR-3 と PR-4 は、どちらも CI の `compile` ジョブを変える。PR-3 が `--output-dir` と lint を足し、PR-4 はその後に棚卸しの検査を足す。
- PR-12 は、PR-6（`TEST_M` の確認）・PR-8・PR-11（`samples/` の探索）のすべてを必要とする。

## 5. リスクの一覧

| No. | リスク | 影響 | 対策 |
|---|---|---|---|
| R-1 | jier が既存の全 112 ファイルで失敗する（83 はエラー、29 は時間切れ。2.3 節）ため、既存のテストファイルに足したテストを L2 で確かめられない | 新しいテストの退行に気づけない | 新しいテストは jier で通る別のファイルに分け、`run-required` ジョブで必ず通す（1.2 節） |
| R-2 | jiecc のコンパイルはベンダーの制約を検査しない | 宣言したターゲットで取り込めない | lint の名前・型の規則と、L4 の記録（3.6 節） |
| R-3 | CI の Jiecc が最新版で変わる | ある日 CI が壊れる。Release の XML の版が分からない | Release に Jiecc の版を同梱（3.9 節）。版の固定は対象外 |
| R-4 | `TEST_M` を JiecLib で初めて使う | jier や Sysmac Studio で想定どおり動かない | PR-6 の最初に、小さなテストで両方を確かめ、`TEST_M` を使う PR-12・PR-14 を PR-6 の後にする |
| R-5 | NaN・無限大の扱いがベンダーで違う | 関数の結果が環境で変わる | PR-8 の最初の調査で方針を決める |
| R-6 | Windows で `--preprocess-only` が cp932 で失敗する | 前処理の出力を使う道具が Windows で動かない | 道具は XML を読む（2.3 節） |
| R-7 | lint の規則を後から足すと、既存コードの修正が大きくなる | PR が膨らむ | 規則は PR-1・PR-3 で出し、後から足すのは PR-10 の `target-consistency` だけにする。警告の規則は基準値で管理し、既存の違反を一度に直さなくてよいようにする |
| R-8 | L3・L4 は手動で、行わなくても CI は通る | 開発環境で動かないものが入る | `pr-body` ジョブで、L3・L4 の欄の書式（合格 / 不合格 / 未実施と理由）を検査する。内容が本当かは機械では確かめられないので、人のレビューで確かめる。未実施は README.md の表で「未確認」として見えるようにする（1.2 節） |
| R-9 | jier はテストが終わった後も周期数まで回り続ける | 周期数を大きくすると時間切れになり、小さくすると `TEST_M` のテストが終わらない | ファイルごとに周期数を指定できるようにし（PR-2）、必要な周期数を測って載せる。足りないときは、テストの数の一致の検査で検出する |
| R-10 | `run_tests.py` は、時間切れのときに jiecc の子のプロセスを残し、終わらなくなる（2.3 節） | CI の `run` ジョブや `run-required` ジョブが、ジョブの制限時間まで止まる | PR-2 の最初に直し、`--timeout` を小さくして確かめる（3.2 節） |

## 6. 未決事項の一覧

「判断の期限」は、その判断がないと進められない時点を表す。「推奨案で進める」は、推奨案で作業を進め、判断が違えば後で変える。

| No. | 事項 | 推奨 | 理由 | 判断の期限 |
|---|---|---|---|---|
| D-1 | CONTRIBUTING.md の名前の制約（1 文字の名前など）と、keyence の宣言が食い違っている（keyence を宣言したファイルに 55 件の違反。2.5 節）。どちらを直すか。あわせて、「要素名」が局所変数を含むか | 先に、keyence を宣言した string_lib を KV Studio に取り込んで確かめる。取り込めれば規則が広すぎるので、CONTRIBUTING.md を実際の制約に合わせて直す。取り込めなければ、宣言を外すか名前を直す（公開 API の引数名を変えるなら、破壊的変更として次のメジャー版に回す）。規則は keyence を宣言したファイルだけに当てる | 全ファイルに当てると、omron だけのライブラリの既存の公開 API の引数名を変えることになる | KV Studio での確認は、KV Studio の環境を持つ作者が行う。判断は PR-10 のマージの前（それまで `keyence-names` は警告のまま） |
| D-2 | array・math・`sys` の宣言の食い違い（2.2 節）を、どちらに揃えるか | KV Studio で確かめたものだけを keyence にする | 宣言は「確かめた」ことの表明として扱う（3.6 節） | PR-10 のマージの前 |
| D-3 | 三菱に対応するか | 対応しないと明記する | 宣言したファイルが 1 つもなく、`sys.iec` に完全には対応しない旨の注記がある | PR-10 のマージの前 |
| D-4 | math の新しい関数の名前と引数名 | 3.4 節の表のとおり（キャメルケース、1 文字の引数名を使わない） | 既存の `Math_floor` / `Math_atan2` の名前の付け方と、命名規則に合わせる | PR-8 のマージの前 |
| D-5 | 利用例のディレクトリ名 | `samples/` | JiecUnit と揃える | PR-11 のマージの前 |
| D-6 | `Control_pid` を提供するか。提供するなら形式（並列形か標準形（ISA）か） | 提供する。並列形にする | NJ/NX の `PIDAT` があるが、他ベンダーでも同じ書き方で使えることに価値がある。並列形は係数の意味が分かりやすい | PR-14 の着手の前 |
| D-7 | doc プラグマの書き方を `(*{doc ...}*)` に揃えるか | 揃える（6 ファイル、49 か所の書き換え） | 1,196 か所が `(*{doc ...}*)` で、揃えるのは小さい | 決定：揃える（PR-1） |
| D-8 | Release への XML の添付で、keyence 用の zip も作るか | 作る | 宣言したファイルだけが入る。宣言の意味（3.6 節）と合う | PR-15 のマージの前 |
| D-9 | `hex_nibble`（`hex.iec` の内部の補助関数）の名前を `private_hex_nibble` に変えるか | 変える。ただし次のメジャー版で行う | 公開の名前に見えるが、内部用の補助関数である。名前を変えると、使っている利用者のプログラムが壊れる | 推奨案で進める（それまでは棚卸しの「テストなしと認めた POU」に置く） |
| D-10 | doc プラグマとコメントの言語。CONTRIBUTING.md は英語と定めているが、`src/` の doc プラグマの 890 か所（75 ファイル）が日本語 | 規約（英語）は残す。新しいコードは英語で書き、既存の日本語は `doc-language` の警告の基準値で管理して、増やさない。既存の翻訳は、この計画では行わない | 既存を一度に翻訳するのは大きく、利用者への効果が小さい。規約を日本語に緩めると、英語の利用者が読めない | 推奨案で進める |
| D-11 | `nextPoisson` の λ の上限の値 | 500 | `EXP(-lambda)` は λ が約 745 を超えるとアンダーフローする。1 回の呼び出しで約 λ 回ループするので、PLC の周期を考えて余裕を持たせる | PR-6 のマージの前（PR-6 は推奨案の 500 で実装した） |
| D-12 | `keyword-case` で、標準関数の名前（`sin`・`exp` など）も小文字に揃えるか | 揃える（18 か所の書き換え） | AGENTS.md の「キーワード」には入らないが、書き方を 1 つにした方が、生成 AI でも人でも迷わない。書き換えは小さい | 決定：揃える（PR-1） |
| D-13 | `run_tests.py` の既定の `--max-cycles`（100000）を下げるか | PR-2 で、エラーで止まらない 29 ファイルの必要な周期数を測り、そのうちの最大値の 2 倍に下げる | jier は周期数まで回り続けるので、既定値が大きいと `run` ジョブが時間切れになる（2.3 節）。`TEST_M` のテストは、ファイルごとの指定で周期数を増やせる。足りなくなっても、テストの数の一致の検査（3.2 節）で検出できる | PR-2 のマージの前（PR-2 は推奨案で実装した。最大値は 1000 で、既定値は 2000） |

## 付録: 計測の方法

2 章の値は、次の方法で求めた。計測に使ったスクリプトはリポジトリに入れていない（PR-1〜PR-4 で正式な道具にする）。別のレビューで、件数と jiecc の挙動を数え直して確かめた。

- ターゲットごとのコンパイル: `src/` のエントリファイル 97 件を、`jiecc <file> -I. -I./src -o <xml> -t <target>` で 4 ターゲットについてコンパイルし、終了コードと `error: ` の行を確かめた。
- jier のベースライン: `python scripts/run_tests.py --timeout 600`（全件のコンパイルと jier の実行）。時間切れの後に残ったプロセスは、プロセスの一覧（起動の時刻・親のプロセス ID・コマンドライン）で確かめた。周期数と時間の関係は、`test/math/test_floor.iec` を `--max-cycles` 1000・3000・100000 で単独で実行して確かめた（1000 周期あたり約 4.5 秒）。
- `Math_floor`: `{#include <math/floor.iec>}` だけのテストを作り、`jiecc --run <file> -I. -I./src -I./vendor/jiecunit -D_TEST_ --max-cycles 1000` で実行した。
- PP29・PP23: 1 行の doc プラグマやコメントを持つ小さなファイルをコンパイルして確かめた。
- CRC の期待値: Python で、ビット単位の CRC の計算を書いて求めた。
- 規約の違反の件数と POU の棚卸し: 全エントリファイルとテストを omron でコンパイルした XML と、ソースを読む簡易なスクリプトで数えた。
