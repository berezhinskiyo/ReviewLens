"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255)),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("consent_at", sa.DateTime(timezone=True)),
        sa.Column("consent_version", sa.String(32)),
        sa.Column("plan", sa.String(32), nullable=False, server_default="free"),
        sa.Column("subscription_until", sa.DateTime(timezone=True)),
        sa.Column(
            "analyses_used_this_period", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("email"),
    )
    op.create_index("idx_users_email", "users", ["email"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("idx_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("idx_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])

    op.create_table(
        "email_verification_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "idx_email_verification_codes_email", "email_verification_codes", ["email"]
    )

    op.create_table(
        "oauth_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_user_id", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),
    )
    op.create_index("idx_oauth_identities_user_id", "oauth_identities", ["user_id"])
    op.create_index("idx_oauth_identities_email", "oauth_identities", ["email"])

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("marketplace", sa.String(16), nullable=False),
        sa.Column("external_id", sa.String(64), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("brand", sa.String(255)),
        sa.Column("category", sa.Text()),
        sa.Column("price_kopecks", sa.Integer()),
        sa.Column("rating", sa.Numeric(2, 1)),
        sa.Column("reviews_count", sa.Integer()),
        sa.Column("last_parsed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("marketplace", "external_id"),
    )
    op.create_index(
        "idx_products_marketplace_external_id",
        "products",
        ["marketplace", "external_id"],
    )

    op.create_table(
        "analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id"),
        ),
        sa.Column("input_url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text()),
        sa.Column("reviews_analyzed_count", sa.Integer()),
        sa.Column("llm_cost_kopecks", sa.Integer()),
        sa.Column("result", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_analyses_user_id", "analyses", ["user_id"])
    op.create_index("idx_analyses_status", "analyses", ["status"])

    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(128)),
        sa.Column("rating", sa.SmallInteger()),
        sa.Column("text", sa.Text()),
        sa.Column("pros", sa.Text()),
        sa.Column("cons", sa.Text()),
        sa.Column("review_date", sa.DateTime(timezone=True)),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("product_id", "external_id"),
    )
    op.create_index("idx_reviews_product_id", "reviews", ["product_id"])

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("yookassa_payment_id", sa.String(64)),
        sa.Column("amount_kopecks", sa.Integer(), nullable=False),
        sa.Column("plan", sa.String(32), nullable=False),
        sa.Column("period_months", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("yookassa_payment_id"),
    )


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_index("idx_reviews_product_id", table_name="reviews")
    op.drop_table("reviews")
    op.drop_index("idx_analyses_status", table_name="analyses")
    op.drop_index("idx_analyses_user_id", table_name="analyses")
    op.drop_table("analyses")
    op.drop_index("idx_products_marketplace_external_id", table_name="products")
    op.drop_table("products")
    op.drop_table("oauth_identities")
    op.drop_table("email_verification_codes")
    op.drop_table("refresh_tokens")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_table("users")
