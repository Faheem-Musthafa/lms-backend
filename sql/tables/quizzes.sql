-- Generated from the SQLAlchemy models — DO NOT hand-edit.
-- Regenerate: python -m scripts.dump_sql
-- Matches Alembic migrations 0001 (schema) + 0002 (RLS).

CREATE TABLE quizzes (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	assignment_id UUID NOT NULL, 
	time_limit_seconds INTEGER NOT NULL, 
	shuffle_questions BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_quizzes PRIMARY KEY (id), 
	CONSTRAINT fk_quizzes_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT uq_quizzes_assignment_id UNIQUE (assignment_id), 
	CONSTRAINT fk_quizzes_assignment_id_assignments FOREIGN KEY(assignment_id) REFERENCES assignments (id) ON DELETE CASCADE
);
