-- Generated from the SQLAlchemy models — DO NOT hand-edit.
-- Regenerate: python -m scripts.dump_sql
-- Matches Alembic migrations 0001 (schema) + 0002 (RLS).

CREATE TABLE document_assets (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	lesson_id UUID NOT NULL, 
	file_url VARCHAR(1000) NOT NULL, 
	file_type VARCHAR(40) NOT NULL, 
	size_bytes INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_document_assets PRIMARY KEY (id), 
	CONSTRAINT fk_document_assets_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT uq_document_assets_lesson_id UNIQUE (lesson_id), 
	CONSTRAINT fk_document_assets_lesson_id_lessons FOREIGN KEY(lesson_id) REFERENCES lessons (id) ON DELETE CASCADE
);
