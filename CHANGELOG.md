# 変更履歴 / Changelog

このファイルは、次のリリース以降の変更を記録します。それ以前の変更は、Git のタグ（`v1.2.0` 〜 `v3.2.0`）と GitHub のリリース・Pull Request（https://github.com/yunos0987/jieclib）を参照してください。

## Unreleased

### その他 / Other

- 貢献者向けの文書を整理しました。
  - `CODING_RULES.md` の内容を、新しく追加した `CONTRIBUTING.md` に移し、`CODING_RULES.md` を削除しました。あわせて、規約中のコード例などの明らかな誤記を直しました。
  - AI エージェント向けのルールを `AGENTS.md` にまとめました。`CLAUDE.md` は `AGENTS.md` を読み込むだけになりました。
  - `CHANGELOG.md` と `SECURITY.md` を追加しました。
- `scripts/run_tests.py` を追加しました。`src/` のライブラリと `test/` のテストを、各ファイルの先頭コメントに書かれたターゲットでコンパイルし、jier（`jiecc --run`）でテストを実行して合否を判定します。
- GitHub Actions の CI（`.github/workflows/ci.yml`）を追加しました。`main` と `develop` への push と Pull Request で、次を行います。
  - 追跡しているテキストファイルが UTF-8 BOM なし・LF であることの確認。
  - Windows と Linux のそれぞれで最新の Jiecc（Windows は https://www.graviness.com/iec_61131-3/jiecc.zip 、Linux は https://www.graviness.com/iec_61131-3/jiecc.tgz ）を取得し、すべてのライブラリとテストをコンパイル。
  - jier によるテストの実行。現在は、失敗しても CI を失敗にしません。
- `.github/dependabot.yml` を追加し、CI で使う actions の更新を Dependabot で確認するようにしました。
- README.md のテスト方法を、`scripts/run_tests.py` を使う手順に更新しました。
