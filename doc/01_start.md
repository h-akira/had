# 新規プロジェクトの作成
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
├── requirements.txt
├── settings.json
└── templates -> build/project/templates
```
