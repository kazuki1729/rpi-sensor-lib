# Contributing

IssueまたはPull Requestでは、対象センサー、バックエンド、Raspberry Piの
モデル、OS、Pythonバージョン、配線、再現手順を記載してください。

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m unittest discover -s tests -v
```

ハードウェアを使う変更には、可能であれば実機結果も添えてください。
認証情報、実IPアドレス、個人データをコミットしないでください。
