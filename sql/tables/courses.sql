-- Generated from the SQLAlchemy models — DO NOT hand-edit.
-- Regenerate: python -m scripts.dump_sql
-- Matches Alembic migrations 0001 (schema) + 0002 (RLS).

CREATE TABLE courses (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	slug VARCHAR(220) NOT NULL, 
	summary VARCHAR(500), 
	description TEXT, 
	category_id UUID, 
	status course_status NOT NULL, 
	level course_level NOT NULL, 
	is_free BOOLEAN NOT NULL, 
	price NUMERIC(10, 2) NOT NULL, 
	thumbnail_url VARCHAR(500), 
	enrollment_count INTEGER NOT NULL, 
	published_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_courses PRIMARY KEY (id), 
	CONSTRAINT uq_courses_tenant_slug UNIQUE (tenant_id, slug), 
	CONSTRAINT fk_courses_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT fk_courses_category_id_categories FOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE SET NULL
);
