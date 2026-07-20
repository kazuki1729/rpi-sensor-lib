# Changelog

このプロジェクトは[Semantic Versioning](https://semver.org/)に従います。

## [0.2.0] - 2026-07-21

### Added

- MH-Z19CのUART応答チェックサム検証と専用例外
- 全MCP3208クラスで共有するバス／デバイス単位のSPIリソース管理
- 公開APIの型注釈と引数検証
- 全センサークラスのハードウェア非依存テスト
- センサー種別ごとのoptional dependency
- `CONTRIBUTING.md`、`SECURITY.md`、リリース整合性検査

### Changed

- `close()`を複数回呼んでも安全な冪等操作へ変更
- キャッシュとチャタリング計測を`time.monotonic()`へ変更
- BME280のバス接続を含む初期化失敗を、次回`read()`で再試行
- `RPI_SENSOR_BACKEND`の不正値を設定エラーとして拒否
- Python 3.10を含むCIマトリクスと型・配布物検査を追加
- バージョン番号を`rpi_sensors/_version.py`へ一元化

### Breaking

- MH-Z19Cは失敗時の`None`ではなく`MHZ19CError`派生例外を送出
- MCP3208の不正チャンネルは`-1`ではなく`ValueError`を送出
- 直接ハードウェア依存は`pip install "rpi-sensor-lib[direct]"`で導入

## [0.1.2] - 2026-07-15

- BME280の一時的なキャリブレーション読込失敗からの自動復旧を追加
- direct／pi4gpioデュアルバックエンドを全センサーへ展開
- DHT22の終端エッジ欠落復元と合成波形テストを追加

## [0.1.1] - 2026-07-12

- PyPI Trusted Publishingによるタグ公開ワークフローを追加

## [0.1.0] - 2026-06-15

- BME280、DHT22、MH-Z19C、MCP3208、タクタイルボタンの初回公開

[0.2.0]: https://github.com/kazuki1729/rpi-sensor-lib/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/kazuki1729/rpi-sensor-lib/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/kazuki1729/rpi-sensor-lib/compare/506b36c...v0.1.1
[0.1.0]: https://pypi.org/project/rpi-sensor-lib/0.1.0/
