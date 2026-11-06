# ハッシュマップ（文字列のキーから dint の値）

通過した部品の数を、部品の名前ごとに数えます。`container/hashmap` のテンプレートの具体化の仕方を示します。

- マクロ `HashMapName` に付けた名前（`PartCount`）が、作られる型と関数の名前に入ります（型 `HashMap_PartCount_t`、関数 `HashMap_PartCount_init`・`HashMap_PartCount_upsert`・`HashMap_PartCount_lookup` など）。
- `HashMapCapacity` はスロットの数です。キーの数がその 80%（`HashMapMaxLoadPermille`。既定 800）を超えると、`upsert` が失敗します。
- 文字列のキーには、最大の長さを付けた型（`string[32 + 1]`）と、比較とハッシュの関数（`string_lib/equivalence.iec` の `String_equals`・`String_hash`）を指定します。
- 具体化の後は、マクロを `{#undef}` で消します。別の値で、もう 1 つのマップを作れるようにするためです。
- 使う前に、1 回だけ `HashMap_PartCount_init` を呼びます。
- `map_full` は、一度真になると、再起動まで真のままです。

## XML の生成

リポジトリのルートで、次のコマンドを実行します。

```
$ jiecc ./samples/hashmap_string_to_dint/hashmap_string_to_dint.iec -I./src -o ./samples/hashmap_string_to_dint/hashmap_string_to_dint.xml -t omron
```

## Sysmac Studio での使い方

1. 生成した `hashmap_string_to_dint.xml` を、[ ツール | IEC 61131-10 XML | インポート ] で取り込みます。
2. タスク設定で、プログラム `HashMapSample` をプライマリ定周期タスクに割り付けます。
3. ビルドして、シミュレータで実行します。 変数 `part_name` に部品の名前を入れ、`passed` を 1 周期だけ真にすると、数が増えます。`shown_name` に名前を入れると、`shown_count` にその数が出ます。
