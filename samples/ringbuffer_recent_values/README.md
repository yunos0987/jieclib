# リングバッファ（直近の値の保持）

測定値の直近 10 個を保持し、その平均を出します。`container/ringbuffer` のテンプレートの使い方を示します。

- マクロ `RingBufferItemType` に要素の型（`lreal`）を指定すると、`RingBuffer_lreal_init`・`RingBuffer_lreal_enqueue`・`RingBuffer_lreal_dequeue` が作られます。状態は `RingBuffer_t` で、要素の配列はプログラムが持ちます。
- 上書きモード（`RingBuffer_lreal_init` の第 3 引数を真）にすると、満杯のときに最も古い値を捨てて追加します。
- 保持している値は、`items[(r_idx + k) mod buf_size]`（`k` = 0 から `w_idx - r_idx - 1`。古い順）です。
- `RingBuffer_t` の `w_idx`・`r_idx` は、取り込むたびに増え続ける dint です（テンプレートの仕様）。約 2^31 回（1 ms ごとに取り込むと約 24 日）で桁あふれするので、長く動かすときは、定期的に `RingBuffer_lreal_init` で初期化し直してください。

## XML の生成

リポジトリのルートで、次のコマンドを実行します。

```
$ jiecc ./samples/ringbuffer_recent_values/ringbuffer_recent_values.iec -I./src -o ./samples/ringbuffer_recent_values/ringbuffer_recent_values.xml -t omron
```

## Sysmac Studio での使い方

1. 生成した `ringbuffer_recent_values.xml` を、[ ツール | IEC 61131-10 XML | インポート ] で取り込みます。
2. タスク設定で、プログラム `RingBufferSample` をプライマリ定周期タスクに割り付けます。
3. ビルドして、シミュレータで実行します。 変数 `measured` に測定値を入れ、`sample_now` を 1 周期だけ真にすると、値を取り込みます。`recent_average` に平均、`kept_count` に保持している個数が出ます。
