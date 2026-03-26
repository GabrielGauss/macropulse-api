"""
MacroPulse configuration module.

Loads environment variables with sensible defaults for local development.
Uses pydantic-settings for typed, validated configuration.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Central configuration for the MacroPulse system."""

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── General ──────────────────────────────────────────────────────
    app_name: str = "MacroPulse"
    app_version: str = "0.1.0"
    log_level: str = "INFO"

    # ── Database ─────────────────────────────────────────────────────
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "macropulse"
    db_password: str = "macropulse"
    db_name: str = "macropulse"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def async_database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    # ── FRED API ─────────────────────────────────────────────────────
    fred_api_key: str = ""

    # ── Anthropic API (for AI commentary endpoint) ───────────────────
    anthropic_api_key: str = ""

    # ── Model artifacts ──────────────────────────────────────────────
    model_artifacts_dir: str = str(_PROJECT_ROOT / "models" / "artifacts")
    default_model_version: str = "v1"

    # ── PCA / HMM hyper-parameters ───────────────────────────────────
    pca_n_components: int = 4
    pca_variance_threshold: float = 0.80
    hmm_n_regimes: int = 4
    hmm_n_iter: int = 200
    hmm_covariance_type: str = "full"

    # ── Auth ────────────────────────────────────────────────────────
    api_keys: list[str] = []  # Empty = dev-mode (no auth enforced)
    owner_api_key: str = ""   # Master key — tier="owner", all features, no rate limit

    # ── Paddle Billing ───────────────────────────────────────────────
    paddle_api_key: str = ""                        # Bearer token for Paddle API
    paddle_webhook_secret: str = ""                 # From Paddle dashboard → Notifications
    paddle_environment: str = "sandbox"             # "sandbox" | "production"
    paddle_starter_price_id: str = ""               # pri_... for $49/mo
    paddle_pro_price_id: str = ""                   # pri_... for $199/mo
    # Product IDs (used for webhook event filtering)
    paddle_starter_product_id: str = "pro_01kkhzzr1c1f1fta693c6p6nzv"
    paddle_pro_product_id: str = "pro_01kkj01cx467jt6v4c5g2hakrd"
    # URL Paddle redirects to after successful checkout
    paddle_success_url: str = "https://macropulse.live/welcome"
    paddle_client_token: str = ""  # From Paddle dashboard → Developer Tools → Authentication

    # ── CORS ────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── Rate limiting ────────────────────────────────────────────────
    # Requests per API key per calendar day.  0 = unlimited (internal / Pro tier).
    # Free: 50  |  Starter: 500  |  Pro: 0
    rate_limit_per_day: int = 0  # default off for local dev

    # ── Transactional email (Brevo) ──────────────────────────────────
    brevo_api_key: str = ""          # xkeysib-... from Brevo dashboard
    brevo_sender_email: str = ""     # override sender (default: noreply@macropulse.live)
    pipeline_alert_email: str = ""   # owner email for pipeline failure notifications

    # ── Alerting (operator notifications) ───────────────────────────
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_recipients: list[str] = []
    webhook_url: str = ""  # Slack / Discord / generic webhook (operator alerts)
    discord_webhook_url: str = ""  # Discord channel webhook for daily signal posts

    # ── X (Twitter) ─────────────────────────────────────────────────
    x_api_key: str = ""
    x_api_secret: str = ""
    x_access_token: str = ""
    x_access_token_secret: str = ""

    # ── Scheduler ───────────────────────────────────────────────────
    pipeline_cron_hour: int = 18  # 18:00 UTC (after US market close)
    pipeline_cron_minute: int = 30

    # ── IRL Engine integration ───────────────────────────────────────
    # Ed25519 private key (hex-encoded 32 bytes) used to sign /regime/current
    # responses so the IRL Engine can verify MTA authenticity.
    # Generate with: python -c "from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey; k=Ed25519PrivateKey.generate(); print(k.private_bytes_raw().hex())"
    mta_signing_key_hex: str = ""

    # ── Pipeline quality thresholds ──────────────────────────────────
    # Drift warning: PCA explained-variance change fraction that triggers alert.
    pipeline_drift_variance_warn: float = Field(
        default=0.10, validation_alias="PIPELINE_DRIFT_VARIANCE_WARN"
    )
    # Drift warning: regime persistence ratio above which alert fires (near-absorbing state).
    pipeline_drift_persistence_warn: float = Field(
        default=0.97, validation_alias="PIPELINE_DRIFT_PERSISTENCE_WARN"
    )
    # Drift warning: feature mean-shift z-score above which alert fires.
    pipeline_drift_feature_shift_warn: float = Field(
        default=1.5, validation_alias="PIPELINE_DRIFT_FEATURE_SHIFT_WARN"
    )

    # Signal confidence: max_prob threshold for "HIGH" label.
    signal_confidence_high_threshold: float = Field(
        default=0.70, validation_alias="SIGNAL_CONFIDENCE_HIGH_THRESHOLD"
    )
    # Signal confidence: max_prob threshold for "MODERATE" label (below -> "LOW").
    signal_confidence_moderate_threshold: float = Field(
        default=0.50, validation_alias="SIGNAL_CONFIDENCE_MODERATE_THRESHOLD"
    )
    # Liquidity trend: minimum positive d_liquidity days (out of 20) to label "EXPANDING".
    signal_liquidity_trend_min_pos: int = Field(
        default=12, validation_alias="SIGNAL_LIQUIDITY_TREND_MIN_POS"
    )
    # Liquidity trend: rolling window size in trading days for trend calculation.
    signal_liquidity_trend_window: int = Field(
        default=20, validation_alias="SIGNAL_LIQUIDITY_TREND_WINDOW"
    )

    # Orchestrator: minimum rows for a valid rolling trend computation.
    orchestrator_min_rows: int = Field(
        default=5, validation_alias="ORCHESTRATOR_MIN_ROWS"
    )
    # Orchestrator: risk-off probability above which equity signal is bearish.
    orchestrator_dominant_prob: float = Field(
        default=0.50, validation_alias="ORCHESTRATOR_DOMINANT_PROB"
    )
    # Orchestrator: growth (expansion+recovery) probability above which equity is bullish.
    orchestrator_equity_growth_prob_high: float = Field(
        default=0.60, validation_alias="ORCHESTRATOR_EQUITY_GROWTH_PROB_HIGH"
    )
    # Orchestrator: growth probability below which equity adds bearish pressure.
    orchestrator_equity_growth_prob_low: float = Field(
        default=0.30, validation_alias="ORCHESTRATOR_EQUITY_GROWTH_PROB_LOW"
    )
    # Orchestrator: growth probability slope (per-day) above which trend is bullish.
    orchestrator_equity_growth_trend: float = Field(
        default=0.002, validation_alias="ORCHESTRATOR_EQUITY_GROWTH_TREND"
    )
    # Orchestrator: equity domain signal threshold for bullish/bearish label.
    orchestrator_domain_signal_threshold: float = Field(
        default=25.0, validation_alias="ORCHESTRATOR_DOMAIN_SIGNAL_THRESHOLD"
    )
    # Orchestrator: composite signal threshold for bullish/bearish label.
    orchestrator_composite_signal_threshold: float = Field(
        default=20.0, validation_alias="ORCHESTRATOR_COMPOSITE_SIGNAL_THRESHOLD"
    )
    # Orchestrator: yield curve slope above which rates are bullish.
    orchestrator_rates_curve_slope: float = Field(
        default=0.0005, validation_alias="ORCHESTRATOR_RATES_CURVE_SLOPE"
    )
    # Orchestrator: 10Y yield slope below which rates are bullish (falling rates).
    orchestrator_rates_10y_fall: float = Field(
        default=0.001, validation_alias="ORCHESTRATOR_RATES_10Y_FALL"
    )
    # Orchestrator: 10Y yield slope above which rates are bearish (sharply rising).
    orchestrator_rates_10y_rise_sharp: float = Field(
        default=0.002, validation_alias="ORCHESTRATOR_RATES_10Y_RISE_SHARP"
    )
    # Orchestrator: credit HY-spread slope above which credit is bearish (widening).
    orchestrator_credit_slope_strong: float = Field(
        default=0.1, validation_alias="ORCHESTRATOR_CREDIT_SLOPE_STRONG"
    )
    # Orchestrator: net credit score threshold for bullish/bearish label.
    orchestrator_credit_net_threshold: float = Field(
        default=0.2, validation_alias="ORCHESTRATOR_CREDIT_NET_THRESHOLD"
    )
    # Orchestrator: liquidity slope above which liquidity is strongly expanding.
    orchestrator_liquidity_slope_strong: float = Field(
        default=0.5, validation_alias="ORCHESTRATOR_LIQUIDITY_SLOPE_STRONG"
    )
    # Orchestrator: liquidity slope above which liquidity is mildly expanding.
    orchestrator_liquidity_slope_mild: float = Field(
        default=0.1, validation_alias="ORCHESTRATOR_LIQUIDITY_SLOPE_MILD"
    )
    # Orchestrator: conviction std deviation below which label is "strong" (tight agreement).
    orchestrator_conviction_high_std: float = Field(
        default=20.0, validation_alias="ORCHESTRATOR_CONVICTION_HIGH_STD"
    )
    # Orchestrator: conviction std deviation above which label is "weak" (wide disagreement).
    orchestrator_conviction_medium_std: float = Field(
        default=45.0, validation_alias="ORCHESTRATOR_CONVICTION_MEDIUM_STD"
    )

    # GARCH vol state bounds (z-score relative to long-run vol).
    # Below garch_vol_low: "low"; between low-normal: "normal";
    # between normal-elevated: "elevated"; above elevated: "crisis".
    garch_vol_low: float = Field(
        default=0.5, validation_alias="GARCH_VOL_LOW"
    )
    garch_vol_normal: float = Field(
        default=1.5, validation_alias="GARCH_VOL_NORMAL"
    )
    garch_vol_elevated: float = Field(
        default=2.5, validation_alias="GARCH_VOL_ELEVATED"
    )

    # VIX daily change thresholds for volatility state classification.
    # Above vix_diff_elevated: "elevated"; below vix_diff_compressed: "compressed".
    vix_diff_elevated: float = Field(
        default=2.0, validation_alias="VIX_DIFF_ELEVATED"
    )
    vix_diff_compressed: float = Field(
        default=-2.0, validation_alias="VIX_DIFF_COMPRESSED"
    )

    # ── Pipeline ─────────────────────────────────────────────────────
    data_lookback_days: int = 756  # ~3 years of trading days
    fred_series: list[str] = [
        "WALCL",       # Fed Total Assets
        "RRPONTSYD",   # Reverse Repo
        "WTREGEN",     # Treasury General Account
        "DGS10",       # 10-Year Treasury Yield
        "DGS2",        # 2-Year Treasury Yield
        "BAMLH0A0HYM2",  # HY OAS Spread
    ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton of application settings.

    # Tests that set env vars must call get_settings.cache_clear() before get_settings().
    """
    return Settings()
