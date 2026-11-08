# Modbus RTU の CRC

Modbus RTU の要求（ファンクション 03、保持レジスタの読み出し）を CRC 付きで組み立て、受信した応答の CRC を確かめます。`hash/crc16.iec` の使い方を示します。

- `CRC16_modbus(dat, offset, length)` で、電文の CRC を求めます。
- Modbus RTU は、CRC を下位バイト、上位バイトの順に送ります。スレーブ 1、アドレス 0、10 レジスタの要求は `01 03 00 00 00 0A C5 CD` です（CRC は `16#CDC5`）。
- 応答は、最後の 2 バイトを除いたバイトの CRC が、最後の 2 バイト（下位、上位の順）と一致すれば正しいとみなします。

## XML の生成

リポジトリのルートで、次のコマンドを実行します。

```
$ jiecc ./samples/modbus_crc/modbus_crc.iec -I./src -o ./samples/modbus_crc/modbus_crc.xml -t omron
```

## Sysmac Studio での使い方

1. 生成した `modbus_crc.xml` を、[ ツール | IEC 61131-10 XML | インポート ] で取り込みます。
2. タスク設定で、プログラム `ModbusCrcSample` をプライマリ定周期タスクに割り付けます。
3. ビルドして、シミュレータで実行します。 `request` に送る電文ができます。受信した電文を `response` に、バイト数を `response_length` に入れると、`response_ok` に CRC の確認の結果が出ます。
