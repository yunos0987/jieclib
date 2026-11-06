# 乱数による工程の変動

工程の値を、目標値に正規分布の変動を加えて模擬します。まれな不良（ベルヌーイ試行）も出します。機械なしで制御のプログラムを試すときに使えます。`random/mersenne_twister.iec` の使い方を示します。

- `MersenneTwister_init` で、生成器を一度だけ初期化します。シードが同じなら、再起動の後も同じ系列になります（試験を再現できます）。
- `MersenneTwister_nextGaussian(mean, sigma)` が正規分布の値を、`MersenneTwister_nextBernoulli(prob)` が確率 `prob` で真を返します。

## XML の生成

リポジトリのルートで、次のコマンドを実行します。

```
$ jiecc ./samples/random_process_variation/random_process_variation.iec -I./src -o ./samples/random_process_variation/random_process_variation.xml -t omron
```

## Sysmac Studio での使い方

1. 生成した `random_process_variation.xml` を、[ ツール | IEC 61131-10 XML | インポート ] で取り込みます。
2. タスク設定で、プログラム `RandomSample` をプライマリ定周期タスクに割り付けます。
3. ビルドして、シミュレータで実行します。 変数 `target`・`variation`・`defect_rate` を変えると、`process_value` と `defect` が変わります。
