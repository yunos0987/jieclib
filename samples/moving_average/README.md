# 移動平均とメディアンフィルタ

ノイズのある測定値を、3 通りの方法でなめらかにします。`signal/` のテンプレートの具体化の仕方と、ファンクションブロックの使い方を示します。

- メディアンフィルタ（`Signal_median_n5`）: 直近 5 個の中央値を出し、短いスパイクを取り除きます。容量は奇数にします。
- 移動平均（`Signal_movingAverage_n10`）: 直近 10 個の平均を出し、ノイズを減らします。
- 一次遅れ（`Signal_lowPass`）: 時定数 0.5 秒でなめらかにします。`sample_time` にタスクの周期（秒）を渡します。

テンプレートは、マクロ（`SignalMovingAverageName`・`SignalMovingAverageCapacity` など）で名前と容量を決めて取り込みます。容量がマクロなので、バッファはファンクションブロックの中にあります。

## XML の生成

リポジトリのルートで、次のコマンドを実行します。

```
$ jiecc ./samples/moving_average/moving_average.iec -I./src -o ./samples/moving_average/moving_average.xml -t omron
```

## Sysmac Studio での使い方

1. 生成した `moving_average.xml` を、[ ツール | IEC 61131-10 XML | インポート ] で取り込みます。
2. タスク設定で、プログラム `MovingAverageSample` を定周期タスクに割り付け、変数 `task_period` にそのタスクの周期（秒）を入れます。
3. ビルドして、シミュレータで実行します。変数 `measured` に値を入れると、`median_value`・`average_value`・`lag_value` が変わります。`restart` を真にすると、フィルタを今の値からやり直します。
