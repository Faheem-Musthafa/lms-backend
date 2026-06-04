-- Generated from the SQLAlchemy models — DO NOT hand-edit.
-- Regenerate: python -m scripts.dump_sql
-- Matches Alembic migrations 0001 (schema) + 0002 (RLS).

CREATE TABLE course_instructors (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	course_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	is_lead BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_course_instructors PRIMARY KEY (id), 
	CONSTRAINT uq_course_instructors_course_user UNIQUE (course_id, user_id), 
	CONSTRAINT fk_course_instructors_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT fk_course_instructors_course_id_courses FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE, 
	CONSTRAINT fk_course_instructors_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
