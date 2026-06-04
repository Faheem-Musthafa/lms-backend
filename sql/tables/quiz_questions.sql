-- Generated from the SQLAlchemy models — DO NOT hand-edit.
-- Regenerate: python -m scripts.dump_sql
-- Matches Alembic migrations 0001 (schema) + 0002 (RLS).

CREATE TABLE quiz_questions (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	quiz_id UUID NOT NULL, 
	text TEXT NOT NULL, 
	type question_type NOT NULL, 
	points NUMERIC(6, 2) NOT NULL, 
	order_index INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_quiz_questions PRIMARY KEY (id), 
	CONSTRAINT fk_quiz_questions_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT fk_quiz_questions_quiz_id_quizzes FOREIGN KEY(quiz_id) REFERENCES quizzes (id) ON DELETE CASCADE
);
