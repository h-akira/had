# プロジェクトの開始
## 事前確認
下記を確認してから次にすすむこと:
- 開発環境がLinuxまたはMacOSである
- `awscli`がインストールされている（認証もできている）

## 新規プロジェクトの作成
まず、下記のコマンドを実行して案内に従ってプロジェクトを作成する。
なお、途中でS3バケット名を求められるので、予め作成しておくことを推奨する（バケット名は全世界でユニークである必要がある）。
```
had-admin.py -s
```
これにより生成される階層構造は下記の通り（`HogeProject`の部分は任意）:
```
HogeProject
├── HogeProject -> build/project/python/lib/python3.12/site-packages
├── build
│   ├── external
│   │   └── python
│   │       └── lib
│   │           └── python3.12
│   │               └── site-packages
│   ├── handlers
│   └── project
│       ├── python
│       │   └── lib
│       │       └── python3.12
│       │           └── site-packages
│       │               └── project
│       │                   └── settings.py
│       └── templates
├── latest_version.json
├── pip.sh
├── python.sh
├── settings.json
└── templates -> build/project/templates
```
### 各ファイルの説明
#### `HogeProject`
- シンボリックリンク（`build/project/python/lib/python3.12/site-packages`）
- 開発時に直接操作されるため配置
#### `build/external/python/lib/python3.12/site-packages`
- 外部ライブラリの格納先
- `pip.sh`を用いてインストールするとここに格納される
#### `build/handlers`
- Lambdaのhandlerの格納先
- `had-admin.py -H settings.py`を実行すると各関数が自動で生成、格納される
#### `build/project/python/lib/python3.12/site-packages`
- プロジェクトのライブラリの格納先
- このライブラリがLambdaによる処理の大部分を担う
-   Lambdaに直接書くコードは定形の最低限にして大部分の処理をライブラリで行うのが基本思想
#### `build/project/templates`
- テンプレートの格納先
#### `latest_version.json`
- S3に格納される`project`, `handler`, `external`の最新バージョンを記録するファイル
- `CloudFormation`のYAMLファイルを生成する際に参照される
#### `pip.sh`
- 初回実行時（`python.sh`含む）に仮想環境を構築し、二回目以降はその仮想環境を利用してpipを実行するスクリプト
- `./pip.sh install`のみ通常とは異なり、`pip install -t build/external/python/lib/python3.12/site-packages`が実行される
- `./pip.sh install2`では上記に加えて単に`pip install`も行われる（こうすることで`./pip.sh freeze`に反映される）
#### `python.sh`
- 初回実行時（`pip.sh`含む）に仮想環境を構築し、二回目以降はその仮想環境を利用してpythonを実行するスクリプト
#### `settings.json`
- 構築用の設定ファイル
- `had-admin`の`-s`以外のオプション実行時に引数としてこのファイルを指定する
- 設定ファイルとしては他に`HogeProject/project/settings.py`があるがこちらはプロジェクト用
#### `templates`
- シンボリックリンク（`build/project/templates`）
- 開発時に直接操作されるため配置

## 設定ファイルの編集
