from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    paper_mode: bool = Field(default=True, alias="PAPER_MODE")
    scan_limit: int = Field(default=25, alias="SCAN_LIMIT")
    min_liquidity_usd: float = Field(default=10000, alias="MIN_LIQUIDITY_USD")
    max_spread_pct: float = Field(default=0.05, alias="MAX_SPREAD_PCT")
    min_abs_edge_bps: float = Field(default=150, alias="MIN_ABS_EDGE_BPS")
    min_confidence: float = Field(default=0.60, alias="MIN_CONFIDENCE")
    snapshot_dir: str = Field(default="./data/snapshots", alias="SNAPSHOT_DIR")
    ledger_path: str = Field(default="./data/paper_ledger.jsonl", alias="LEDGER_PATH")
    report_path: str = Field(default="./data/reports/latest_report.json", alias="REPORT_PATH")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    claude_model: str = Field(default="claude-sonnet-4-5", alias="CLAUDE_MODEL")
