-- Generated from the SQLAlchemy models — DO NOT hand-edit.
-- Regenerate: python -m scripts.dump_sql
-- Matches Alembic migrations 0001 (schema) + 0002 (RLS).

CREATE TABLE roles (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	code VARCHAR(50) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	description VARCHAR(255), 
	is_system BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_roles PRIMARY KEY (id), 
	CONSTRAINT uq_roles_tenant_code UNIQUE (tenant_id, code), 
	CONSTRAINT fk_roles_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
);
