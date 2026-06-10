# BouyomiUTAU for YMM4

UTAUの単独音を、**ゆっくりMovieMaker4（YMM4）の声質として直接使う**ための音声合成プラグインです。YMM4でセリフを入力すると、プラグインが`oto.ini`とWAVを直接読み込み、生成した音声をタイムラインへ追加します。

- 棒読みちゃんは不要です。
- MoreBOUYOMIPluginも不要です。インストール済みでも競合せず、そのまま併用できます。
- PythonアプリやローカルHTTPサーバーを起動しておく必要もありません。
- 音源データはPCの外へ送信されません。

> [!NOTE]
> 漢字の読み変換には未対応です。YMM4のセリフは`今日は良い天気`ではなく、`きょうはいいてんき`のように、ひらがな・カタカナで入力してください。

## YMM4プラグインのビルドとインストール

現在のYMM4は.NET 10を使用するため、ビルドには**.NET 10 SDK**と、インストール済みのYMM4が必要です。

1. PowerShellを開き、このリポジトリのフォルダーへ移動します。
2. 次のコマンドを、実際のYMM4フォルダーを指定して実行します。

```powershell
powershell -ExecutionPolicy Bypass -File .\ymm4\build-plugin.ps1 -YMM4DirPath "C:\Users\ユーザー名\AppData\Local\YukkuriMovieMaker4\"
```

3. 作成された`ymm4\BouyomiUTAU-YMM4.ymme`をYMM4のウィンドウへドラッグ＆ドロップします。
4. YMM4を再起動します。
5. YMM4の「設定」→「プラグイン」→「プラグイン一覧」に`BouyomiUTAU（UTAU単独音）`が表示されれば完了です。

`.ymme`を使わず開発する場合は、`ymm4/Directory.Build.props.sample`を`ymm4/Directory.Build.props`へコピーし、`YMM4DirPath`を設定してからVisual Studioでビルドできます。

## YMM4内でしゃべらせる

1. YMM4のキャラクター編集画面で、声質に**「BouyomiUTAU / UTAU単独音」**を選びます。
2. 声質パラメーターの**「UTAU音源フォルダー」**へ、`oto.ini`が入った単独音音源フォルダーの絶対パスを入力します。

   ```text
   C:\UTAU\voice\デフォ子
   ```

3. 必要なら「読み上げ速度」と「音のつなぎ」を調整します。
4. キャラクターのセリフとして、ひらがな・カタカナを入力します。
5. 通常のYMM4音声と同じように、音声生成・タイムライン追加・動画出力ができます。

音源フォルダーの設定はキャラクター設定に保存されるため、キャラクターごとに別のUTAU音源を割り当てられます。

## 対応音源

- UTAU単独音形式の`oto.ini`
- UTF-8またはCP932（Shift_JIS）の`oto.ini`
- 16-bit PCM WAV
- ひらがな・カタカナのエイリアス
- `ゃ・ゅ・ょ`などを含む拗音エイリアス

句読点や空白では短い間を入れます。音源内に存在しない文字は読み飛ばします。

## 補助デスクトップアプリ

YMM4を開かずに音源を試聴したい場合のみ、既存のデスクトップアプリも利用できます。YMM4で話すためには起動不要です。

```bat
BouyomiUTAU.bat
```

従来のHTTP APIも`BouyomiUTAU-Server.bat`または`python -m bouyomi_utau --server`で利用できます。MoreBOUYOMIPluginを使った既存環境を残したい場合の補助機能です。

## 開発者向けテスト

Python版合成エンジンの回帰テスト：

```bash
python -m unittest discover -v
```

YMM4プラグインのビルド確認（Windows、.NET 10 SDK、YMM4本体が必要）：

```powershell
powershell -ExecutionPolicy Bypass -File .\ymm4\build-plugin.ps1 -YMM4DirPath "YMM4のフォルダー\"
```
