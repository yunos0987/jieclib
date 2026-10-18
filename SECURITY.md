# セキュリティポリシー / Security Policy

**English summary:** Please report security vulnerabilities privately through GitHub's private vulnerability reporting (the "Report a vulnerability" button in the repository's Security tab). Do not open a public issue for a vulnerability. Security fixes are made for the latest release and for the `develop` branch. The rest of this document is in Japanese.

## 脆弱性の報告方法

脆弱性は、公開の Issue や Pull Request では報告しないでください。GitHub の非公開の脆弱性報告（private vulnerability reporting）を使ってください。

1. リポジトリの **Security** タブを開く
2. **Report a vulnerability** を押す
3. 下記の内容を書いて送る

報告は管理者だけに届きます。修正が公開されるまで、報告内容は公開しないでください。

## 対象バージョン

セキュリティ修正の対象は、最新のリリースと `develop` ブランチです。古いリリースへの修正の取り込み（バックポート）は予定していません。JiecLib のバージョンは、リポジトリルートの `VERSION` ファイルと Git のタグ（`vX.Y.Z`）で確認できます。

## 報告に含めてほしい内容

- 影響を受けるバージョン（タグ名、または commit ハッシュ）
- 使った OS、Python と Jiecc のバージョン、PLC の開発環境とそのバージョン
- 問題を再現できる最小のファイルとコマンドライン
- 起きたことと、想定していた動作
- 分かる場合は、原因の見立てや修正案

## 対象範囲

JiecLib は、IEC 61131-3 ST 言語のライブラリ（`.iec` ファイル）と、Jiecc を実行する Python の補助スクリプト（`scripts/`）です。次のような問題を、セキュリティ上の問題として扱います。

- `scripts/` のスクリプトに、意図しないコマンドの実行、意図しないファイルの読み書き・削除につながる欠陥があること
- `.iec` ライブラリの欠陥により、ライブラリを組み込んだ PLC プログラムが、配列の範囲外へのアクセスなど、利用者の意図しないメモリやデータへのアクセスを行ってしまうこと

### 対象外

- 利用者が実行を指示した Jiecc や PLC の開発環境（Sysmac Studio など）自体の問題。それぞれの提供元に報告してください。
- テストフレームワーク JiecUnit（`vendor/jiecunit`）の問題。[JiecUnit のリポジトリ](https://github.com/yunos0987/jiecunit)に報告してください。
- 利用者が書いたプログラムの内容による問題
