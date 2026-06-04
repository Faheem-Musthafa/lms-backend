-- Generated from the SQLAlchemy models — DO NOT hand-edit.
-- Regenerate: python -m scripts.dump_sql
-- Matches Alembic migrations 0001 (schema) + 0002 (RLS).

CREATE TABLE lesson_progress (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	lesson_id UUID NOT NULL, 
	course_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	status progress_status NOT NULL, 
	last_position_seconds INTEGER NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_lesson_progress PRIMARY KEY (id), 
	CONSTRAINT uq_lesson_progress_lesson_user UNIQUE (lesson_id, user_id), 
	CONSTRAINT fk_lesson_progress_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT fk_lesson_progress_lesson_id_lessons FOREIGN KEY(lesson_id) REFERENCES lessons (id) ON DELETE CASCADE, 
	CONSTRAINT fk_lesson_progress_course_id_courses FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE, 
	CONSTRAINT fk_lesson_progress_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
