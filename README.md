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

Sysmac StudioでJiecLib内のライブラリを取り込む方法について、[string_lib](./string_lib/string_lib.txt)を例として示します。

1. 次のコマンドを実行し、JiecLibプロジェクトをクローンとサブモジュールを初期化します。

```
$ git clone https://github.com/yunos0987/jieclib.git
$ cd jieclib
$ git submodule update --init --recursive
```

※一部のライブラリが、[JiecUnit](https://github.com/yunos0987/jiecunit)内のモジュールに依存しており、サブモジュールの初期化を必要とします。

2. 次のコマンドを実行します。事前に[jiecc.exe](https://www.graviness.com/iec_61131-3/jiecc.html#Header.Jiecc%E3%81%AE%E3%83%80%E3%82%A6%E3%83%B3%E3%83%AD%E3%83%BC%E3%83%89%E3%81%A8%E5%AE%9F%E8%A1%8C%E6%96%B9%E6%B3%95)をjieclibディレクトリ直下におくか、jieccがあるディレクトリへパスを通しておいてください。

```
$ jiecc ./string_lib/string_lib.txt -o ./string_lib/string_lib.xml -t omron
```

`./string_lib/string_lib.xml`が出力されます。

※xmlを生成するためのコマンドは、ライブラリごとに違います。各ライブラリ（*.txt）の先頭にxmlを生成するためのコマンドを記載しています。

3. 出力された`./string_lib/string_lib.xml`ををSysmac StudioのIEC 61131-10インポート機能 [ ツール | IEC 61131-10 XML | インポート ] でインポートします。

![string_lib.xmlインポート完了後の画面](./docs/screen_stringlib_import_completed.png)

[string_lib](./string_lib/string_lib.txt)に含まれるPOU群（charAtファンクション, lowerファンクション, ...）がインポートされます。

## JiecLibに含まれるライブラリ

JiecLibに含まれるライブラリと、IEC 61131-10 XMLを生成するためのコマンドを示します。

* [array](./array)
  * 基本的な配列操作ライブラリです。
  * **配列判定（正規配列）**
    * [Array_isRegular_lreal](./array/array.txt) / [Array_isRegular_dint](./array/array.txt): 1次元配列の正規性判定
    * [Array_isRegular2d_x_lreal](./array/array.txt) / [Array_isRegular2d_x_dint](./array/array.txt): 2次元配列の次元ごとの正規性判定
    * [Array_isRegular2d_lreal](./array/array.txt) / [Array_isRegular2d_dint](./array/array.txt): 2次元配列の正規性判定
  * **コピー**
    * [Array_copy_lreal](./array/copy.txt) / [Array_copy_dint](./array/copy.txt): 全要素コピー
    * [Array_copy_x_lreal](./array/copy.txt) / [Array_copy_x_dint](./array/copy.txt): 範囲指定コピー
  * **ソート**
    * [Array_bubblesort_lreal](./array/sort.txt) / [Array_bubblesort_dint](./array/sort.txt): バブルソート
    * [Array_mergesort_lreal](./array/sort.txt) / [Array_mergesort_dint](./array/sort.txt): マージソート
    * [Array_quicksort_lreal](./array/sort.txt) / [Array_quicksort_dint](./array/sort.txt): クイックソート
  * IEC 61131-10 XML生成コマンド: `jiecc ./array/array.txt -I. -I./vendor/jiecunit/sys -o ./array/array.xml -t omron`
* [base64](./base64)
  * メール等で使用されているエンコード方式Base64です。
  * IEC 61131-10 XML生成コマンド: `jiecc ./base64/base64.txt -I. -I./vendor/jiecunit/sys -o ./base64/base64.xml -t omron`
* [math](./math)
  * 数学関数ライブラリです。
  * [Math_floor](./math/floor.txt): 床関数（floor）
  * [Math_atan2](./math/atan2.txt): 2引数アークタンジェント
  * IEC 61131-10 XML生成コマンド:
    * `jiecc ./math/floor.txt -I. -I./vendor/jiecunit/sys -o ./math/floor.xml -t omron`
    * `jiecc ./math/atan2.txt -I. -I./vendor/jiecunit/sys -o ./math/atan2.xml -t omron`
* [vector](./vector)
  * ベクトル演算ライブラリです。
  * **生成・基本演算**
    * [Vector_zeros](./vector/constructors.txt) / [Vector_ones](./vector/constructors.txt) / [Vector_from_iterable](./vector/constructors.txt): 生成
    * [Vector_add](./vector/arithmetic.txt) / [Vector_sub](./vector/arithmetic.txt) / [Vector_scale](./vector/arithmetic.txt): 基本演算
    * [Vector_dot](./vector/arithmetic.txt): 内積
    * [Vector_negate](./vector/arithmetic.txt) / [Vector_elementwise_mul](./vector/arithmetic.txt) / [Vector_elementwise_div](./vector/arithmetic.txt): 要素演算
    * [Vector_linear_combination](./vector/arithmetic.txt) / [Vector_equal](./vector/arithmetic.txt): 線形結合・比較
  * **外積・幾何**
    * [Vector_cross_product](./vector/dot.txt) / [Vector_cross_product_magnitude](./vector/dot.txt) / [Vector_cross_product_unit](./vector/dot.txt): 外積
    * [Vector_scalar_triple_product](./vector/dot.txt) / [Vector_vector_triple_product](./vector/dot.txt): 三重積
    * [Vector_angle_from_cross_product](./vector/dot.txt) / [Vector_is_parallel](./vector/dot.txt) / [Vector_is_orthogonal](./vector/dot.txt): 角度・平行/直交判定
  * **ノルム・距離**
    * [Vector_norm_l1](./vector/norms.txt) / [Vector_norm_l2](./vector/norms.txt) / [Vector_norm_linf](./vector/norms.txt) / [Vector_norm_lp](./vector/norms.txt): ノルム
    * [Vector_normalize_l2](./vector/norms.txt): 正規化
    * [Vector_distance_l1](./vector/norms.txt) / [Vector_distance_l2](./vector/norms.txt) / [Vector_distance_linf](./vector/norms.txt): 距離
    * [Vector_is_unit](./vector/norms.txt): 単位ベクトル判定
  * **ユーティリティ**
    * [Vector_utils_is_regular](./vector/utils.txt) / [Vector_utils_is_zero](./vector/utils.txt) / [Vector_utils_normalize](./vector/utils.txt): 補助関数
  * IEC 61131-10 XML生成コマンド: `jiecc ./vector/vector.txt -I. -I./vendor/jiecunit/sys -o ./vector/vector.xml -t omron`
* [mersenne_twister](./mersenne_twister)
  * 擬似乱数生成アルゴリズムの一つであるメルセンヌ・ツイスタのIEC 61131-3 ST言語の実装です。
    * [Python言語のrandomモジュール](https://docs.python.org/ja/3.12/library/random.html)でも採用されている高速かつ超長周期の疑似乱数生成アルゴリズムです。その他の詳しい説明は、[メルセンヌ・ツイスタ考案者のウェブサイト](http://www.math.sci.hiroshima-u.ac.jp/m-mat/MT/mt.html)を参照してください。
    * なお、[オリジナルに近いIEC 61131-3 ST言語ソースコードはこちら](http://blog.graviness.com/?eid=949297)にあります。
  * IEC 61131-10 XML生成コマンド: `jiecc ./mersenne_twister/mersenne_twister.txt -I. -I./vendor/jiecunit/sys -o ./mersenne_twister/mersenne_twister.xml -t omron`
* [ringbuffer](./ringbuffer)
  * FIFO形式のリングバッファです。
    * バッファのデータ型を簡単に拡張できます。
    * バッファがいっぱいの状態でさらに追加しようとするときの振る舞いを指定できます。上書き（`overwrite=true`）を指定する場合、最も過去に加えたデータを上書きします。`overwrite=true`で初期化すると、最新のログを記録する目的で使用できます。
  * IEC 61131-10 XML生成コマンド: `jiecc ./ringbuffer/ringbuffer.txt -I. -I./vendor/jiecunit/sys -o ./ringbuffer/ringbuffer.xml -t omron`
* [stats](./stats)
  * 基本的な統計ライブラリです。
	* **記述統計**: 算術平均、幾何平均、調和平均、中央値、最頻値、分散、標準偏差、歪度、尖度、変動係数、相関、共分散、分位数、平均絶対偏差、標準誤差など
	* **確率分布**: 正規分布、t分布、カイ二乗分布、指数分布、一様分布（連続）、二項分布、ポアソン分布（離散）
	* **統計的推論**: t検定、カイ二乗検定、正規性検定、ノンパラメトリック検定、信頼区間推定、効果量計算
	* **回帰分析**: 線形回帰、相関検定
	* **モーメント計算**: 原点モーメント、中心モーメント、標準化モーメント
	* **数列処理**: ソート、順位付け、分位数、累積計算
	* 産業用制御システムにおけるプロセス監視やデータ分析、品質管理などの用途で使用できます。
  * IEC 61131-10 XML生成コマンド: `jiecc ./stats/stats.txt -I. -I./vendor/jiecunit/sys -o ./stats/stats.xml -t omron`
* [string_lib](./string_lib)
  * 基本的な文字列操作ライブラリです。
    * JavaScriptやPythonライクな at, charAt, empty, asciiCharCodeAt, fromAsciiCharCode, lower, upper, remove, reverse, startswith, endswith, indexOf, includes, split, substring, trim, ltrim, rtrim, join, substitute を含みます。
    * 文字列操作に関するIEC 61131-3の特徴として、文字のインデクスは0始まりではなく、1始まりです。例えば、FIND('abcde', 'cd') は3を得ます。本ライブラリは、0始まりに統一しています。
    * ASCII範囲外の文字の操作については、IEC 61131-3規格の範囲では限りがあります。ASCII範囲内で運用することをお勧めします。ASCII範囲外の文字を操作するには、ベンダー提供の組み込みPOUを使用するか、ベンダーの文字列型の文字コードが明確であれば、自作することを検討してください。
  * IEC 61131-10 XML生成コマンド: `jiecc ./string_lib/string_lib.txt -I. -I./vendor/jiecunit/sys -o ./string_lib/string_lib.xml -t omron`
* [xorshift32](./xorshift32)
  * 疑似乱数生成アルゴリズムxorshiftです。
  * IEC 61131-10 XML生成コマンド: `jiecc ./xorshift32/xorshift32.txt -I. -I./vendor/jiecunit/sys -o ./xorshift32/xorshift32.xml -t omron`

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
$ jiecc ./string_lib/string_lib.txt -I. -I./vendor/jiecunit/sys -o ./string_lib/string_lib.xml -t omron
```

`./test/string_lib/test_string_lib.xml`が生成されます。

2. [オムロン社製Sysmac Studioの場合の単体テストサンプルの実行方法](https://github.com/yunos0987/jiecunit#%E3%82%AA%E3%83%A0%E3%83%AD%E3%83%B3%E7%A4%BE%E8%A3%BDsysmac-studio%E3%81%AE%E5%A0%B4%E5%90%88%E3%81%AE%E5%8D%98%E4%BD%93%E3%83%86%E3%82%B9%E3%83%88%E3%82%B5%E3%83%B3%E3%83%97%E3%83%AB%E3%81%AE%E5%AE%9F%E8%A1%8C%E6%96%B9%E6%B3%95)の手順2以降を実行します。

## ライセンス

このプロジェクトはApache License 2.0の下でライセンスされています。詳細は[LICENSE](./LICENSE)ファイルを参照してください。
