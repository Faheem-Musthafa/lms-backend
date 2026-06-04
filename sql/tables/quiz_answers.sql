-- Generated from the SQLAlchemy models — DO NOT hand-edit.
-- Regenerate: python -m scripts.dump_sql
-- Matches Alembic migrations 0001 (schema) + 0002 (RLS).

CREATE TABLE quiz_answers (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	question_id UUID NOT NULL, 
	text TEXT NOT NULL, 
	is_correct BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_quiz_answers PRIMARY KEY (id), 
	CONSTRAINT fk_quiz_answers_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT fk_quiz_answers_question_id_quiz_questions FOREIGN KEY(question_id) REFERENCES quiz_questions (id) ON DELETE CASCADE
);
