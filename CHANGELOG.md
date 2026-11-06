# 変更履歴 / Changelog

このファイルは、3.4.0 以降の変更を記録します。それ以前の変更は、Git のタグ（`v1.2.0` 〜 `v3.2.0`）と GitHub のリリース・Pull Request（https://github.com/yunos0987/jieclib）を参照してください。

## [Unreleased]

### 追加 / Added

- math に 13 個の関数を追加しました（1 関数 1 ファイル）。丸めの `Math_ceil`・`Math_trunc`・`Math_round`・`Math_roundHalfEven`・`Math_roundTo`、`Math_clamp`・`Math_lerp`・`Math_sign`・`Math_hypot`・`Math_fmod`、整数の `Math_gcd`・`Math_lcm`、比較の `Math_isClose` です。テストは `test/math/test_<名前>.iec` で、すべて jier で実行できます（`scripts/jier_required.txt` に載せました）。NaN と無限大を渡したときの結果は未定義です。
- hash に CRC-16（`CRC16_modbus`・`CRC16_ccittFalse`・`CRC16_xmodem`・`CRC16_toHex`）とチェックサム（`Checksum_sum8`・`Checksum_xor8`・`Checksum_lrc`）を追加しました。Modbus RTU・シリアル通信の電文に使えます。`shl` / `shr` を使わないので、jier でもテストを実行できます（`test/hash/test_crc16.iec`・`test/hash/test_checksum.iec`）。
- ライブラリの使い方を示す利用例 `samples/` を追加しました（ハッシュマップの具体化、リングバッファ、乱数による工程の変動、Modbus RTU の CRC）。README.md の「利用例（samples）」から参照できます。`scripts/run_tests.py` は、`samples/` の、先頭コメントに `$ jiecc` の行があるファイルもコンパイルします。
- 信号処理のライブラリ `src/signal/` を追加しました。`Signal_deadband`（不感帯）、`Signal_lowPass`（一次遅れ）、`Signal_rateLimiter`（変化率の上限）、`Signal_hysteresis`（ヒステリシス付き比較）と、テンプレートの移動平均（`moving_average_template.iec`）・メディアンフィルタ（`median_template.iec`）です。テスト `test/signal/test_signal.iec` は jier で実行でき、利用例 `samples/moving_average/` もあります。
- 補間テーブルのライブラリ `src/interp/` を追加しました。`Interp_linear1d`（折れ線の線形補間。使う点の数・外挿の有無を指定できる）と `Interp_linear2d`（2 次元テーブルの双線形補間）です。テスト `test/interp/test_interp.iec` は jier で実行できます。
- GitHub の Release を公開すると、`src/` の XML をターゲットごとの zip（`jieclib-X.Y.Z-omron.zip`・`jieclib-X.Y.Z-keyence.zip`）にして添付する workflow（`.github/workflows/release.yml`）を追加しました。Jiecc を用意しなくても、XML を取り込めます。zip には、使った Jiecc の版と取り込みの注意が入ります。
- 制御のライブラリ `src/control/` を追加しました。`Control_pid`（並列形の PID。出力の上下限、アンチワインドアップ、手動・自動の切替、微分先行、不完全微分）と `Control_ramp`（ランプ）です。テスト `test/control/test_control.iec` は jier で実行でき、利用例 `samples/pid_loop/` もあります。

### 修正 / Fixed

- `Math_floor` が、絶対値が 2^63 以上の値で誤った値を返す不具合を直しました（例: `Math_floor(1.0e19)` が `-8.446744073709552e+18`、`Math_floor(1.0e300)` が `0.0` を返していました）。`lint` に変換して切り捨てていたため、`lint` の範囲を超える値であふれていました。絶対値が 2^52 以上の `lreal` は必ず整数なので、その値をそのまま返します。テストは `test/math/test_floor_large.iec` です。
- `MersenneTwister_nextPoisson` と `Xorshift32_nextPoisson` は、`lambda` が 500 を超えると `eno := false` を返すようにしました。これまでは上限がなく、`lambda` が約 745 を超えると `exp(-lambda)` が 0 になり、`lambda` と関係のない値を返していました。また、1 回の呼び出しで約 `lambda + 1` 個の乱数を使うため、`lambda` が大きいとタスクの周期を圧迫します。

- `MersenneTwister_next` と `Xorshift32_next` は、`bits` が 1〜32 の範囲外のとき `eno := false` を返すようにしました。生成器の状態は変えません。これまでは範囲を確かめずに `shr(x, 32 - bits)` を計算していました。

### その他 / Other

- 対応ターゲットの宣言を整理しました。ソースとテストで食い違っていた `keyence` の宣言を外しました（`src/array/array.iec`・`src/array/sort.iec`、`test/math/test_floor.iec`・`test/math/test_atan2.iec`、`test/test_sys.iec`・`test/test_sys_conv.iec`）。KV Studio で確かめた記録がないためです。確かめた後で、ソースとテストの両方に宣言を戻します。CI は、これらを keyence ではコンパイルしなくなります。
- README.md に「対応ターゲット」の節を設け、ライブラリごとの宣言の表（`scripts/target_table.py` で作り、CI が一致を確かめる）と、開発環境で確かめた結果の表を載せました。三菱電機（mitsubishi）には対応しないことを明記しました。
- lint に `target-consistency`（同じライブラリのソースとテストで、宣言したターゲットが同じ）を追加しました。
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
- `scripts/lint.py` に `--xml-dir DIR` を追加しました。`run_tests.py --compile-only --output-dir DIR` でコンパイルした XML を読み、テンプレートが作る名前も含めて、名前と型の規則（`left` などの予約語、`p_` の接頭辞、可変長配列は `var_in_out` だけ、構造体を返す関数、エイリアス型、64 バイトを超える POU 名、キーエンスの名前の制約）を検査します（`scripts/lint_xml.py`）。既存のコードの違反は、キーエンスの名前の制約の 54 件（警告。`scripts/lint_baseline.json` に記録）だけです。CI の `compile` ジョブが、コンパイルの後にこの検査を行います。
- テストのない公開の POU を検出する `scripts/pou_inventory.py` を追加しました。CI の `compile` ジョブが、コンパイルした XML で検査します。今テストのない 31 個（array の dint 版 8 個、stats の 16 個、random の 2 個、`Console_print`、`hex_nibble`、恒等変換 3 個）は、理由と一緒に `scripts/pou_inventory_allow.txt` に載せました。
- 乱数の分布のテスト `test/random/test_random_distribution.iec` を追加しました。各生成器の `nextIntInRange`・`nextRealInRange`・`nextBernoulli`・`nextGaussian`・`nextExponential`・`nextPoisson` について、固定したシードで 10,000 個を生成し、標本平均・標本分散・出現回数（カイ二乗）が理論値の許容幅に収まることを確かめます。生成器が幅なしの `shl` / `shr` を使うため、このテストは jier では実行できません（PLC の環境で実行します）。
- JiecUnit の `TEST_M`（複数の周期にわたるテスト）が jier で動くことを確かめるテスト `test/test_jiecunit_test_m.iec` を追加しました。
- テストのなかった公開の POU のテストを追加しました（array の dint 版 8 個、`stats.iec` の基本統計 13 個、`Stats_p_value_*` 3 個、`next(bits)` 2 個、`Console_print`）。`scripts/pou_inventory_allow.txt` に残るのは、内部の補助関数 `hex_nibble` と恒等変換 3 個だけです。
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
