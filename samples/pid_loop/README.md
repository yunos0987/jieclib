# PID 制御のループ

`Control_pid`（並列形の PID）と `Control_ramp`（ランプ）の使い方を示します。機械の代わりに、一次遅れ（`Signal_lowPass`）で模擬した対象を制御するので、シミュレータで試せます。

- 目標値 `target` は、`Control_ramp` で毎秒 10 ずつ近づけてから、`Control_pid` の `setpoint` に渡します。
- `Control_pid` は、出力を 0〜100% に制限します。出力が上下限に達している間は、積分を止めます（アンチワインドアップ）。
- `manual` を真にすると、出力は `manual_output` になります。自動に戻したときに、出力は飛びません。
- 微分は測定値に対して行い（目標値を変えても出力が跳ねない）、時定数 `derivative_filter` で平滑化します。
- 実機では、模擬した対象（`process`）を、機械の入力（`process_value`）と出力（`output_percent`）に置き換えます。

## XML の生成

リポジトリのルートで、次のコマンドを実行します。

```
$ jiecc ./samples/pid_loop/pid_loop.iec -I./src -o ./samples/pid_loop/pid_loop.xml -t omron
```

## Sysmac Studio での使い方

1. 生成した `pid_loop.xml` を、[ ツール | IEC 61131-10 XML | インポート ] で取り込みます。
2. タスク設定で、プログラム `PidLoopSample` を定周期タスクに割り付け、変数 `task_period` にそのタスクの周期（秒）を入れます。
3. ビルドして、シミュレータで実行します。`process_value` が `setpoint` に近づきます。`target` を変えたり、`manual` を切り替えたりして、出力の動きを確かめます。
