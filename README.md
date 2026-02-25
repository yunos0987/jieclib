# JiecLib

## 概要

JiecLibは、<a href="https://www.graviness.com/iec_61131-3/">IEC 61131-3 ST言語</a>のライブラリです。

特徴は、テスト対象POUのソースコード、および、その単体テストコードがIEC 61131-3 ST言語を拡張したテキスト形式で完結していることです。このため、すべてがダイレクトにGit等で構成管理が可能です。使用するIDEによっては生成AIを使ってIEC 61131-3プログラミングできます。

このテキスト形式のコードをPLCメーカーのツールで取り込み可能な形式に変換するために、[IEC 61131-3 ⇄ IEC 61131-10変換ソフトウェア Jiecc](https://www.graviness.com/iec_61131-3/jiecc.html)を使用します。

現在、JiecLibは[IEC 61131-10 XML](https://plcopen.org/sites/default/files/downloads/iec_61131-10_preview.pdf)をサポートするオムロン社製の[Sysmac Studio](https://www.fa.omron.co.jp/products/family/3077/download/software.html)を対象にしています。

## 必要環境

オムロン社製のSysmac Studioを使用して、JiecLib内のライブラリを使用するために必要な環境は以下の通りです。

* [Jiecc 5.6以降](https://www.graviness.com/iec_61131-3/jiecc.html#Header.Jiecc%E3%81%AE%E3%83%80%E3%82%A6%E3%83%B3%E3%83%AD%E3%83%BC%E3%83%89%E3%81%A8%E5%AE%9F%E8%A1%8C%E6%96%B9%E6%B3%95)
  * Jieccは、IEC 61131-3テキストをIEC 61131-10 XMLに変換するコマンドラインベースで無料のソフトウェアです。[Jieccのダウンロードと実行方法](https://www.graviness.com/iec_61131-3/jiecc.html#Header.Jiecc%E3%81%AE%E3%83%80%E3%82%A6%E3%83%B3%E3%83%AD%E3%83%BC%E3%83%89%E3%81%A8%E5%AE%9F%E8%A1%8C%E6%96%B9%E6%B3%95)から最新のJieccをダウンロードできます。
* [Sysmac Studio](https://www.fa.omron.co.jp/products/family/3077/download/software.html)
  * 高価なソフトウェアですが、Sysmac Studioに同梱されているシミュレータでテストが可能です。必要に応じて、PLC本体も入手してください。

## Sysmac StudioでJiecLib内のライブラリを取り込む方法

Sysmac StudioでJiecLib内のライブラリを取り込む方法について、[string_lib](./src/string_lib/string_lib.txt)を例として示します。

1. 次のコマンドを実行し、JiecLibプロジェクトをクローンとサブモジュールを初期化します。

```
$ git clone https://github.com/yunos0987/jieclib.git
$ cd jieclib
$ git submodule update --init --recursive
```

※一部のライブラリが、[JiecUnit](https://github.com/yunos0987/jiecunit)内のモジュールに依存しており、サブモジュールの初期化を必要とします。

2. 次のコマンドを実行します。事前に[jiecc.exe](https://www.graviness.com/iec_61131-3/jiecc.html#Header.Jiecc%E3%81%AE%E3%83%80%E3%82%A6%E3%83%B3%E3%83%AD%E3%83%BC%E3%83%89%E3%81%A8%E5%AE%9F%E8%A1%8C%E6%96%B9%E6%B3%95)をjieclibディレクトリ直下におくか、jieccがあるディレクトリへパスを通しておいてください。

```
$ jiecc ./src/string_lib/string_lib.txt -I. -I./src -o ./src/string_lib/string_lib.xml -t omron
```

`./src/string_lib/string_lib.xml`が出力されます。

※xmlを生成するためのコマンドは、ライブラリごとに違います。各ライブラリ（*.txt）の先頭にxmlを生成するためのコマンドを記載しています。

3. 出力された`./src/string_lib/string_lib.xml`ををSysmac StudioのIEC 61131-10インポート機能 [ ツール | IEC 61131-10 XML | インポート ] でインポートします。

![string_lib.xmlインポート完了後の画面](./docs/screen_stringlib_import_completed.png)

[string_lib](./src/string_lib/string_lib.txt)に含まれるPOU群（charAtファンクション, lowerファンクション, ...）がインポートされます。

## JiecLibに含まれるライブラリ

JiecLibに含まれるライブラリと、IEC 61131-10 XMLを生成するためのコマンドを示します。

* [array](./src/array)
  * 基本的な配列操作ライブラリです。
  * **配列判定（正規配列）**
    * [Array_isRegular_lreal](./src/array/array.txt) / [Array_isRegular_dint](./src/array/array.txt): 1次元配列の正規性判定
    * [Array_isRegular2d_x_lreal](./src/array/array.txt) / [Array_isRegular2d_x_dint](./src/array/array.txt): 2次元配列の次元ごとの正規性判定
    * [Array_isRegular2d_lreal](./src/array/array.txt) / [Array_isRegular2d_dint](./src/array/array.txt): 2次元配列の正規性判定
  * **コピー**
    * [Array_copy_lreal](./src/array/copy.txt) / [Array_copy_dint](./src/array/copy.txt): 全要素コピー
    * [Array_copy_x_lreal](./src/array/copy.txt) / [Array_copy_x_dint](./src/array/copy.txt): 範囲指定コピー
  * **ソート**
    * [Array_bubblesort_lreal](./src/array/sort.txt) / [Array_bubblesort_dint](./src/array/sort.txt): バブルソート
    * [Array_mergesort_lreal](./src/array/sort.txt) / [Array_mergesort_dint](./src/array/sort.txt): マージソート
    * [Array_quicksort_lreal](./src/array/sort.txt) / [Array_quicksort_dint](./src/array/sort.txt): クイックソート
  * IEC 61131-10 XML生成コマンド: `jiecc ./src/array/array.txt -I. -I./src -I./vendor/jiecunit/sys -o ./src/array/array.xml -t omron`
* [encoding](./src/encoding)
  * エンコーディング関連ライブラリです。
  * **Base64**
    * [base64encode](./src/encoding/base64.txt) / [base64decode](./src/encoding/base64.txt)
    * IEC 61131-10 XML生成コマンド: `jiecc ./src/encoding/base64.txt -I. -I./vendor/jiecunit/sys -o ./src/encoding/base64.xml -t omron`
  * **Percent（URLエンコード）**
    * [percentencode](./src/encoding/percent.txt) / [percentdecode](./src/encoding/percent.txt)
    * IEC 61131-10 XML生成コマンド: `jiecc ./src/encoding/percent.txt -I. -I./vendor/jiecunit/sys -o ./src/encoding/percent.xml -t omron`
  * **Hex**
    * [hexencode](./src/encoding/hex.txt) / [hexdecode](./src/encoding/hex.txt)
    * IEC 61131-10 XML生成コマンド: `jiecc ./src/encoding/hex.txt -I. -I./vendor/jiecunit/sys -o ./src/encoding/hex.xml -t omron`
* [hash](./src/hash)
  * ハッシュ関連ライブラリです。
  * **CRC32**
    * [CRC32_string](./src/hash/crc32.txt): 文字列入力のCRC32
    * [CRC32_bytes](./src/hash/crc32.txt): バイト配列入力のCRC32（`offset`/`length`を指定）
    * IEC 61131-10 XML生成コマンド: `jiecc ./src/hash/crc32.txt -I. -I./src -I./vendor/jiecunit/sys -o ./src/hash/crc32.xml -t omron`
  * **MD5**
    * [MD5_string](./src/hash/md5.txt): 文字列入力のMD5
    * [MD5_bytes](./src/hash/md5.txt): バイト配列入力のMD5（`offset`/`length`/を指定）
    * IEC 61131-10 XML生成コマンド: `jiecc ./src/hash/md5.txt -I. -I./src -I./vendor/jiecunit/sys -o ./src/hash/md5.xml -t omron`
  * **SHA-1**
    * [SHA1_string](./src/hash/sha1.txt): 文字列入力のSHA-1
    * [SHA1_bytes](./src/hash/sha1.txt): バイト配列入力のSHA-1（`offset`/`length`を指定）
    * IEC 61131-10 XML生成コマンド: `jiecc ./src/hash/sha1.txt -I. -I./src -I./vendor/jiecunit/sys -o ./src/hash/sha1.xml -t omron`
  * **SHA-256**
    * [SHA256_string](./src/hash/sha256.txt): 文字列入力のSHA-256
    * [SHA256_bytes](./src/hash/sha256.txt): バイト配列入力のSHA-256（`offset`/`length`を指定）
    * IEC 61131-10 XML生成コマンド: `jiecc ./src/hash/sha256.txt -I. -I./src -I./vendor/jiecunit/sys -o ./src/hash/sha256.xml -t omron`
  * **SHA-512**
    * [SHA512_string](./src/hash/sha512.txt): 文字列入力のSHA-512
    * [SHA512_bytes](./src/hash/sha512.txt): バイト配列入力のSHA-512（`offset`/`length`を指定）
    * IEC 61131-10 XML生成コマンド: `jiecc ./src/hash/sha512.txt -I. -I./src -I./vendor/jiecunit/sys -o ./src/hash/sha512.xml -t omron`
* [hashmap](./src/hashmap)
  * Robin Hood hashing ベースの連想配列（HashMap）テンプレートです。
  * 単一の固定型ライブラリではなく、`src/hashmap/hashmap_gen.txt` を `#include` する際にマクロで型・容量・比較関数・ハッシュ関数を指定してインスタンス生成します。
  * 主な生成関数:
    * `HashMap_<name>_init`
    * `HashMap_<name>_upsert`
    * `HashMap_<name>_try_get`
    * `HashMap_<name>_remove`
    * `HashMap_<name>_contains`
    * `HashMap_<name>_count`
    * `HashMap_<name>_clear`
  * 生成例（stringキー / dint値）:
    * `{#define HashMapName mymap}`
    * `{#define HashMapCapacity 256}`
    * `{#define HashMapKeyType string[128]}`
    * `{#define HashMapKeyEqualsFunction String_equals}`
    * `{#define HashMapKeyHashFunction String_hash}`
    * `{#define HashMapValueType dint}`
    * `{#include <src/hashmap/hashmap_gen.txt>}`
  * テスト用XML生成コマンド: `jiecc ./test/hashmap/test_hashmap.txt -I. -I./vendor/jiecunit -I./vendor/jiecunit/sys -o ./test/hashmap/test_hashmap.xml -t omron`
* [math](./src/math)
  * 数学関数ライブラリです。
  * [Math_floor](./src/math/floor.txt): 床関数（floor）
  * [Math_atan2](./src/math/atan2.txt): 2引数アークタンジェント
  * IEC 61131-10 XML生成コマンド:
    * `jiecc ./src/math/floor.txt -I. -I./src -I./vendor/jiecunit/sys -o ./src/math/floor.xml -t omron`
    * `jiecc ./src/math/atan2.txt -I. -I./src -I./vendor/jiecunit/sys -o ./src/math/atan2.xml -t omron`
* [vector](./src/vector)
  * ベクトル演算ライブラリです。
  * **生成・基本演算**
    * [Vector_zeros](./src/vector/constructors.txt) / [Vector_ones](./src/vector/constructors.txt) / [Vector_from_iterable](./src/vector/constructors.txt): 生成
    * [Vector_add](./src/vector/arithmetic.txt) / [Vector_sub](./src/vector/arithmetic.txt) / [Vector_scale](./src/vector/arithmetic.txt): 基本演算
    * [Vector_dot](./src/vector/arithmetic.txt): 内積
    * [Vector_negate](./src/vector/arithmetic.txt) / [Vector_elementwise_mul](./src/vector/arithmetic.txt) / [Vector_elementwise_div](./src/vector/arithmetic.txt): 要素演算
    * [Vector_linear_combination](./src/vector/arithmetic.txt) / [Vector_equal](./src/vector/arithmetic.txt): 線形結合・比較
  * **外積・幾何**
    * [Vector_cross_product](./src/vector/dot.txt) / [Vector_cross_product_magnitude](./src/vector/dot.txt) / [Vector_cross_product_unit](./src/vector/dot.txt): 外積
    * [Vector_scalar_triple_product](./src/vector/dot.txt) / [Vector_vector_triple_product](./src/vector/dot.txt): 三重積
    * [Vector_angle_from_cross_product](./src/vector/dot.txt) / [Vector_is_parallel](./src/vector/dot.txt) / [Vector_is_orthogonal](./src/vector/dot.txt): 角度・平行/直交判定
  * **ノルム・距離**
    * [Vector_norm_l1](./src/vector/norms.txt) / [Vector_norm_l2](./src/vector/norms.txt) / [Vector_norm_linf](./src/vector/norms.txt) / [Vector_norm_lp](./src/vector/norms.txt): ノルム
    * [Vector_normalize_l2](./src/vector/norms.txt): 正規化
    * [Vector_distance_l1](./src/vector/norms.txt) / [Vector_distance_l2](./src/vector/norms.txt) / [Vector_distance_linf](./src/vector/norms.txt): 距離
    * [Vector_is_unit](./src/vector/norms.txt): 単位ベクトル判定
  * **ユーティリティ**
    * [Vector_utils_is_regular](./src/vector/utils.txt) / [Vector_utils_is_zero](./src/vector/utils.txt) / [Vector_utils_normalize](./src/vector/utils.txt): 補助関数
  * IEC 61131-10 XML生成コマンド: `jiecc ./src/vector/vector.txt -I. -I./src -I./vendor/jiecunit/sys -o ./src/vector/vector.xml -t omron`
* [linalg](./src/linalg)
  * 行列中心の線形代数ライブラリです。
  * **行列演算**
    * [Matrix_add](./src/linalg/matrix/arithmetic.txt): 加算
    * [Matrix_sub](./src/linalg/matrix/arithmetic.txt): 減算
    * [Matrix_scale](./src/linalg/matrix/arithmetic.txt): スカラー倍
    * [Matrix_multiply](./src/linalg/matrix/arithmetic.txt): 乗算
    * [Matrix_transpose](./src/linalg/matrix/arithmetic.txt): 転置
    * [Matrix_vector_multiply](./src/linalg/matrix/arithmetic.txt): 行列とベクトルの乗算
    * [Matrix_inverse](./src/linalg/matrix/inverse.txt): 逆行列
    * [Matrix_determinant](./src/linalg/matrix/properties.txt) / [Matrix_trace](./src/linalg/matrix/properties.txt) / [Matrix_rank](./src/linalg/matrix/properties.txt): 性質判定
    * [Matrix_norm_frobenius](./src/linalg/matrix/properties.txt) / [Matrix_norm_spectral](./src/linalg/matrix/properties.txt) / [Matrix_norm_l1](./src/linalg/matrix/properties.txt) / [Matrix_norm_linf](./src/linalg/matrix/properties.txt): 行列ノルム
  * **分解**
    * [Matrix_lu_decompose](./src/linalg/decomposition/lu.txt): LU分解
    * [Matrix_qr_decompose](./src/linalg/decomposition/qr.txt): QR分解
    * [Matrix_cholesky_decompose](./src/linalg/decomposition/cholesky.txt): コレスキー分解
    * [Matrix_svd_decompose](./src/linalg/decomposition/svd.txt): 特異値分解（SVD）
  * **固有値問題**
    * [Matrix_eigenvalue_compute](./src/linalg/eigenvalue/eigenvalue.txt): 固有値計算
    * [Matrix_eigenvector_compute](./src/linalg/eigenvalue/eigenvector.txt): 固有ベクトル計算
  * **連立方程式**
    * [Matrix_solve_gaussian](./src/linalg/solve/gaussian.txt): ガウス消去法
    * [Matrix_solve_iterative](./src/linalg/solve/iterative.txt): 反復法
    * [Matrix_solve_least_squares](./src/linalg/solve/least_squares.txt): 最小二乗法
  * **座標変換**
    * [Matrix_rotation_2d](./src/linalg/transform/rotation.txt) / [Matrix_rotation_z](./src/linalg/transform/rotation.txt): 回転
    * [Matrix_scaling_2d](./src/linalg/transform/scaling.txt) / [Matrix_scaling_3d](./src/linalg/transform/scaling.txt): 拡大縮小
    * [Matrix_translation_2d](./src/linalg/transform/translation.txt) / [Matrix_translation_3d](./src/linalg/transform/translation.txt): 並進
  * IEC 61131-10 XML生成コマンド: `jiecc ./src/linalg/linalg.txt -I. -I./src -I./vendor/jiecunit/sys -o ./src/linalg/linalg.xml -t omron`
* [random](./src/random)
  * 乱数生成ライブラリです。
  * **Mersenne Twister**
    * [mersenne_twister](./src/random/mersenne_twister.txt): 高速かつ超長周期の疑似乱数生成アルゴリズム
    * [Python言語のrandomモジュール](https://docs.python.org/ja/3.12/library/random.html)でも採用されています。
    * IEC 61131-10 XML生成コマンド: `jiecc ./src/random/mersenne_twister.txt -I. -I./src -I./vendor/jiecunit/sys -o ./src/random/mersenne_twister.xml -t omron`
  * **Xorshift32**
    * [xorshift32](./src/random/xorshift32.txt): 軽量で高速な疑似乱数生成アルゴリズム
    * IEC 61131-10 XML生成コマンド: `jiecc ./src/random/xorshift32.txt -I. -I./src -I./vendor/jiecunit/sys -o ./src/random/xorshift32.xml -t omron`
* [ringbuffer](./src/ringbuffer)
  * FIFO形式のリングバッファです。
    * バッファのデータ型を簡単に拡張できます。
    * バッファがいっぱいの状態でさらに追加しようとするときの振る舞いを指定できます。上書き（`overwrite=true`）を指定する場合、最も過去に加えたデータを上書きします。`overwrite=true`で初期化すると、最新のログを記録する目的で使用できます。
  * IEC 61131-10 XML生成コマンド: `jiecc ./src/ringbuffer/ringbuffer.txt -I. -I./src -I./vendor/jiecunit/sys -o ./src/ringbuffer/ringbuffer.xml -t omron`
* [stats](./src/stats)
  * 基本的な統計ライブラリです。
	* **記述統計**: 算術平均、幾何平均、調和平均、中央値、最頻値、分散、標準偏差、歪度、尖度、変動係数、相関、共分散、分位数、平均絶対偏差、標準誤差など
	* **確率分布**: 正規分布、t分布、カイ二乗分布、指数分布、一様分布（連続）、二項分布、ポアソン分布（離散）
	* **統計的推論**: t検定、カイ二乗検定、正規性検定、ノンパラメトリック検定、信頼区間推定、効果量計算
	* **回帰分析**: 線形回帰、相関検定
	* **モーメント計算**: 原点モーメント、中心モーメント、標準化モーメント
	* **数列処理**: ソート、順位付け、分位数、累積計算
	* 産業用制御システムにおけるプロセス監視やデータ分析、品質管理などの用途で使用できます。
  * IEC 61131-10 XML生成コマンド: `jiecc ./src/stats/stats.txt -I. -I./src -I./vendor/jiecunit/sys -o ./src/stats/stats.xml -t omron`
* [string_lib](./src/string_lib)
  * 基本的な文字列操作ライブラリです。
    * JavaScriptやPythonライクな at, charAt, empty, asciiCharCodeAt, fromAsciiCharCode, lower, upper, remove, reverse, startswith, endswith, indexOf, includes, split, substring, trim, ltrim, rtrim, join, substitute を含みます。
    * 文字列操作に関するIEC 61131-3の特徴として、文字のインデクスは0始まりではなく、1始まりです。例えば、FIND('abcde', 'cd') は3を得ます。本ライブラリは、0始まりに統一しています。
    * ASCII範囲外の文字の操作については、IEC 61131-3規格の範囲では限りがあります。ASCII範囲内で運用することをお勧めします。ASCII範囲外の文字を操作するには、ベンダー提供の組み込みPOUを使用するか、ベンダーの文字列型の文字コードが明確であれば、自作することを検討してください。
  * IEC 61131-10 XML生成コマンド: `jiecc ./src/string_lib/string_lib.txt -I. -I./src -I./vendor/jiecunit/sys -o ./src/string_lib/string_lib.xml -t omron`
## JiecLib開発者向け

JiecLibプロジェクトの一部のライブラリは、外部の[JiecUnit](https://github.com/yunos0987/jiecunit)に依存しています。JiecLibプロジェクトは、外部依存のライブラリ管理のため、Git submodule を使用します。

### サブモジュール含むリポジトリのクローン方法

JiecLibプロジェクトをクローンするときに、サブモジュールの初期化も必要です。

```
$ git clone https://github.com/yunos0987/jieclib.git
$ cd jieclib
$ git submodule update --init --recursive
```

サブモジュールをupdateするには、次のコマンドを実行します。

```
$ cd jieclib
$ git submodule update --remote
```

### JiecLibのテスト方法

JiecLibの単体テストに[JiecUnit](https://github.com/yunos0987/jiecunit)を使用します。テストコードは、[jieclib/test](./test)ディレクトリに含まれます。

1. 次のコマンドを実行します。事前に[jiecc.exe](https://www.graviness.com/iec_61131-3/jiecc.html#Header.Jiecc%E3%81%AE%E3%83%80%E3%82%A6%E3%83%B3%E3%83%AD%E3%83%BC%E3%83%89%E3%81%A8%E5%AE%9F%E8%A1%8C%E6%96%B9%E6%B3%95)をjieclibディレクトリ直下におくか、jieccがあるディレクトリへパスを通しておいてください。

```
$ cd jieclib
$ jiecc ./src/string_lib/string_lib.txt -I. -I./src -I./vendor/jiecunit/sys -o ./src/string_lib/string_lib.xml -t omron
```

`./test/string_lib/test_string_lib.xml`が生成されます。

2. [オムロン社製Sysmac Studioの場合の単体テストサンプルの実行方法](https://github.com/yunos0987/jiecunit#%E3%82%AA%E3%83%A0%E3%83%AD%E3%83%B3%E7%A4%BE%E8%A3%BDsysmac-studio%E3%81%AE%E5%A0%B4%E5%90%88%E3%81%AE%E5%8D%98%E4%BD%93%E3%83%86%E3%82%B9%E3%83%88%E3%82%B5%E3%83%B3%E3%83%97%E3%83%AB%E3%81%AE%E5%AE%9F%E8%A1%8C%E6%96%B9%E6%B3%95)の手順2以降を実行します。

## ライセンス

このプロジェクトはApache License 2.0の下でライセンスされています。詳細は[LICENSE](./LICENSE)ファイルを参照してください。
