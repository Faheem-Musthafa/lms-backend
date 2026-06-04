-- Generated from the SQLAlchemy models — DO NOT hand-edit.
-- Regenerate: python -m scripts.dump_sql
-- Matches Alembic migrations 0001 (schema) + 0002 (RLS).

CREATE TABLE lessons (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	course_id UUID NOT NULL, 
	module_id UUID, 
	title VARCHAR(200) NOT NULL, 
	content_type lesson_type NOT NULL, 
	content TEXT, 
	order_index INTEGER NOT NULL, 
	duration_seconds INTEGER NOT NULL, 
	is_preview BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_lessons PRIMARY KEY (id), 
	CONSTRAINT fk_lessons_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT fk_lessons_course_id_courses FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE, 
	CONSTRAINT fk_lessons_module_id_course_modules FOREIGN KEY(module_id) REFERENCES course_modules (id) ON DELETE SET NULL
);
