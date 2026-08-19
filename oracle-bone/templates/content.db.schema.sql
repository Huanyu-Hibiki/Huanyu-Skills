-- oracle-bone content.db schema (SQLite 升级位)
-- 当 calibration_samples_total >= 30 且 data_layer=markdown 时，md-to-sqlite 升级用。
-- 字段与 candidates / predictions 的 markdown 格式一一对应（candidate-schema.md / prediction-anatomy.md）。

PRAGMA journal_mode = WAL;

-- 候选池（candidates.md → articles）
CREATE TABLE IF NOT EXISTS articles (
  id            TEXT PRIMARY KEY,          -- 12 位稳定 hash
  title         TEXT NOT NULL,
  source        TEXT NOT NULL,             -- trend:hackernews / pool:... / paste:manual / seed
  snapshot_text TEXT,
  snapshot_at   TEXT NOT NULL,             -- ISO 8601
  url           TEXT,
  tier          TEXT,                      -- tier1/2/3/skip/risky/done
  track         TEXT,                      -- 轨道 id 或 cross:t1+t2，NULL=未分流
  read_status   TEXT,                      -- unread/skimmed/deep_read/done
  category      TEXT,
  composite_score REAL,
  dimension_scores TEXT,                   -- JSON object
  scored_under_rubric_version TEXT,
  predicted_bucket TEXT,
  predicted_reason TEXT,
  note          TEXT,
  rejected_at   TEXT,
  rejected_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_articles_track  ON articles(track);
CREATE INDEX IF NOT EXISTS idx_articles_tier   ON articles(tier);
CREATE INDEX IF NOT EXISTS idx_articles_score  ON articles(composite_score DESC);

-- 预测日志（<NNN>_*/predictions/*.md → predictions）
CREATE TABLE IF NOT EXISTS predictions (
  id            TEXT PRIMARY KEY,          -- Article ID（candidate id）
  title         TEXT NOT NULL,
  track         TEXT NOT NULL,
  work_folder   TEXT,                      -- <NNN>_<标题>/
  script_path   TEXT,
  script_hash   TEXT,                      -- sha256:12 at predict time
  rubric_version TEXT NOT NULL,
  prediction_basis TEXT NOT NULL,          -- pre_shoot / post_review_pre_publish / post_shoot_pre_publish / post_titlepick
  predicted_at  TEXT NOT NULL,
  bucket        TEXT,
  central       REAL,                      -- 中枢点估计
  confidence_label TEXT,                   -- 🔴..🔵
  scored_by     TEXT,                      -- claude / claude+user_override
  user_override TEXT,
  blind_status  TEXT,                      -- blind / reconstructed
  published_at  TEXT,
  platforms     TEXT                       -- JSON: per-platform url/id/published_at
);
CREATE INDEX IF NOT EXISTS idx_predictions_track ON predictions(track);
CREATE INDEX IF NOT EXISTS idx_predictions_pub   ON predictions(published_at);

-- 复盘实绩（retro 段 → retros；一个 prediction 可有多窗口条目）
CREATE TABLE IF NOT EXISTS retros (
  prediction_id TEXT NOT NULL REFERENCES predictions(id),
  window_days   INTEGER NOT NULL,          -- 3 / 7 / 30
  retro_at      TEXT NOT NULL,
  data_source   TEXT,                      -- manual / adapter:<name>
  metrics       TEXT NOT NULL,             -- JSON: 各 success_metric 实绩（播放/咨询/付费...）
  ratios        TEXT,                      -- JSON: 派生比率
  verified      TEXT,                      -- JSON: 被验证的假设
  refuted       TEXT,                      -- JSON: 被推翻的假设
  observations  TEXT,                      -- JSON: 新观察（同步 rubric_notes）
  calibration_skipped INTEGER DEFAULT 0,   -- 1 = retroactive 不计校准
  PRIMARY KEY (prediction_id, window_days)
);

-- 观察记录（rubric_notes 观察段 → observations_log，供跨样本检索）
CREATE TABLE IF NOT EXISTS observations_log (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  track         TEXT NOT NULL,
  logged_at     TEXT NOT NULL,
  title         TEXT,
  stage         TEXT,                      -- 观察/跨样本/沉淀/待验证
  body          TEXT NOT NULL,
  evidence      TEXT,                      -- JSON: 数据点引用
  status        TEXT DEFAULT 'active'      -- active / absorbed / refuted / promoted
);
CREATE INDEX IF NOT EXISTS idx_obs_track ON observations_log(track, stage);
