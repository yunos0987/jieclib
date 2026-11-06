# JiecLib 改善計画（v4.0.0 以降）

v4.0.0 の時点でリポジトリを見直し、足りないものを洗い出して計画にしました。対象は次の 8 項目です。

| No. | 項目 | 区分 | 想定する版 |
|---|---|---|---|
| 13 | 規約の lint を CI に入れる | 基盤 | 4.1.0 |
| 3 | テストの不足を埋める | 品質 | 4.1.0 |
| 4 | math ライブラリを拡充する | 機能 | 4.1.0 |
| 6 | CRC16 などのチェックサムを追加する | 機能 | 4.1.0 |
| 7 | 対応ターゲットを明記する | 文書 | 4.1.0 |
| 11 | 利用例（`examples/`）を追加する | 文書 | 4.2.0 |
| 5 | FA 向けの機能（信号処理・制御・補間）を追加する | 機能 | 4.2.0 |
| 12 | リリースを自動化する | 運用 | 4.2.0 |

この計画の対象外にした項目は次の 4 つです。jier の run ジョブの必須化、CI の Jiecc の版の固定、名前の接頭辞の統一、CHANGELOG の `[Unreleased]` 節の追加です。

## 進め方

- フェーズ 1（13 → 3）で検査とテストの土台を作り、フェーズ 2（4・6・7）とフェーズ 3（11・5・12）で機能と文書を足す。
- 各項目は `develop` で 1 つ以上の PR にまとめ、`main` へマージする。版は CONTRIBUTING.md の手順で、`release vX.Y.Z` のコミットでだけ上げる。
- 新しい POU は既存の規約（CONTRIBUTING.md）に従う。`eno` でエラーを通知し、POU・引数・型に doc プラグマを書き、テストは `TEST_S` に 1 関数の事実をまとめる。
- 新しいテストも、`python scripts/run_tests.py` でコンパイルが通ることを合格の条件にする。jier では 83 ファイルが既知の理由で失敗するため（CHANGELOG.md の 4.0.0「既知の問題」）、jier で実行できないテストは Sysmac Studio のシミュレータで確認し、その旨を PR に書く。

## 調査で分かった現状

- `src/` の `.iec` は 126 ファイル、`test/` は `TEST_S` が 494 個ある。
- ヘッダーのコメントに `-t keyence` がある `src/` のファイルは 8 つ（`array/array.iec`、`array/sort.iec`、`random/lcg.iec`、`random/mersenne_twister.iec`、`random/xorshift32.iec`、`string_lib/` の 3 ファイル）。`run_tests.py` はヘッダーのターゲットごとにコンパイルするため、CI はこの 8 つを keyence でもコンパイルしている。
- `-t mitsubishi` のファイルは 1 つもない。`src/sys.iec` に「Mitsubishi は完全には対応しない」という注記があり、`src/sys_conv.iec` の `_MITSUBISHI` の分岐は `// TODO:` のままである。
- math のテストは `test_floor`（`EXPECT` 47 個）と `test_atan2`（`EXPECT` 70 個）、string_lib のテストは全 API を扱う 27 個の `TEST_S` があり、量は足りている。v4.0.0 の見直しで「薄い」と書いたのは誤りだった。
- テストを書く規約（`// Fact:` の 1 行コメントと AAA 形式）に従っていないテストファイルが多い。`TEST_S` を含む 103 ファイルのうち 77 ファイルに `// Fact:` がない（math・random・hash・linalg・stats・vector など）。
- doc プラグマの書き方は 2 通りある。`(*{doc ...}*)`（例: `src/hash/crc32.iec`）と `{doc ...}`（例: `src/math/floor.iec`）。言語も日本語と英語が混ざっている。
- FA でよく使う信号処理・制御・補間の機能は、`src/` に 1 つもない。`round`・`ceil`・`clamp` に相当する関数もない。
- `run_tests.py` は XML を一時ディレクトリに出力して捨てる。リリース用に XML を残す手段がない。

## 13. 規約の lint を CI に入れる

### 目的

CONTRIBUTING.md と AGENTS.md の規約のうち、機械的に判定できるものを CI で検査する。レビューでの見落としをなくし、後のフェーズで追加するコードにも同じ基準を当てる。

### 作業

1. `scripts/lint.py` を追加する。標準ライブラリだけを使い、`run_tests.py` と同じく引数でファイルやディレクトリを絞れるようにする。コメントと文字列リテラルを取り除いてから判定する。
2. 検査する規則（エラー）:
   - IEC 61131-3 のキーワードが小文字であること（AGENTS.md）。
   - 禁止された名前を使っていないこと（CONTRIBUTING.md「命名規則」）。`left` / `right` / `len` / `cmp` / `dec`、`p_` / `P_` で始まる要素名、`h` / `H` で始まり `_` を含まない変数名、`^[rRtTcC]\d+$` にあたる変数名、アルファベット 1 文字の要素名。`sys.iec` のマクロ `inc` / `dec` のように、定義の名前でないものは対象外にする。
   - POU 名が 64 バイト以内であること。
   - `//` コメントの最初の語が `{#` で始まらないこと（jiepp の PP30。AGENTS.md「既知の落とし穴」）。
   - doc プラグマにアポストロフィ（`'`）を含まないこと（jiepp の PP29）。
3. 検査する規則（警告。CI を失敗にしない）:
   - POU の直前に doc プラグマがあること。
   - テストの `TEST_S` に `// Fact:` コメントがあること。
4. 既存のコードで一度実行し、エラーの件数を数える。件数が少なければ同じ PR で直し、多ければ PR を分けて直す。エラーが 0 件になった時点で、CI にジョブを足す（`ci.yml` の `format` ジョブの後）。
5. CONTRIBUTING.md の「テストの実行」に `python scripts/lint.py` を、AGENTS.md の「テスト」に lint の実行を追記する。

### 完了の条件

- `python scripts/lint.py` が既存コードでエラー 0 件になり、CI の lint ジョブが通る。
- わざと違反を入れたファイルで、各規則がエラーになることを確かめる（`scripts/` のテスト、またはサンプル入力で確認）。

### 未決事項

- doc プラグマの書き方（`(*{doc}*)` と `{doc}`）と言語（日本語・英語）をどちらかに揃えるか。揃えるなら lint で検査するが、既存コードの書き換えが大きくなる。

## 3. テストの不足を埋める

### 目的

テストのない振る舞いと、既知の実装上の穴をテストで押さえる。

### 作業

1. 網羅の棚卸し: テンプレートはマクロで POU の名前を作るため、ソースの grep では POU の一覧を正しく取れない。コンパイルした XML から POU 名を集め、テストの XML から呼び出しを集めて突き合わせるスクリプトを作り、テストのない POU の一覧を出す（`scripts/` に置くか一時的な調査にするかは、出来を見て決める）。
2. 乱数の分布のテスト（`src/random/*_template.iec`）: 今は、引数のエラー、`prob=0/1` などの端の値、Python で求めた 1 つの値だけを確かめている。固定シードで N 個（例: 10,000 個）生成し、標本平均と標本分散が理論値の許容幅に収まることを確かめる。対象は `nextGaussian` / `nextExponential` / `nextPoisson` / `nextBernoulli` / `nextIntInRange` / `nextRealInRange` で、生成器ごと（Mersenne Twister・Xorshift32・LCG・LFSR32 のうち、その API があるもの）に行う。PLC のタスク周期の上限を超えないよう、N はシミュレータで確かめて決める。
3. `Math_floor` の大きな値: 実装は `trunc` で `lint` に変換するため、`|x| >= 2^63` では正しい値を返さない。テストを追加し、`|x| >= 2^52` では `x` をそのまま返すよう実装も直す（この範囲の `lreal` は必ず整数になる）。NaN と無限大の扱いも決めてテストにする。
4. 棚卸し（作業 1）で見つかった、テストのない POU のテストを追加する。
5. テストの書き方を規約（`// Fact:`・AAA 形式）に揃える作業は、テストの追加とは PR を分ける。lint（項目 13）の警告が減ることで進み具合を測る。

### 完了の条件

- 作業 1 の一覧で、テストのない公開 POU（`private_` で始まらないもの）が 0 件になる。0 件にしないものは、理由を一覧に残す。
- 乱数の分布のテストと `Math_floor` のテストが、コンパイルとシミュレータで通る。

## 4. math ライブラリを拡充する

### 目的

PLC のプログラムでよく使うのに、IEC 61131-3 の標準関数にない数値関数をそろえる。

### 作業

1. 追加する関数（名前の接頭辞は既存の `Math_` に合わせ、1 関数 1 ファイルの構成は `src/math/floor.iec` に合わせる）:

   | 関数 | 内容 |
   |---|---|
   | `Math_ceil` | 天井関数 |
   | `Math_trunc` | 0 方向への切り捨て（`lreal` を返す） |
   | `Math_round` | 四捨五入（0 から遠い方へ） |
   | `Math_roundHalfEven` | 偶数丸め（銀行丸め） |
   | `Math_roundTo` | 小数点以下 n 桁への丸め |
   | `Math_clamp` | 値を `[lo, hi]` に収める。`lo > hi` なら `eno := false` |
   | `Math_lerp` | 線形補間 `a + (b - a) * t` |
   | `Math_sign` | 符号（-1 / 0 / 1） |
   | `Math_hypot` | `sqrt(x^2 + y^2)` を桁あふれなしで求める |
   | `Math_fmod` | 浮動小数点の剰余（C の `fmod` と同じ符号） |
   | `Math_gcd` / `Math_lcm` | 最大公約数・最小公倍数（`lint`） |
   | `Math_isClose` | 相対誤差と絶対誤差による近さの判定（Python の `math.isclose` と同じ意味） |

2. `Math_floor` の修正（項目 3 の作業 3）と同じ方針で、大きな値・NaN・無限大を扱う。
3. 各関数にテストを書き、`test/math/test_math.iec` にまとめて登録する。期待値は Python の `math` モジュールで求め、コメントに書く。
4. README.md の math の表に追加する。

### 完了の条件

- 全関数のテストがコンパイルとシミュレータで通る。keyence でもコンパイルできる関数は、ヘッダーに `-t keyence` を書いて CI でも確かめる。

## 6. CRC16 などのチェックサムを追加する

### 目的

Modbus RTU・シリアル通信・機器の電文でよく使う誤り検出の符号を追加する。今は CRC32 だけである。

### 作業

1. `src/hash/crc16.iec` を追加する。`CRC32_bytes` / `CRC32_string` と同じ引数（`dat`・`offset`・`length`・`work`）で、16 進文字列を返す関数に加え、数値（`word`）を返す関数も用意する。電文に付けるには数値の方が使いやすい。
   - 多項式の種類: CRC-16/MODBUS（初期値 `16#FFFF`、反転あり）、CRC-16/CCITT-FALSE（多項式 `16#1021`、初期値 `16#FFFF`）、CRC-16/XMODEM（初期値 `16#0000`）。
   - 名前の案: `CRC16_modbus_bytes` / `CRC16_ccitt_bytes` / `CRC16_xmodem_bytes`（数値を返すもの）と、それぞれの `_hex` 版。
2. `src/hash/checksum.iec` を追加する。`Checksum_sum8`（8 ビット和）、`Checksum_xor8`（XOR）、`Checksum_lrc`（Modbus ASCII の LRC）。
3. テストの期待値は、各 CRC の仕様の確認値（入力 `'123456789'` の CRC）と Python で求めた値を使う。
4. README.md の hash の節に追加する。

### 完了の条件

- 確認値のテストが、全種類でコンパイルとシミュレータで通る。

### 未決事項

- 16 進文字列を返す関数を、CRC32 と同じく小文字にするか（CRC32 は小文字を返す）。

## 7. 対応ターゲットを明記する

### 目的

README.md は「Sysmac Studio が対象」と書いているが、実際は 8 つのライブラリが keyence でもコンパイルでき、mitsubishi の分岐も一部ある。利用者が、使えるターゲットを判断できるようにする。

### 作業

1. 各 `src/` のエントリファイルのヘッダーにある `-t` を集め、ライブラリごとのターゲットの表を README.md に載せる。表は手書きにせず、`scripts/` のスクリプトでヘッダーから生成し、CI で README.md との食い違いを検査する（lint の 1 規則にしてもよい）。
2. 「コンパイルできる」と「実機・シミュレータで確かめた」を分けて書く。keyence で動作を確かめたかどうかは、記録がないので作者に確認する。
3. mitsubishi の扱いを決める（未決事項）。
   - 対応しない場合: README.md に「未対応」と明記し、`sys_conv.iec` の `// TODO:` を `{#error}` か「未対応」のコメントに置き換える。
   - 対応する場合: 対応する範囲を決め、ヘッダーに `-t mitsubishi` を足して CI でコンパイルする。`sys.iec` の注記にある `var_in_out` の制約を先に調べる。
4. keyence でコンパイルできるのに `-t keyence` を書いていないライブラリがないか、全エントリファイルを keyence でコンパイルして確かめ、通るものはヘッダーに追記する。

### 完了の条件

- README.md にターゲットの表があり、CI がヘッダーとの一致を検査する。
- mitsubishi の扱いが README.md に書かれ、`// TODO:` が残っていない。

### 未決事項

- mitsubishi に対応するか（作者の判断）。

## 11. 利用例（`examples/`）を追加する

### 目的

README.md の取り込みの手順は string_lib の 1 例だけで、テンプレート（container・random の分布・項目 5 の FA 機能）の具体化の仕方は、テストを読まないと分からない。コピーして使える利用例を用意する。

### 作業

1. `examples/` を作り、1 例 1 ディレクトリにする。各ディレクトリに `.iec` と短い `README.md`（目的・XML の生成コマンド・Sysmac Studio での使い方）を置く。
2. 用意する例:
   - `examples/hashmap_string_to_dint/`: `hashmap_template.iec` の具体化（`test/container/hashmap/hashmap_dint.iec` を元に、マクロの意味をコメントで説明する）と、プログラムからの使い方。
   - `examples/ringbuffer_logging/`: `ringbuffer_template.iec` で直近 N 件の値を保持する。
   - `examples/random_simulation/`: Mersenne Twister で工程の変動（正規分布）を作る。
   - `examples/modbus_crc/`: 項目 6 の CRC16 で電文に CRC を付ける（項目 6 の後に追加）。
   - 項目 5 の FA 機能の例（項目 5 の後に追加）。
3. `scripts/run_tests.py` のコンパイルの対象に `examples/` を加え、CI で例が壊れていないことを確かめる。
4. README.md の目次と「取り込む方法」から `examples/` へリンクする。

### 完了の条件

- 全例が CI でコンパイルでき、README.md からたどれる。

## 5. FA 向けの機能（信号処理・制御・補間）を追加する

### 目的

FA の制御プログラムで毎回書かれがちな部品を、テスト付きで提供する。

### 作業

1. 新しいモジュールを 3 つ作る。状態を持つものは `function_block` にする。内部にバッファを持つものは、container と同じくテンプレート（容量をマクロで指定）にする。

   | モジュール | POU（案） | 内容 |
   |---|---|---|
   | `src/signal/` | `Signal_movingAverage`（テンプレート） | 単純移動平均。容量 N をマクロで指定する |
   | | `Signal_lowPass` | 一次遅れ（指数移動平均）フィルタ |
   | | `Signal_median`（テンプレート） | メディアンフィルタ |
   | | `Signal_deadband` | 不感帯 |
   | | `Signal_rateLimiter` | 変化率の制限 |
   | | `Signal_hysteresis` | ヒステリシス付きの比較（オン・オフの閾値が別） |
   | `src/control/` | `Control_pid` | PID（アンチワインドアップ、出力の上下限、手動・自動の切替、微分の先行） |
   | | `Control_ramp` | 目標値へのランプ生成 |
   | `src/interp/` | `Interp_linear1d` | 折れ線テーブル（`x` 昇順の配列）による 1 次元の線形補間。範囲外は端の値で止めるか外挿するかを引数で選ぶ |
   | | `Interp_linear2d` | 2 次元テーブルの双線形補間 |

2. 周期に依存する POU（`Signal_lowPass`・`Signal_rateLimiter`・`Control_pid`・`Control_ramp`）は、サンプリング周期を引数で受け取る（`lreal` の秒）。タスク周期を内部で仮定しない。
3. 引数の誤り（容量 0、周期 0 以下、上限 < 下限、`x` が昇順でないテーブル）は `eno := false` で通知する。
4. テストは、Python（numpy / scipy）で同じ入力から求めた値を期待値にする。`Control_pid` は、ステップ応答と飽和時のアンチワインドアップの振る舞いを確かめる。
5. README.md に 3 つのモジュールの節を追加し、`examples/` に PID と移動平均の例を足す（項目 11）。

### 完了の条件

- 全 POU のテストが、コンパイルとシミュレータで通る。
- 1 つの PR が大きくなりすぎないよう、モジュールごとに PR を分ける（signal → interp → control の順）。

### 未決事項

- `Control_pid` の形式（並列形か標準形（ISA）か）と、微分の先行・不完全微分のフィルタを入れるか。
- Sysmac Studio の標準の PID 命令と役割が重なるため、提供する価値を作者に確認する。

## 12. リリースを自動化する

### 目的

タグを付けたら、GitHub Release と取り込み用の XML が自動でできるようにする。利用者が Jiecc を用意しなくても、XML をダウンロードして Sysmac Studio に取り込めるようにする。

### 作業

1. `scripts/run_tests.py` に `--output-dir DIR` を追加する。指定したときは、`src/` のエントリファイルの XML を一時ディレクトリでなく `DIR` に、ターゲットごとのサブディレクトリ（`DIR/omron/...`、`DIR/keyence/...`）に出力する。
2. `.github/workflows/release.yml` を追加する。`v*` のタグの push で、次を行う。
   - タグの番号と `VERSION` が一致することを確かめる。一致しなければ失敗にする。
   - `setup-jiecc` で Jiecc を取得し、`run_tests.py --compile-only --output-dir` で XML を作る。
   - XML をターゲットごとに zip にまとめ、GitHub Release を作って添付する。本文には CHANGELOG.md の該当する版の節と、使った Jiecc の版（`jiecc --version`）を書く。
   - workflow の権限は `contents: write` だけにする。
3. CONTRIBUTING.md の「バージョン管理」に、タグの push で Release ができることを追記する。
4. 動作は、フォークか一時的なタグ（例: `v0.0.0-test`）で確かめる。タグの番号の検査は、テスト用のタグでは止めるように作る。

### 完了の条件

- タグを push すると、Release と XML の zip が自動でできる。
- `VERSION` と食い違うタグでは失敗する。

### 未決事項

- Release を下書き（draft）で作って作者が公開するか、すぐ公開するか。
- CI の Jiecc の版を固定していないため、Release の XML がどの Jiecc で作られたかを本文に残す（版の固定そのものは、この計画の対象外）。
