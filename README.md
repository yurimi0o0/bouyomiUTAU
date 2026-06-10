# BouyomiUTAU Studio

無料ソフト「棒読みちゃん」と組み合わせて使える、UTAU単独音向けのローカル音声合成APIです。`oto.ini` を読み込み、入力されたひらがな・カタカナに対応するWAVをクロスフェードで連結します。

## 起動

Python 3.10以上だけで動作し、追加パッケージは不要です。

```bash
python -m bouyomi_utau
```

ブラウザーで `http://127.0.0.1:50100` が開きます。画面でUTAU音源フォルダーを指定し、ひらがなを入力してください。

## 棒読みちゃん・配信ツールから使う

起動中は次のHTTP APIが利用できます。URLを呼び出せる棒読みちゃんプラグイン、配信ツール、ショートカットなどから利用してください。

```text
GET http://127.0.0.1:50100/api/talk?voicebank=C%3A%5CUTAU%5Cvoice%5Csample&text=こんにちは&speed=1.0
```

レスポンスはモノラル16-bit WAVです。`X-Missing-Aliases` ヘッダーには、音源内に見つからなかった音が入ります。

> [!NOTE]
> UTAU単独音は歌唱用の短い録音です。自然なTTSほど滑らかにはなりません。漢字の読み変換には未対応のため、ひらがな・カタカナで入力してください。

## テスト

```bash
python -m unittest discover -v
```
