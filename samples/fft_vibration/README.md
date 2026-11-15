# 振動の周波数分析（FFT）

模擬した振動の信号を FFT で分析し、いちばん大きい周波数成分（ピーク）の周波数と振幅を求めます。`fft/` の窓関数・実数 FFT・振幅スペクトルの使い方を示します。

- 信号: オフセット 0.2 に、64 Hz・振幅 1.5 と 200 Hz・振幅 0.4 の正弦波を足したものを、1024 Hz で 256 点サンプリングします。周波数の分解能は 1024 / 256 = 4 Hz で、64 Hz はビン 16、200 Hz はビン 50 です。
- 窓関数: `Fft_window_hann` で Hann 窓を作り、`Vector_elementwise_mul` で信号に掛けます。窓の係数の平均（`Fft_window_gain`、Hann 窓は 0.5）を `Fft_amplitude` の `window_gain` に渡し、窓で小さくなった振幅を補正します。
- 変換: `Fft_rfft` で 256 点の実数の信号を変換し、片側の 129 点（0〜512 Hz）のスペクトルを得ます。
- 振幅: `Fft_amplitude` で、各周波数の振幅（正弦波の振幅そのもの）にします。直流（ビン 0）を除いて最大のビンを探し、周波数 `ビン × 1024 / 256` と振幅を出します。この例では、`peak_frequency` が 64.0、`peak_amplitude` が 1.5、`dc_amplitude` が 0.2 になります。

分析は 1 回の呼び出しで終わります（256 点の実数 FFT は、128 点の複素 FFT の 448 回のバタフライと、前後の処理です）。点の数を増やすときは、タスクの周期に収まるかを確かめてください。

## XML の生成

リポジトリのルートで、次のコマンドを実行します。

```
$ jiecc ./samples/fft_vibration/fft_vibration.iec -I./src -o ./samples/fft_vibration/fft_vibration.xml -t omron
```

## Sysmac Studio での使い方

1. 生成した `fft_vibration.xml` を、[ ツール | IEC 61131-10 XML | インポート ] で取り込みます。
2. タスク設定で、プログラム `FftVibrationSample` をタスクに割り付けます。
3. ビルドして、シミュレータで実行します。最初の周期で分析し、`peak_frequency`・`peak_amplitude`・`peak_bin`・`dc_amplitude` に結果が入ります。`main_frequency` などを変えてから `analyze` を真にすると、もう一度分析します。
