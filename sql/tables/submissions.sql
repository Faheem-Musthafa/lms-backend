-- Generated from the SQLAlchemy models — DO NOT hand-edit.
-- Regenerate: python -m scripts.dump_sql
-- Matches Alembic migrations 0001 (schema) + 0002 (RLS).

CREATE TABLE submissions (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	assignment_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	content TEXT, 
	file_url VARCHAR(1000), 
	answers JSONB, 
	status submission_status NOT NULL, 
	submitted_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_submissions PRIMARY KEY (id), 
	CONSTRAINT fk_submissions_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT fk_submissions_assignment_id_assignments FOREIGN KEY(assignment_id) REFERENCES assignments (id) ON DELETE CASCADE, 
	CONSTRAINT fk_submissions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
