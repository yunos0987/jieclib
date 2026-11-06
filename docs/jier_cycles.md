# jier の周期数

jier（`jiecc --run`）は、テストが終わった後も、`--max-cycles` で指定した周期数まで回り続けます。そのため、実行時間は周期数でほぼ決まります。このファイルには、テストファイルごとに合格に必要な周期数と、その測り方を記録します。`scripts/run_tests.py` の既定の `--max-cycles`（2000）と、`scripts/jier_required.txt` の周期数は、この結果から決めました。

## 測定の条件

- 日付: 2026-11-06
- Jiecc 9.2.0、Windows 11、Python 3.14
- 対象: `test/` の、`DEFINE_CONFIGURATION` を含む 112 ファイル
- 6 ファイルを並列に実行した。実行時間は、その条件での値である（1 ファイルずつ実行すると短くなる）。

## 測り方

1. 各ファイルを `python scripts/run_tests.py --run-only --max-cycles N <ファイル>` と同じコマンド（`jiecc --run <ファイル> -I. -I./src -I./vendor/jiecunit -D_TEST_ --max-cycles N`）で実行する。
2. N を 1000・2000・4000・8000・16000 の順に増やし、合格した最初の N を、そのファイルに必要な周期数とする。合格とは、`run_tests.py` の判定（集計行が出て、`[========] Running N tests.` の数と実行したテストの数が一致し、失敗がない）を満たすことである。
3. 出力に `error:` の行があるファイルは、周期数に関係なく失敗するので、そこで止める。

新しいテストファイルを `scripts/jier_required.txt` に載せるときも、同じ方法で測る。1 つの `TEST_S` は数周期で終わるので、`TEST_S` だけのファイルは 1000 周期で足りる（`test/math/test_floor.iec` は 2 周期で合格した）。`TEST_M` を使うファイルは、そのテストが使う周期数を足す。

## 結果

| 結果 | ファイル数 |
|---|---|
| 1000 周期で合格 | 28 |
| エラーで止まる（周期数に関係なく失敗する） | 83 |
| 1000 周期でも 900 秒で終わらない | 1 |

2000 周期以上が必要なファイルはなかった。既定の `--max-cycles` は、最大の 1000 の 2 倍の 2000 にした。以前の既定の 100000 では、1 ファイルに 280 秒以上かかり、CI の `run` ジョブ（1 ファイル 300 秒まで）で時間切れになっていた。

### 1000 周期で合格したファイル

| ファイル | テストの数 | 周期数 | 実行時間（秒） |
|---|---|---|---|
| `test/test_sys.iec` | 6 | 1000 | 16.7 |
| `test/test_sys_conv.iec` | 5 | 1000 | 14.9 |
| `test/array/test_array_aggregate.iec` | 4 | 1000 | 14.3 |
| `test/array/test_array_copy.iec` | 6 | 1000 | 18.4 |
| `test/array/test_array_equivalence.iec` | 2 | 1000 | 11.6 |
| `test/array/test_array_fill.iec` | 2 | 1000 | 9.5 |
| `test/array/test_array_reverse.iec` | 2 | 1000 | 10.1 |
| `test/array/test_array_rotate.iec` | 3 | 1000 | 12.0 |
| `test/array/test_array_search.iec` | 4 | 1000 | 14.0 |
| `test/array/test_array_sort.iec` | 9 | 1000 | 22.4 |
| `test/compress/test_rle.iec` | 2 | 1000 | 12.0 |
| `test/container/arraylist/test_arraylist.iec` | 16 | 1000 | 33.1 |
| `test/container/dequeue/test_dequeue.iec` | 16 | 1000 | 33.7 |
| `test/container/linkedlist/test_linkedlist.iec` | 19 | 1000 | 46.3 |
| `test/container/ringbuffer/test_ringbuffer.iec` | 3 | 1000 | 14.8 |
| `test/container/stack/test_stack.iec` | 11 | 1000 | 27.6 |
| `test/math/test_atan2.iec` | 1 | 1000 | 11.7 |
| `test/math/test_floor.iec` | 1 | 1000 | 12.2 |
| `test/math/test_math.iec` | 2 | 1000 | 16.1 |
| `test/stats/distributions/continuous/test_chi_square.iec` | 5 | 1000 | 18.2 |
| `test/stats/distributions/continuous/test_exponential.iec` | 5 | 1000 | 15.2 |
| `test/stats/distributions/continuous/test_normal.iec` | 5 | 1000 | 15.3 |
| `test/stats/distributions/continuous/test_student_t.iec` | 5 | 1000 | 15.7 |
| `test/stats/distributions/continuous/test_uniform.iec` | 5 | 1000 | 14.4 |
| `test/stats/distributions/core/test_special_functions.iec` | 9 | 1000 | 22.7 |
| `test/stats/distributions/discrete/test_binomial.iec` | 5 | 1000 | 17.6 |
| `test/stats/distributions/discrete/test_poisson.iec` | 4 | 1000 | 15.2 |
| `test/vector/test_dot.iec` | 8 | 1000 | 20.8 |

### エラーで止まるファイル（83）

CHANGELOG.md 4.0.0 の「既知の問題」と同じ内訳である。

| エラー | ファイル数 |
|---|---|
| dint の `max` / `min` など: `cannot marshal Python int ... LREAL` | 62 |
| 幅なしの `shr`: `UNDEFINED_SYMBOL` | 15 |
| 幅なしの `shl`: `UNDEFINED_SYMBOL` | 6 |

### 終わらないファイル（1）

`test/string_lib/test_string_lib.iec` は、`test_String_remove` で止まり、1000 周期でも 900 秒で終わらない。`String_remove('abcdabcd', '', -1)`（空の文字列を削除する）で、`src/string_lib/string_lib.iec` の `String_remove` のループが終わらないためである。jier の `find(s, '')` は 0 以外を返す（`find('abc', '') = 0` を確かめるテストが jier で失敗する）。`String_remove` は、`find` が 0 を返すまでループする。PLC の環境の `find` が空の文字列に何を返すかは、確かめていない。

## 追加したテストファイル

`scripts/jier_required.txt` に載せたファイルの、必要な周期数（同じ方法で測った値）。

| ファイル | 必要な周期数 | 一覧の値 |
|---|---|---|
| `test/math/test_floor_large.iec` | 1000 以下 | 1000 |
| `test/test_jiecunit_test_m.iec` | 21（`TEST_M` が 20 周期を使う。20 では失敗する） | 1000 |
| `test/array/test_array_dint.iec` | 1000 以下 | 1000 |
| `test/stats/inference/tests/test_p_values.iec` | 1000 以下 | 1000 |
| `test/test_sys_console.iec` | 1000 以下 | 1000 |
| `test/math/test_<名前>.iec`（PR-8 の 13 ファイル: trunc・ceil・round・round_half_even・round_to・clamp・lerp・sign・hypot・fmod・gcd・lcm・is_close） | 1000 以下 | 1000 |

## 測り直すとき

Jiecc の版が変わったとき、または jier で通るファイルが増えたときは、測り直してこのファイルを更新する。
