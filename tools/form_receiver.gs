/**
 * UchUchU 問い合わせフォーム 受信プログラム（Google Apps Script）
 *
 * サイトのフォームから送信された内容を受け取り、
 *   1. スプレッドシートに1行追加して保存
 *   2. 指定アドレスへメール通知
 * する。第三者サービスを経由せず、すべて自社のGoogleアカウント内で完結する。
 * 費用は無料、件数の上限もない。
 *
 * ───────────────────────────────────────────
 * 設置手順（5分）
 *
 *  1. https://script.google.com/ を開き「新しいプロジェクト」を作成
 *  2. このファイルの中身をすべて貼り付ける
 *  3. 上部の「デプロイ」→「新しいデプロイ」を選ぶ
 *  4. 歯車アイコン →「ウェブアプリ」を選択
 *  5. 設定:
 *        説明          : UchUchU 問い合わせ受信
 *        次のユーザーとして実行 : 自分
 *        アクセスできるユーザー : 全員          ← ここが重要
 *  6. 「デプロイ」を押す（初回は権限の承認を求められる）
 *  7. 表示される「ウェブアプリのURL」をコピーしてClaudeに渡す
 *        https://script.google.com/macros/s/XXXXXXXX/exec
 *
 *  ※ コードを修正したときは「デプロイ」→「デプロイを管理」→ 鉛筆アイコン →
 *     バージョンを「新バージョン」にして再デプロイすること。URLは変わらない。
 * ───────────────────────────────────────────
 */

// 通知先メールアドレス。変更する場合はここだけ直す。
var NOTIFY_EMAIL = 'joe@gtoe.info';

// 保存先スプレッドシート名（初回実行時に自動作成される）
var SHEET_NAME = 'UchUchU 問い合わせ';

// 受け取る項目と表示名。サイト側のフォームと対応している。
var FIELDS = [
  ['kind', 'ご用件'],
  ['company', '貴社名'],
  ['name', 'ご担当者名'],
  ['email', 'メールアドレス'],
  ['tel', '電話番号'],
  ['site', '貴社サイトURL'],
  ['message', 'ご相談内容']
];

/** フォームからのPOSTを受け取る */
function doPost(e) {
  try {
    var data = parseRequest_(e);

    // 簡易スパム対策: 空送信と、hp（ハニーポット）が埋まっている送信を弾く
    if (!data.message && !data.company) {
      return json_({ success: false, message: 'empty' });
    }
    if (data.hp) {
      // ボットだけが埋める隠しフィールド。成功を装って捨てる
      return json_({ success: true });
    }

    saveToSheet_(data);
    sendNotification_(data);
    return json_({ success: true });
  } catch (err) {
    // 失敗しても内容は失いたくないので、管理者に生データを送る
    try {
      MailApp.sendEmail({
        to: NOTIFY_EMAIL,
        subject: '[UchUchU] フォーム受信でエラーが発生しました',
        body: 'エラー: ' + err + '\n\n生データ:\n' + (e && e.postData ? e.postData.contents : '(なし)')
      });
    } catch (e2) {}
    return json_({ success: false, message: String(err) });
  }
}

/** 動作確認用。ブラウザでURLを開くと表示される */
function doGet() {
  return ContentService
    .createTextOutput('UchUchU form receiver is running.')
    .setMimeType(ContentService.MimeType.TEXT);
}

/** JSON / フォーム形式のどちらでも受け取れるようにする */
function parseRequest_(e) {
  if (e && e.postData && e.postData.contents) {
    try {
      return JSON.parse(e.postData.contents);
    } catch (err) {
      // JSONでなければフォームパラメータとして扱う
    }
  }
  return (e && e.parameter) ? e.parameter : {};
}

/** スプレッドシートに1行追加する */
function saveToSheet_(data) {
  var props = PropertiesService.getScriptProperties();
  var id = props.getProperty('SHEET_ID');
  var ss;

  if (id) {
    try { ss = SpreadsheetApp.openById(id); } catch (err) { ss = null; }
  }
  if (!ss) {
    ss = SpreadsheetApp.create(SHEET_NAME);
    props.setProperty('SHEET_ID', ss.getId());
    var head = ['受信日時'];
    for (var i = 0; i < FIELDS.length; i++) head.push(FIELDS[i][1]);
    ss.getActiveSheet().appendRow(head);
    ss.getActiveSheet().setFrozenRows(1);
  }

  var row = [new Date()];
  for (var j = 0; j < FIELDS.length; j++) {
    row.push(data[FIELDS[j][0]] || '');
  }
  ss.getActiveSheet().appendRow(row);
}

/** 通知メールを送る */
function sendNotification_(data) {
  var lines = [];
  for (var i = 0; i < FIELDS.length; i++) {
    var v = data[FIELDS[i][0]];
    if (v) lines.push(FIELDS[i][1] + '：' + v);
  }

  var props = PropertiesService.getScriptProperties();
  var sheetId = props.getProperty('SHEET_ID');
  var sheetUrl = sheetId ? '\n\n一覧: https://docs.google.com/spreadsheets/d/' + sheetId : '';

  MailApp.sendEmail({
    to: NOTIFY_EMAIL,
    replyTo: data.email || NOTIFY_EMAIL,   // 返信すれば相手に直接届く
    subject: '[UchUchU] ' + (data.kind || 'お問い合わせ') + '（' + (data.company || '') + '）',
    body: lines.join('\n') + sheetUrl + '\n\n――――――――――\nUchUchU 問い合わせフォームより'
  });
}

function json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
