-- Generated from the SQLAlchemy models — DO NOT hand-edit.
-- Regenerate: python -m scripts.dump_sql
-- Matches Alembic migrations 0001 (schema) + 0002 (RLS).

CREATE TABLE grades (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	submission_id UUID NOT NULL, 
	assignment_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	points NUMERIC(6, 2) NOT NULL, 
	max_points NUMERIC(6, 2) NOT NULL, 
	feedback TEXT, 
	is_auto BOOLEAN NOT NULL, 
	graded_by UUID, 
	graded_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_grades PRIMARY KEY (id), 
	CONSTRAINT fk_grades_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT uq_grades_submission_id UNIQUE (submission_id), 
	CONSTRAINT fk_grades_submission_id_submissions FOREIGN KEY(submission_id) REFERENCES submissions (id) ON DELETE CASCADE, 
	CONSTRAINT fk_grades_assignment_id_assignments FOREIGN KEY(assignment_id) REFERENCES assignments (id) ON DELETE CASCADE
);
