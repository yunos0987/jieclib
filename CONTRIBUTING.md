# Contributing to JiecLib

JiecLib への貢献に関心を持っていただき、ありがとうございます。

## 目次

1. [貢献の流れ](#貢献の流れ)
2. [テストの実行](#テストの実行)
3. [コーディング規約](#コーディング規約)
   1. [目的](#目的)
   2. [コーディングスタイル](#コーディングスタイル)
   3. [命名規則](#命名規則)
   4. [フォーマット](#フォーマット)
   5. [エラーハンドリング](#エラーハンドリング)
   6. [テスト](#テスト)
   7. [ドキュメント](#ドキュメント)
   8. [依存関係](#依存関係)
4. [バージョン管理](#バージョン管理)

## 貢献の流れ

1. `develop` ブランチから作業用のブランチを作る。
2. 変更する。コミットは、目的が分かる最小の単位にする。
3. `python scripts/run_tests.py` を実行し、`All checks passed.` と表示されることを確認する。`python scripts/lint.py` を実行し、`Lint passed.` と表示されることを確認する（[テストの実行](#テストの実行)）。
4. 利用者に関係する変更は、[CHANGELOG.md](CHANGELOG.md) の `[Unreleased]` 節に書く。
5. Pull Request を作る。通常は `develop` を宛先にする。`main` への Pull Request は、`develop` からのリリースの取り込みに使う。本文は、テンプレート（`.github/pull_request_template.md`）の欄を埋める。`src/` を変更したときは Sysmac Studio のシミュレータでの実行（L3）の結果を、keyence を宣言したファイルを変更したときは KV Studio での実行（L4）の結果を書く（未実施なら理由を書く）。CI がこの欄の書式を確かめる。
6. リリースは、`main` のコミットにタグ `vX.Y.Z` を付けて行う（[バージョン管理](#バージョン管理)）。

## テストの実行

[Jiecc](https://www.graviness.com/iec_61131-3/jiecc.html) が必要です。バージョンの要件は [README.md](README.md#必要環境) を参照してください。JiecUnit は Git submodule（`vendor/jiecunit`）として取り込んでいるので、クローンした後に `git submodule update --init --recursive` を実行しておいてください。

```
$ cd <JiecLib Project Root>
$ python scripts/run_tests.py
```

`scripts/run_tests.py` は、次の 2 つを行います。

- コンパイル: `src/` のライブラリと `samples/` の利用例（先頭コメントに `$ jiecc` のコマンド行があるファイル）と、`test/` のテスト（`DEFINE_CONFIGURATION` を含むファイル）を、先頭コメントの `-t` に書かれたターゲット（書かれていなければ `omron`）でコンパイルします。生成した XML は一時ディレクトリに出力し、終了時に削除します。
- 実行: `test/` のテストを、jier（`jiecc --run`）で実行します。`jiecc --run` の終了コードはテストの失敗を反映しないため、JiecUnit の集計行（`[========] N tests ran.` など）から合否を判定します。

どちらも、`jiecc` の出力に `error:` の行があれば失敗とみなします。すべて成功すると、最後に `All checks passed.` と表示されます。

jiecc は、`--jiecc PATH`、環境変数 `JIECC`、`PATH` の順に探します。

```
$ python scripts/run_tests.py --jiecc /path/to/jiecc.exe
```

主なオプションは次のとおりです。

- ファイルやディレクトリを指定すると、それだけを確認します（例: `python scripts/run_tests.py src/math test/math`）。
- `--compile-only`: コンパイルだけを行います。
- `--run-only`: テストの実行だけを行います。
- `--jobs N`: 並列に実行する jiecc の数（既定: CPU 数）。
- `--max-cycles N`: `jiecc --run` の最大スキャン回数（既定: 2000。[jier の周期数](#jier-の周期数)）。
- `--timeout SEC`: jiecc 1 回あたりの制限時間（秒）。時間を超えると、jiecc が起動した子のプロセスも含めて終了させ、失敗とします。
- `--output-dir DIR`: 生成した XML を消さずに、`DIR/<ターゲット>/<ファイルのパス>.xml`（例: `DIR/omron/src/string_lib/string_lib.xml`）に残します。コンパイルに失敗したファイルの XML は残しません。`--run-only` とは一緒に使えません。
- `--paths-from FILE`: 対象のパスを、ファイルから 1 行 1 項目で読みます（下記）。

#### jier の周期数

jier は、テストが終わった後も `--max-cycles` で指定した周期数まで回り続けます。そのため、実行時間は周期数でほぼ決まります（1,000 周期あたり数秒）。周期数が足りないと、集計行が出ないか、`[========] Running N tests.` の N と実行したテストの数が合わず、失敗と判定されます。ファイルごとに必要な周期数は [docs/jier_cycles.md](docs/jier_cycles.md) にあります。

#### jier で必ず通すテスト

新しく追加したテストファイルは、`scripts/jier_required.txt` に、必要な周期数と一緒に載せてください。CI の `run-required` ジョブが、Windows と Linux で、この一覧のファイルを jier で実行し、1 つでも失敗すると CI を失敗にします（全テストを実行する `run` ジョブは、参考扱いです）。

```
# <リポジトリからの相対パス> <周期数>
test/math/test_floor_large.iec 1000
```

- パスの区切りは `/` にしてください。`\` を含む行、存在しないパス、同じパスの重複はエラーになります。テストを実行するとき（`--compile-only` を付けないとき）は、テストファイルを含まないパスもエラーになります。
- 周期数は、[docs/jier_cycles.md](docs/jier_cycles.md) の方法で測った値にしてください。
- 手元では `python scripts/run_tests.py --run-only --paths-from scripts/jier_required.txt` で確かめられます。
- 既存のテストファイルの多くは、jier で通りません（CHANGELOG.md 4.0.0 の「既知の問題」）。既存のファイルにテストを足すときは、jier で通る新しいファイルに分けて、この一覧に載せてください。

### 規約の検査（lint）

`scripts/lint.py` は、[コーディング規約](#コーディング規約)と AGENTS.md の規約のうち、ソースを読んで判定できるものを検査します。jiecc は要りません。

```
$ python scripts/lint.py
$ python scripts/lint.py src/math test/math
```

`src/`・`test/`・`samples/` の `.iec` を読み、違反を `<path>:<line>: error: <規則>: <説明>`（警告は `warning:`）の形で 1 行ずつ出力します。違反がなければ、最後に `Lint passed.` と表示されます。規則の一覧は `scripts/lint.py` の先頭のコメントにあります。キーワードなどの小文字の規則では、`{#define}` で定義したマクロの名前（`STRING` など）と、`.` の後のメンバーの名前は検査しません。マクロの名前は、どのファイルで定義したものでも、すべてのファイルで検査の対象外になります。

- エラーの規則（キーワードなどを小文字で書く、doc プラグマを `(*{doc ...}*)` の形で書く、doc プラグマの引用符を対にする、`src/` の POU の直前に doc プラグマを書く、`continue` と `/* */` を使わない）は、1 件でもあれば失敗です。
- 警告の規則（コメントと doc プラグマを英語で書く、テストに `// Fact:` を書く）は、既存の違反を `scripts/lint_baseline.json` に一覧として記録しています。一覧にない警告が出たら失敗です。新しく書くコードでは、警告も出さないでください。
- 一覧の項目は、ファイルと、コメントの最初の日本語の行（またはテストの名前）です。行番号は含まないので、コードを動かしても変わりません。既存の日本語のコメントの、最初の日本語の行を書き換えると、新しい警告になります。そのときは英語に直してください。
- 警告を直したら、`python scripts/lint.py --update-baseline` で一覧から消します。このオプションは、一覧にある規則の項目を消すだけで、足しません。一覧に節のない規則（新しく足した警告の規則）だけは、今の警告で節を作ります。一覧のファイルがないときはエラーになります。
- 一覧に項目を足す変更は、CI（`pr-checks.yml` の `lint-baseline` ジョブ）が失敗にします。規則そのものを見直す Pull Request だけは、`python scripts/lint.py --reset-baseline` で一覧を作り直し、管理者がラベル `lint-baseline-reset` を付けます。本文に理由を書いてください。
- `scripts/test_lint.py` は、`lint.py` の単体テストです。規則ごとの違反の例と違反しない例が `scripts/lint_testdata/` にあります。

#### コンパイルした XML の検査

名前と型の規則は、jiecc でコンパイルした XML を読んで検査します。テンプレートが作る POU や変数の名前も検査できます。

```
$ python scripts/run_tests.py --compile-only --output-dir out
$ python scripts/lint.py --xml-dir out
```

`--xml-dir` を付けると、ソースの規則に加えて、次の規則を検査します（`scripts/lint_xml.py`）。違反は `<XML>: error: <規則>: <POU 名>.<名前>: <説明>` の形で出力します。同じ POU は、それを include したすべての XML に入るので、規則・POU・名前ごとに 1 回だけ出力します。

| 規則 | 重さ | 内容 |
|---|---|---|
| `xml-missing` | エラー | ヘッダーで宣言したターゲットの XML がない、または読めない（コンパイルの失敗を見逃さない） |
| `pou-name-length` | エラー | POU 名が 64 バイトを超える |
| `reserved-name` | エラー | 変数・構造体のメンバーの名前が `left`・`right`・`len`・`cmp`・`dec` |
| `omron-p-prefix` | エラー | 変数・構造体のメンバーの名前が `p_`・`P_` で始まる |
| `varlen-array-inout` | エラー | 可変長配列（`array[*]`）を `var_in_out` 以外で使う |
| `no-struct-return` | エラー | 関数が構造体を返す |
| `no-alias-type` | エラー | 直接派生型（エイリアス型）を宣言する |
| `keyence-names` | 警告 | keyence（または mitsubishi）を宣言したファイルで、1 文字の名前、`h` / `H` で始まり `_` を含まない変数名、`^[rRtTcC]\d+$` の変数名を使う |

- 対象は、関数・ファンクションブロックの変数（引数・局所変数・一時変数）と、構造体のメンバーです。テストのプログラム（`Program`）と、構成（`Configuration`）のグローバル変数（テストにだけある）と、JiecUnit の POU と型（`vendor/jiecunit` で定義し、`src/` で定義していないもの、`JiecTest_` で始まるもの）は検査しません。
- `keyence-names` の既存の違反は、`scripts/lint_baseline.json` の `keyence-names` の節にあります（項目は `<POU 名>.<名前>`）。`--xml-dir` を付けずに `--update-baseline` を実行しても、この節は変わりません。
- CI の `compile` ジョブが、コンパイルの後にこの検査を行います。
- ファイルやディレクトリを指定すると（例: `python scripts/lint.py --xml-dir out src/math`）、その下のファイルの XML だけを読みます。

#### テストのない POU の検査

公開の POU には、テストを書いてください。`scripts/pou_inventory.py` は、コンパイルした XML（omron）を読み、テストのプログラムから直接呼ばれていない公開の POU を一覧にします。

```
$ python scripts/run_tests.py --compile-only --output-dir out
$ python scripts/pou_inventory.py --xml-dir out --check
```

- `src/` のエントリファイルの XML にある POU（`src/` が具体化したテンプレートの POU を含む）は、1 つずつテストが要ります。
- テストでだけ具体化するテンプレート（container など）は、操作ごとにまとめます。`HashMap_*_copy` のどれか 1 つの具体化が呼ばれていれば、テストありです。操作の形は、テンプレートの名前を作るマクロ（`{#define _HASHMAP_COPY_(T) HashMap_@@T@@_copy}`）から求めます。
- 名前に `private` または `_static_` を含む POU は、内部の POU なので対象外です。
- テストを書かない理由がある POU は、`scripts/pou_inventory_allow.txt` に `<名前またはテンプレートの形> <理由>` の形で載せます。`--check` は、一覧にないテストなしの POU、どの分類にも当てはまらない POU（未分類）、理由のない行、古い行（POU がない、またはテストができた）があれば失敗します。テストを書いたら、一覧の行を消してください。
- CI の `compile` ジョブが、XML の lint の後に `--check` を実行します。

### CI

GitHub Actions の CI（`.github/workflows/ci.yml`）は、Windows と Linux の両方で、最新の Jiecc（Windows は [jiecc.zip](https://www.graviness.com/iec_61131-3/jiecc.zip)、Linux は [jiecc.tgz](https://www.graviness.com/iec_61131-3/jiecc.tgz)）を取得し、`--compile-only` と `--run-only` を別々のジョブで実行します。現在、全テストを実行する `run` ジョブは失敗しても CI を失敗にしません。`run-required` ジョブは、`scripts/jier_required.txt` のテストファイルを jier で実行し（[jier で必ず通すテスト](#jier-で必ず通すテスト)）、失敗すると CI を失敗にします。このジョブは、`scripts/run_tests.py` と `scripts/lint.py` の単体テストも、jiecc を使って実行します。`compile` ジョブは、コンパイルの後に、生成した XML を `python scripts/lint.py --xml-dir out` で検査します（[コンパイルした XML の検査](#コンパイルした-xml-の検査)）。`lint` ジョブは `scripts/lint.py` とその単体テストを実行します。

Pull Request では、`.github/workflows/pr-checks.yml` も実行します。本文やラベルを変えたときにも再実行されます。

- `lint-baseline`: `scripts/lint_baseline.json` に、宛先のブランチとの分岐点のコミットにない項目があれば失敗にします。ラベル `lint-baseline-reset` があれば省略します。
- `pr-body`: 本文の L3・L4 の欄の書式を確かめます（`scripts/check_pr_body.py`）。宛先が `main` の Pull Request は対象外です。

## コーディング規約

### 目的

このコーディング規約は、JiecLibプロジェクトにおけるIEC 61131-3 ST言語コードの品質と一貫性を保つために定められています。

- コードの可読性と保守性の向上
- チーム開発における統一されたコーディングスタイルの確立
- 各社プログラミングツールとの互換性の確保
- 生成AIとの協調開発における効率性の向上
- テスト駆動開発（TDD）による品質保証

### コーディングスタイル

- 文字コードは、UTF-8 BOMなし、改行コードをLFとする。
- コメントやdocプラグマ内では、英語を使用すること。
- continue構文を使用しないこと。
	- オムロン環境が未サポートのため。
- 直接派生型（エイリアス型; `type <var>alias_name</var>: <var>name</var>; end`）を使用しないこと。
	- オムロン環境が未サポートのため。
- 多次元配列の初期値は、1次元フラットで要素数だけ合わせて記述します。
```
var a: array[0..1, 0..2] of dint := [16#00, 16#01, 16#02, 16#10, 16#11, 16#12];
```
- 可変長配列（e.g. array[\*] of lreal）は、var_in_out引数でのみ使用すること。
- ファンクションの戻り値に構造体型を使用しないこと。構造体データを結果として得る必要がある場合、var_in_outを使用する。
	- オムロン環境が未サポートのため。
- 論理式における or や and のオペランドが式の場合、括弧で括る。
```
if ((i = 0) and (j = 0)) or first_time then
	...
end_if;
```
- 一行で書くことができる注釈は、// ～ を使用する。複数行の注釈は、(\* ～ \*) を使用する。/\* ～ \*/を使用しない。
- ブロック内が空になることは許可されません。; のみを挿入します。
```
if x = 2 then
  ; // do nothing.
else
  y := 10;
end_if;
```
- 異常系の実装においては、enoをfalseに設定してそのPOUを終える。その際、戻り値を設定する必要はない。
```
if ＜異常＞ then
	eno := false;
	return;
end_if;
```
- and, or, xor演算子は、整数型の要素には使用できません。
- POU呼び出しにおいて、仮引数有りと仮引数無しの引数が混在してはいけない。
- for ループのカウンタをループ本体内で変更しないこと。早期脱出が必要な場合は while ループと条件式を組み合わせること。
- 統計ライブラリ（/statsディレクトリ以下）において、内部で可変のwork領域が必要であれば、var_in_outで呼び出し元で用意する。このとき、当該引数変数名の接尾に_workを付加する。ただし、既にworkであれば付加しなくて良い。
- 統計ライブラリ（/statsディレクトリ以下）において、`Array_isRegular`でない配列を異常として扱う。
- 線形代数ライブラリ（/linalgディレクトリ以下）において、ベクトルや行列の基底の型は、lreal型とする。

### 命名規則

- 以下の名前で定義することを禁止する。
  - left, right, len
    - IEC 61131-3 の定義と重複するため。
  - `h`, `H`で始まり、`_`を含まない変数名
    - キーエンス環境の制約
  - `^[rRtTcC]\d+$` にマッチする変数名
    - キーエンス環境の制約
  - `p_`, `P_`で始まる要素名
    - オムロン環境の制約。
  - cmp, dec
    - オムロン環境の制約。
  - アルファベット1文字の要素名。
    - キーエンス環境や三菱環境の制約。
- POU名は、64バイト以内とすること。
  - キーエンス環境の制約。
- IEC 61131-3は、ASCIIの大文字・小文字を区別しないことに注意すること。
	- 例えば、行列を意味する変数Aと、ベクトルを意味する変数aを同一のものとして解釈します。

### フォーマット

- インデントにはタブ文字を使用する。スペース文字によるインデントは使用しない。
- エディタのタブ幅設定は4文字とする。
- コード部は、POUの本体に直接書きます（Jiecc 9.2.0以降）。`{st}` ~ `{end}`では括りません。defineマクロ内でも、`${st$}` ~ `${end$}`は不要です。

### エラーハンドリング

- すべてのファンクション・ファンクションブロックは、`eno`（Enable Output）パラメータを使用してエラー状態を通知する。
- エラー発生時は`eno := false`を設定し、`return`で処理を終了する。
- 入力パラメータの妥当性検証（配列の正規性チェック、範囲チェックなど）を実装する。
- 統計ライブラリにおいては、数値計算の特異点（ゼロ除算、負の数の平方根など）に対する適切な処理を実装する。

### テスト

次の例のように記述すること。要点については後述する。

```
TEST_S(test_mean)
	var
		x_regular: array[0..3] of lreal;
		x_zeros: array[0..2] of lreal;
		x_negative: array[0..2] of lreal;
		mean_val: lreal;
	end
	// Fact: The mean of a sequence of values equals their arithmetic average.
		// Arrange
	x_regular[0] := 6.0;
	x_regular[1] := 3.0;
	x_regular[2] := 5.0;
	x_regular[3] := 2.0;
		// Act
	mean_val := mean(x_regular);
		// Assert
	EXPECT_NEAR(4.0, mean_val, 1.0e-6);

	// Fact: The mean of all-zero values is 0.
		// Arrange
	x_zeros[0] := 0.0;
	x_zeros[1] := 0.0;
	x_zeros[2] := 0.0;
		// Act/Assert
	EXPECT_NEAR(0.0, mean(x_zeros), 1.0e-6);

	// Fact: The mean is correctly computed even when values include negatives.
		// Arrange
	x_negative[0] := -7.0;
	x_negative[1] := -1.0;
	x_negative[2] := 2.0;
		// Act
	mean_val := mean(x_negative);
		// Assert
	EXPECT_NEAR(-2.0, mean_val, 1.0e-6);
END_TEST_S
```

- 1事実を1インスタンスでテストコードを記述する。
- 1関数のn事実を一つのTEST_S内に記述する。
  - オムロン環境にて、タスクの数が増えると登録に時間が掛かるため。
- 事実を1行のコメントで記述する。
- AAA形式で、Arrange節, Act節, Assert節を明示する。

以下は個別。

- 統計ライブラリ（/test/statsディレクトリ以下）におけるp値の検証は、EXPECT_NEARを使用することを基本とし、abs_errorを1.0e-4以下とする。

### ドキュメント

- POU、POUの引数、および型の先頭にdocプラグマを記述すること。
- docプラグマ内では、まず一行で示し、改行して詳細を記述すること。
```
(*{doc Obtain basic statistical measures.
Compute the mean, variance, skewness, and kurtosis.
@inout data Array containing the sample data.
	It must be a regular array (the lower bound is 0 and the number of elements is at least 1).
@input n Use the first n elements of data.
	If -1 is specified, all elements of data are used.
	Default value: -1
@output mean Mean (arithmetic mean).
@output variance Variance.
@output skewness Skewness.
@output kurtosis Kurtosis.
@return Number of array elements actually used in the computation.
@error If data is not a regular array. }*)
function Stats_statistics_value: dint
	_PROLOGUE_OF_FUNCTION_()
	var_in_out
		(*{doc Array containing the sample data.}*)
		data: array[*] of lreal;
	end
	var_input
		(*{doc Use the first n elements of data.}*)
		n: dint := -1;
	end
	var_output
		(*{doc Mean (arithmetic mean).}*)
		mean: lreal;
		(*{doc Variance.}*)
		variance: lreal;
		(*{doc Skewness.}*)
		skewness: lreal;
		(*{doc Kurtosis.}*)
		kurtosis: lreal;
	end
	:
end
```

### 依存関係

- JiecUnitテストフレームワークへの依存は、テストコードのみに限定する。
- `{#include}`プリプロセッサ指令を使用してモジュール間の依存関係を明確にする。

## バージョン管理

- Gitを使用してソースコードを管理する。
- `main`ブランチは常にビルド可能で、テストが通る状態を維持する。
- タグを使用してリリースバージョンを管理する（例：v1.0.0）。
- `.gitignore`ファイルを適切に設定し、生成ファイル（*.xml、__pycache__など）をリポジトリに含めない。

JiecLib のバージョンは、リポジトリルートの `VERSION` ファイルに `MAJOR.MINOR.PATCH`（例: `3.4.0`）の 1 行で記録します。バージョンを表すマクロはありません。Git のタグ（`vX.Y.Z`）は、`VERSION` と同じ番号を `main` のコミットに付けたものです。

`VERSION` は、リリース専用のコミット（メッセージは `release vX.Y.Z`）でだけ更新します。機能追加・修正のコミットでは更新しません。変更の内容は、Pull Request ごとに [CHANGELOG.md](CHANGELOG.md) の `[Unreleased]` 節に書いておきます。リリースのコミットで、`[Unreleased]` 節の見出しを `[X.Y.Z] - 日付` に置き換え、次の変更のために空の `[Unreleased]` 節を設けます。`develop` を `main` にマージした後、`main` のコミットにタグを付けます。

GitHub で、そのタグの Release を公開すると、`.github/workflows/release.yml` が `src/` の XML を作り、ターゲットごとの zip（`jieclib-X.Y.Z-omron.zip`・`jieclib-X.Y.Z-keyence.zip`）を Release に添付します。zip には、使った Jiecc の版と取り込みの注意（`IMPORT_NOTES.txt`）が入ります。タグが `v` + `VERSION` と一致しないときは、何も添付せずに失敗します。添付をやり直すときは、Actions の画面から `Release XML` をタグを指定して実行します（`workflow_dispatch`）。

```
$ git tag vX.Y.Z
$ git push origin vX.Y.Z
```
