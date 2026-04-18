# StageCrew ロードマップ（タスク表）

上から順に進める。各タスクの `[ ]` を `[x]` に変えて進捗管理する。

---

## データ所有権モデル

どの情報が団体/公演に属し、どの情報がユーザー個人に属するかの整理。

### 団体/公演所有（Organization → Production）

```
Organization（団体）
 └── Production（公演）
      ├── Department（部門）
      │    ├── StaffRole（役職定義）
      │    ├── DepartmentMembership（部門所属）
      │    └── StatusDefinition（カスタムステータス）
      ├── ProductionPhase（公演フェーズ: 企画→稽古→本番等）
      ├── Milestone（マイルストーン）
      ├── Label（ラベル）
      ├── Issue（課題/タスク）
      │    ├── IssueAssignee → User
      │    ├── IssueLabel → Label
      │    ├── IssueDependency
      │    └── Comment → User
      ├── Event（イベント/稽古）  ← Phase 2.5
      │    ├── EventAttendee → User（招集・出欠）
      │    └── EventScene → Scene（稽古対象シーン）
      └── Script（脚本）  ← Phase 2
           ├── Scene（シーン）
           ├── Character（登場人物）
           │    └── Casting（配役） → ProductionMembership
           ├── Line（セリフ）
           └── SceneChart（香盤表）
```

### ユーザー所有（User）

```
User（ユーザー）
 ├── OrganizationMembership → Organization（団体所属）
 ├── ProductionMembership → Production（公演参加）
 │    ├── is_cast（キャストフラグ）
 │    ├── cast_capabilities（キャスト権限）
 │    └── DepartmentMembership → Department（部門所属）
 ├── UserAvailability（個人の空き状況、公演スコープ）  ← Phase 2.5
 └── EventAttendee 経由で RSVP 回答（中間テーブル）  ← Phase 2.5
```

---

## Phase 1: MVP基盤

> 認証・組織管理・課題管理の基本機能。

- [x] Discord OAuth ログイン
- [x] 団体（Organization）CRUD
- [x] 団体メンバー管理・招待
- [x] 公演（Production）CRUD
- [x] 公演メンバー管理
- [x] 部門（Department）CRUD・ロール定義
- [x] 部門メンバー管理（ケイパビリティ付き）
- [x] カスタムステータス定義
- [x] 課題（Issue）CRUD・フィルタ・親子関係・担当割当・コメント・ラベル
- [x] カンバンボード（部門別 + 全体ビュー、ドラッグ&ドロップ）
- [x] ガントチャート（タイムライン表示、依存関係、マイルストーン）
- [x] 本番カウントダウン（初日までの日数表示）
- [x] Discord Webhook 通知（タスク作成/更新/完了、コメント追加、期限リマインダー）
- [x] ダッシュボード（公演進捗サマリー、担当タスク一覧、期限警告）

---

## Phase 2: 脚本管理

> 脚本のアップロードから配役・香盤表・PDF出力・通知までを一気通貫で扱う。

### 2-1. データモデル・基本CRUD
- [x] Script モデル（title, author, revision, draft_date, copyright, contact, notes 等）
- [x] Scene モデル（act_number, scene_number, heading, description）
- [x] Character モデル（name, description, order）
- [x] Line モデル（content, order, character_id, scene_id）
- [x] 脚本の一覧取得・詳細取得 API
- [x] 脚本の削除 API

### 2-2. アップロード・パース
- [x] ファイルアップロード API（テキスト / Fountain）※ PDF/Word は Discord 管理
- [x] Fountain 形式パーサー（メタデータ抽出、シーン・登場人物・セリフの自動解析）
- [x] マルチエンコーディング対応（UTF-8, Shift_JIS 等）
- [x] Fountain 以外のフォーマット：手動でシーン・登場人物を登録する API

### 2-3. キャスティング（配役）
- [x] 登場人物へのキャスト割当 API（ダブルキャスト対応）
- [x] 表示名・キャストメモの管理
- [x] 脚本更新時のキャスティング情報保持

### 2-4. 香盤表（Scene Chart）
- [x] 香盤表データモデル（SceneChart / SceneCharacterMapping）
- [x] Fountain パース時の香盤表自動生成
- [x] 手動編集 API（シーン×登場人物マッピングの追加・削除）
- [x] 香盤表の表示 UI  ← 2-8 と統合

### 2-5. PDF出力
- [x] 脚本 PDF 生成（縦書き/横書き対応）
- [x] 日本語フォント対応
- [x] メタデータ付きレイアウト（著者、日付、改訂番号、連絡先）
- [x] PDF ダウンロード API

### 2-6. バージョン管理
- [x] 改訂番号（revision）管理
- [x] 改訂テキスト（revision_text）メモ
- [x] 更新時のデータ再構築（シーン・セリフ・マッピング）とキャスティング保持

### 2-7. Discord 通知連携
- [x] 脚本アップロード/更新時の Webhook 通知
- [x] 通知に改訂番号・公演名・脚本タイトルを含む
- [x] 生成 PDF の添付

### 2-8. フロントエンド
- [x] 脚本一覧ページ
- [x] 脚本詳細ページ（シーン・登場人物・セリフ表示）
- [x] 脚本アップロード UI
- [x] キャスティング UI
- [x] 香盤表ビュー
- [ ] PDF ダウンロードボタン

---

## Phase 2.5: スケジュール・カレンダー管理

> キャスト・スタッフ双方の視点でスケジュールを管理する。
> 香盤表連携（2.5-5）以外は Phase 2 と独立して実装可能。

### 2.5-1. データモデル・基本CRUD
- [ ] `Event` モデル（event_type, title, description, start_at, end_at, location_name, location_url, is_all_day, production_id, created_by）
- [ ] `EventAttendee` モデル（event_id, user_id, attendance_type, rsvp_status, actual_attendance, responded_at）
- [ ] `EventScene` モデル（event_id, scene_id）← 香盤表連携用
- [ ] `UserAvailability` モデル（user_id, production_id, date, availability, start_time, end_time, note）
- [ ] Event CRUD API（作成・取得・更新・削除、日付範囲フィルタ）
- [ ] EventAttendee API（招集メンバー追加・削除・RSVP回答）
- [ ] UserAvailability API（個人の空き登録・取得・更新）

### 2.5-2. カレンダービュー
- [ ] 月間カレンダー表示（公演イベント一覧）
- [ ] 週間カレンダー表示（時間帯付き詳細ビュー）
- [ ] イベント詳細モーダル（参加者一覧、出欠状況、対象シーン）
- [ ] イベント作成・編集 UI
- [ ] 日付セルクリックでクイック作成

### 2.5-3. 出欠・RSVP管理
- [ ] 招集メンバーの一括追加（部門全員、キャスト全員、個別選択）
- [ ] RSVP 回答 UI（参加・不参加・未定）
- [ ] 出欠状況一覧表示（マトリクス: イベント × メンバー）
- [ ] 実績入力（当日の実際の出欠記録）

### 2.5-4. ユーザー空き状況管理
- [ ] カレンダー形式の空き登録 UI（日単位、時間帯指定可）
- [ ] 空き状況一覧ビュー（マネージャー向け: メンバー × 日付マトリクス）
- [ ] 稽古日程設定時に空き状況をオーバーレイ表示

### 2.5-5. 香盤表連携・スマート招集（Phase 2-4 完了後）
- [ ] イベントにシーンを紐付け → 香盤表から必要キャストを自動提案
- [ ] 「このシーンに出演するキャスト」の自動招集ボタン
- [ ] ダブルキャスト対応（どちらのキャストが参加するか選択）
- [ ] 招集対象にスタッフ（演出、舞台監督等）も追加可能

### 2.5-6. パーソナルスケジュール・外部カレンダー連携
- [ ] 全公演横断の「マイスケジュール」ビュー（自分が招集されているイベント一覧）
- [ ] Google Calendar API 連携（公演の代表者が Google カレンダーを接続 → イベント自動同期 → 共有カレンダーとして関係者全員に公開）
- [ ] iCal フィード URL 生成（Google 以外のカレンダーアプリ向け購読 URL、読み取り専用・自動更新）

### 2.5-7. ダッシュボード統合
- [ ] ダッシュボードに「直近のスケジュール」セクション追加
- [ ] 今日・明日・今週のイベント表示
- [ ] 未回答の RSVP アラート

### 2.5-8. Discord 通知連携
- [ ] イベント作成/更新/削除時の Webhook 通知
- [ ] 稽古前日リマインダー（既存の deadline_reminder パターンを流用）
- [ ] 招集通知（新しくイベントに招集された時）
- [ ] RSVP 催促通知

---

## Phase 3: タスク管理拡張

> WBS・テンプレート・依存関係の可視化で課題管理を強化。

- [ ] WBS ツリービュー（課題の階層表示、進捗率自動集計）
- [ ] タスクテンプレート（フェーズ × 部門マトリクス、団体独自テンプレート保存）
- [ ] 依存関係の可視化（ガントチャート上の依存線、ブロック警告）

---

## Phase 4: 運営管理

> 予算・会場など公演運営に必要な管理機能。

- [ ] 予算・経費管理（予算枠設定、部門別配分、経費登録・承認、消化率表示）
- [ ] 会場マスタ管理（会場情報登録 → Event の location 参照先として正規化）

---

## Phase 5: VR演劇対応

> VR演劇特有のワークフロー・アセット管理。

- [ ] VR プラットフォーム管理（VRChat / cluster / Resonite）
- [ ] 3D アセット管理（進捗ステータス、担当者割当）
- [ ] ライセンス規約チェック（ライセンス種別記録、商用利用可否、警告表示）
- [ ] クレジット一覧自動生成

---

## Phase 6: プラットフォーム拡張

> 認証手段追加・セルフホスト・課金。

- [ ] メール認証（Discord 以外の認証手段）
- [ ] セルフホスト用 Docker 対応
- [ ] 課金機能（フリーミアムプラン）

---

## Phase 7: 公開・共有

> 脚本の公開配信・インポート機能。

- [ ] 脚本の公開/非公開切り替え
- [ ] 公開脚本の一覧表示（ページネーション）
- [ ] 公開脚本のインポート（他公演への取り込み）
- [ ] 公開利用条件・連絡先の設定
