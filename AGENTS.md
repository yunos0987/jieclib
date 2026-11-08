# JiecLib Rules for AI Agents

JiecLib は、IEC 61131-3 ST 言語のライブラリです。コーディング規約・バージョン管理の詳細は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。ここには重複して書きません。

## ファイルの形式

- 文字コードは UTF-8 BOM なし、改行コードは LF とする。
- バッチ処理で文字列を置換するときは、置換元のファイルの文字コードに注意する。
- IEC 61131-3 のキーワードはすべて小文字とする（例: `if` / `var` / `and`）。
- コーディング規約（命名規則・インデント・テストの書き方など）は [CONTRIBUTING.md](CONTRIBUTING.md#コーディング規約) に従う。

## バージョン

- `VERSION` は、リリース時に `release vX.Y.Z` という独立したコミットで更新する。機能追加・修正のコミットでは更新しない。手順は [CONTRIBUTING.md](CONTRIBUTING.md#バージョン管理) を参照する。

## テスト

- 変更後は、リポジトリルートで `python scripts/run_tests.py` を実行し、`All checks passed.` と表示されることを確認する。`src/` のライブラリと `test/` のテストを、各ファイルの先頭コメントに書かれたターゲットでコンパイルし、jier（`jiecc --run`）でテストを実行する。
- 変更したファイルだけを確認する場合は、ファイルやディレクトリを指定する（例: `python scripts/run_tests.py src/math test/math`）。コンパイルだけなら `--compile-only`、テストの実行だけなら `--run-only` を付ける。
- jiecc は、`--jiecc PATH`、環境変数 `JIECC`、`PATH` 上の `jiecc` の順に探す。
- `scripts/run_tests.py` は、`jiecc --help` に `--allow-narrowing` があれば（Jiecc 9.4.0 以降）それを `jiecc --run` に付ける。手動で jier を走らせるときも付ける（jier の `len` は DINT を返すので、OMRON の UINT を変換する `uint_to_dint(len(s))` が縮小になり、既定では止まる）。
- JiecUnit v7.0.0 は、テストが終わると jier を `halt` で止める。`jiecc --run` の終了コードは、全テストが合格なら 0、失敗があれば 1 になる。`scripts/run_tests.py` は、終了コードと標準出力の集計行の両方で合否を判定する。
- `jiecc` の終了コードが 0 でも、出力に `error:` の行があれば失敗とみなす。手動でコンパイルや実行をした場合も、この行を確認する。
- すべてのテストファイルは jier で通す（CI の `run` ジョブが、全テストを jier で実行し、1 つでも失敗すると CI を失敗にする）。ライブラリのテストを 1 つにまとめるファイル（自分では `TEST_S` / `TEST_M` を定義せず、テストファイルを `{#include "..."}` するだけ。例: `test/container/test_container.iec`）は、まとめるファイルも実行するときは jier で実行しない（`SKIP run` と表示する）。新しいテストは、まとめるファイルではなく個別のテストファイルに書く。
- `scripts/run_tests.py` を変更したら、`python scripts/test_run_tests.py` を実行する。
- `.iec` を変更したら、`python scripts/lint.py` を実行し、`Lint passed.` と表示されることを確認する。キーワード・標準関数・型の名前の小文字、doc プラグマの書き方（`(*{doc ...}*)`）などを検査する（[CONTRIBUTING.md](CONTRIBUTING.md#規約の検査lint)）。
- 名前と型の規則（予約語・`p_` の接頭辞・可変長配列・構造体の戻り値・エイリアス型・POU 名の長さ・キーエンスの名前の制約）は、コンパイルした XML で検査する。`python scripts/run_tests.py --compile-only --output-dir out` の後に `python scripts/lint.py --xml-dir out` を実行する（CI の `compile` ジョブも行う）。
- ヘッダーのターゲットの宣言（`-t keyence` など）は、その開発環境で確かめたものだけにし、`src/<名前>/` と `test/<名前>/` で揃える（lint の `target-consistency`）。宣言を変えたら `python scripts/target_table.py --update` で README.md の表を作り直す。新しいファイルは omron だけを宣言する。
- 公開の POU を追加したら、テストを書く。`python scripts/pou_inventory.py --xml-dir out --check`（`run_tests.py --compile-only --output-dir out` の後）が、テストのない公開の POU を検出する。テストを書いたら、`scripts/pou_inventory_allow.txt` からその行を消す。
- 新しく書くコメントと doc プラグマは英語にし、テストには `// Fact:` を書く。既存の違反は `scripts/lint_baseline.json` に記録した分だけ許される。警告を通すために、この一覧に項目を足さない（CI が失敗にする）。直した警告は `python scripts/lint.py --update-baseline` で一覧から消す。

## 既知の落とし穴

- `scripts/run_tests.py` の `--max-cycles`（既定 2000）は、`halt` に届かないテストを止めるための上限である。`TEST_M`（複数の周期にわたるテスト）が使う周期数の合計がこれを超えると、集計行が出ずに失敗と判定される。1 周期の中で終わらない処理（無限ループなど）は、`--timeout`（既定 300 秒）で止まり、失敗になる。
- 1 つのテストファイルは、jier で単独で実行して 60 秒以内に終わるようにする（全件を並列で実行すると 2〜3 倍かかる。`--timeout` の既定 300 秒を超えると失敗になる）。`scripts/run_tests.py` は、run の行に各ファイルの秒数（`[12.3 s]`）を出す。60 秒を超えるファイルは、`{#ifdef _JIER}` で jier のときだけ処理を減らす（例: `test/random/test_random_distribution.iec` の標本の数。許容幅は減らした数で計算し直す）。PLC のターゲットでの処理は変えない。
- jier（`jiecc --run`）は、関数を呼び出す位置より前にその関数が定義されている必要がある。後ろで定義した関数を呼ぶと `UNDEFINED_SYMBOL` になる。定義の順序を入れ替えて対処する。前方宣言は、PLC メーカーの環境が対応していないので使わない。
- `//` で始まるコメント行の最初の語が `{#` の場合（例: `//   {#define NAME(...)`）、jiepp はそれをディレクティブとして解釈する。Jiecc 8.0.0（jiepp 1.0.0）ではエラー（PP30）になる。コメントの中にディレクティブの例を書くときは、`{` を付けない（`#define NAME(...)`）。
- Jiecc 9.2.0 以降では、POU の本体直下に ST の文を `{st}` / `{end}` なしで書く。POU の見出し（名前・戻り型など）の直後の行が `(`、`[`、`+`、`-`、文字列リテラルで始まる文だと、見出しの続きとして読まれる。その場合は、見出しの末尾に `;` を付ける。
- POU の本体直下では、宣言は書いた位置から有効になる。文の後ろで `var` を宣言した変数を、その文より前で使うと `UNDEFINED_SYMBOL` になる。pragma、`var` ブロック、入れ子の定義は、文のまとまりの区切りになる。
- `(*{doc ...}*)` プラグマの中にアポストロフィ（`'`）を書くと、jiepp が警告（PP29）を出す。アポストロフィを使わない言い回しにするか、`$27` と書く。
