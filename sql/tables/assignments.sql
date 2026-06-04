-- Generated from the SQLAlchemy models — DO NOT hand-edit.
-- Regenerate: python -m scripts.dump_sql
-- Matches Alembic migrations 0001 (schema) + 0002 (RLS).

CREATE TABLE assignments (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	course_id UUID NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT, 
	type assignment_type NOT NULL, 
	max_points NUMERIC(6, 2) NOT NULL, 
	pass_points NUMERIC(6, 2) NOT NULL, 
	due_at TIMESTAMP WITH TIME ZONE, 
	is_published BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_assignments PRIMARY KEY (id), 
	CONSTRAINT fk_assignments_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT fk_assignments_course_id_courses FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
);
