-- Generated from the SQLAlchemy models — DO NOT hand-edit.
-- Regenerate: python -m scripts.dump_sql
-- Matches Alembic migrations 0001 (schema) + 0002 (RLS).

CREATE TABLE course_modules (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	course_id UUID NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT, 
	order_index INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_course_modules PRIMARY KEY (id), 
	CONSTRAINT fk_course_modules_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT fk_course_modules_course_id_courses FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
);
