-- Generated from the SQLAlchemy models — DO NOT hand-edit.
-- Regenerate: python -m scripts.dump_sql
-- Matches Alembic migrations 0001 (schema) + 0002 (RLS).

CREATE TABLE tenant_modules (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	module_id UUID NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	enabled_at TIMESTAMP WITH TIME ZONE, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_tenant_modules PRIMARY KEY (id), 
	CONSTRAINT uq_tenant_modules_tenant_module UNIQUE (tenant_id, module_id), 
	CONSTRAINT fk_tenant_modules_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT fk_tenant_modules_module_id_modules FOREIGN KEY(module_id) REFERENCES modules (id) ON DELETE CASCADE
);
