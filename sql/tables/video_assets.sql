-- Generated from the SQLAlchemy models — DO NOT hand-edit.
-- Regenerate: python -m scripts.dump_sql
-- Matches Alembic migrations 0001 (schema) + 0002 (RLS).

CREATE TABLE video_assets (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	lesson_id UUID NOT NULL, 
	provider VARCHAR(40) NOT NULL, 
	url VARCHAR(1000) NOT NULL, 
	hls_url VARCHAR(1000), 
	duration_seconds INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_video_assets PRIMARY KEY (id), 
	CONSTRAINT fk_video_assets_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT uq_video_assets_lesson_id UNIQUE (lesson_id), 
	CONSTRAINT fk_video_assets_lesson_id_lessons FOREIGN KEY(lesson_id) REFERENCES lessons (id) ON DELETE CASCADE
);
