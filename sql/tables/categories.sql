-- Generated from the SQLAlchemy models — DO NOT hand-edit.
-- Regenerate: python -m scripts.dump_sql
-- Matches Alembic migrations 0001 (schema) + 0002 (RLS).

CREATE TABLE categories (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	slug VARCHAR(140) NOT NULL, 
	description TEXT, 
	parent_id UUID, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_categories PRIMARY KEY (id), 
	CONSTRAINT uq_categories_tenant_slug UNIQUE (tenant_id, slug), 
	CONSTRAINT fk_categories_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT fk_categories_parent_id_categories FOREIGN KEY(parent_id) REFERENCES categories (id) ON DELETE SET NULL
);
