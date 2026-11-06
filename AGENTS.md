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
- `jiecc --run` の終了コードは、テストの失敗を反映しない。テストの合否は標準出力の集計行から判定する（`scripts/run_tests.py` が行う）。
- `jiecc` の終了コードが 0 でも、出力に `error:` の行があれば失敗とみなす。手動でコンパイルや実行をした場合も、この行を確認する。
- 新しく追加したテストファイルは、jier で通し、必要な周期数と一緒に `scripts/jier_required.txt` に載せる（CI の `run-required` ジョブが必ず通す）。周期数は [docs/jier_cycles.md](docs/jier_cycles.md) の方法で測る。既存のテストファイルの多くは jier で通らないので、既存のファイルにテストを足すときは、新しいファイルに分ける。
- `scripts/run_tests.py` を変更したら、`python scripts/test_run_tests.py` を実行する。
- `.iec` を変更したら、`python scripts/lint.py` を実行し、`Lint passed.` と表示されることを確認する。キーワード・標準関数・型の名前の小文字、doc プラグマの書き方（`(*{doc ...}*)`）などを検査する（[CONTRIBUTING.md](CONTRIBUTING.md#規約の検査lint)）。
- 名前と型の規則（予約語・`p_` の接頭辞・可変長配列・構造体の戻り値・エイリアス型・POU 名の長さ・キーエンスの名前の制約）は、コンパイルした XML で検査する。`python scripts/run_tests.py --compile-only --output-dir out` の後に `python scripts/lint.py --xml-dir out` を実行する（CI の `compile` ジョブも行う）。
- 公開の POU を追加したら、テストを書く。`python scripts/pou_inventory.py --xml-dir out --check`（`run_tests.py --compile-only --output-dir out` の後）が、テストのない公開の POU を検出する。テストを書いたら、`scripts/pou_inventory_allow.txt` からその行を消す。
- 新しく書くコメントと doc プラグマは英語にし、テストには `// Fact:` を書く。既存の違反は `scripts/lint_baseline.json` に記録した分だけ許される。警告を通すために、この一覧に項目を足さない（CI が失敗にする）。直した警告は `python scripts/lint.py --update-baseline` で一覧から消す。

## 既知の落とし穴

- jier（`jiecc --run`）は、テストが終わった後も `--max-cycles` の周期数まで回り続ける。実行時間は周期数でほぼ決まる（1,000 周期あたり数秒）ので、周期数を必要以上に大きくしない。周期数が足りないと、集計行が出ないか、テストの数が合わずに失敗と判定される。`TEST_M`（複数の周期にわたるテスト）を使うファイルは、使う周期数を足した値を `scripts/jier_required.txt` の行に書く。
- jier（`jiecc --run`）は、関数を呼び出す位置より前にその関数が定義されている必要がある。後ろで定義した関数を呼ぶと `UNDEFINED_SYMBOL` になる。定義の順序を入れ替えて対処する。前方宣言は、PLC メーカーの環境が対応していないので使わない。
- `//` で始まるコメント行の最初の語が `{#` の場合（例: `//   {#define NAME(...)`）、jiepp はそれをディレクティブとして解釈する。Jiecc 8.0.0（jiepp 1.0.0）ではエラー（PP30）になる。コメントの中にディレクティブの例を書くときは、`{` を付けない（`#define NAME(...)`）。
- Jiecc 9.2.0 以降では、POU の本体直下に ST の文を `{st}` / `{end}` なしで書く。POU の見出し（名前・戻り型など）の直後の行が `(`、`[`、`+`、`-`、文字列リテラルで始まる文だと、見出しの続きとして読まれる。その場合は、見出しの末尾に `;` を付ける。
- POU の本体直下では、宣言は書いた位置から有効になる。文の後ろで `var` を宣言した変数を、その文より前で使うと `UNDEFINED_SYMBOL` になる。pragma、`var` ブロック、入れ子の定義は、文のまとまりの区切りになる。
- `(*{doc ...}*)` プラグマの中にアポストロフィ（`'`）を書くと、jiepp が警告（PP29）を出す。アポストロフィを使わない言い回しにするか、`$27` と書く。
