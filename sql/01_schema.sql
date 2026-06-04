-- Generated from the SQLAlchemy models — DO NOT hand-edit.
-- Regenerate: python -m scripts.dump_sql
-- Matches Alembic migrations 0001 (schema) + 0002 (RLS).

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE isolation_mode AS ENUM ('shared', 'schema', 'database');

CREATE TYPE assignment_type AS ENUM ('assignment', 'quiz');

CREATE TYPE question_type AS ENUM ('single', 'multiple', 'boolean');

CREATE TYPE submission_status AS ENUM ('submitted', 'graded', 'returned');

CREATE TYPE course_status AS ENUM ('draft', 'published', 'archived');

CREATE TYPE course_level AS ENUM ('beginner', 'intermediate', 'advanced');

CREATE TYPE enrollment_status AS ENUM ('active', 'completed', 'cancelled');

CREATE TYPE lesson_type AS ENUM ('video', 'document', 'text');

CREATE TYPE progress_status AS ENUM ('not_started', 'in_progress', 'completed');

CREATE TABLE modules (
	id UUID NOT NULL, 
	code VARCHAR(40) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	description VARCHAR(255), 
	is_active BOOLEAN NOT NULL, 
	is_core BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_modules PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_modules_code ON modules (code);

CREATE TABLE tenants (
	id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	slug VARCHAR(80) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	isolation_mode isolation_mode NOT NULL, 
	schema_name VARCHAR(80), 
	settings JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_tenants PRIMARY KEY (id)
);

CREATE INDEX ix_tenants_deleted_at ON tenants (deleted_at);

CREATE UNIQUE INDEX ix_tenants_slug ON tenants (slug);

CREATE TABLE permissions (
	id UUID NOT NULL, 
	code VARCHAR(100) NOT NULL, 
	description VARCHAR(255), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_permissions PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_permissions_code ON permissions (code);

CREATE TABLE audit_logs (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	user_id UUID, 
	action VARCHAR(100) NOT NULL, 
	resource VARCHAR(100) NOT NULL, 
	resource_id UUID, 
	old_values JSONB, 
	new_values JSONB, 
	ip_address VARCHAR(64), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_audit_logs PRIMARY KEY (id), 
	CONSTRAINT fk_audit_logs_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
);

CREATE INDEX ix_audit_logs_resource ON audit_logs (tenant_id, resource, resource_id);

CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id);

CREATE INDEX ix_audit_logs_tenant_id ON audit_logs (tenant_id);

CREATE INDEX ix_audit_logs_tenant_created ON audit_logs (tenant_id, created_at);

CREATE TABLE tenant_modules (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	module_id UUID NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	enabled_at TIMESTAMP WITH TIME ZONE, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_tenant_modules PRIMARY KEY (id), 
	CONSTRAINT uq_tenant_modules_tenant_module UNIQUE (tenant_id, module_id), 
	CONSTRAINT fk_tenant_modules_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT fk_tenant_modules_module_id_modules FOREIGN KEY(module_id) REFERENCES modules (id) ON DELETE CASCADE
);

CREATE INDEX ix_tenant_modules_module_id ON tenant_modules (module_id);

CREATE INDEX ix_tenant_modules_tenant_id ON tenant_modules (tenant_id);

CREATE TABLE roles (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	code VARCHAR(50) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	description VARCHAR(255), 
	is_system BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_roles PRIMARY KEY (id), 
	CONSTRAINT uq_roles_tenant_code UNIQUE (tenant_id, code), 
	CONSTRAINT fk_roles_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
);

CREATE INDEX ix_roles_tenant_id ON roles (tenant_id);

CREATE TABLE users (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	hashed_password VARCHAR(255) NOT NULL, 
	full_name VARCHAR(200) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	is_verified BOOLEAN NOT NULL, 
	is_superuser BOOLEAN NOT NULL, 
	last_login_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_users PRIMARY KEY (id), 
	CONSTRAINT uq_users_tenant_email UNIQUE (tenant_id, email), 
	CONSTRAINT fk_users_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
);

CREATE INDEX ix_users_email ON users (email);

CREATE INDEX ix_users_tenant_id ON users (tenant_id);

CREATE INDEX ix_users_deleted_at ON users (deleted_at);

CREATE TABLE categories (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	slug VARCHAR(140) NOT NULL, 
	description TEXT, 
	parent_id UUID, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_categories PRIMARY KEY (id), 
	CONSTRAINT uq_categories_tenant_slug UNIQUE (tenant_id, slug), 
	CONSTRAINT fk_categories_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT fk_categories_parent_id_categories FOREIGN KEY(parent_id) REFERENCES categories (id) ON DELETE SET NULL
);

CREATE INDEX ix_categories_deleted_at ON categories (deleted_at);

CREATE INDEX ix_categories_tenant_id ON categories (tenant_id);

CREATE INDEX ix_categories_slug ON categories (slug);

CREATE TABLE user_roles (
	user_id UUID NOT NULL, 
	role_id UUID NOT NULL, 
	CONSTRAINT pk_user_roles PRIMARY KEY (user_id, role_id), 
	CONSTRAINT fk_user_roles_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT fk_user_roles_role_id_roles FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE
);

CREATE TABLE role_permissions (
	role_id UUID NOT NULL, 
	permission_id UUID NOT NULL, 
	CONSTRAINT pk_role_permissions PRIMARY KEY (role_id, permission_id), 
	CONSTRAINT fk_role_permissions_role_id_roles FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE, 
	CONSTRAINT fk_role_permissions_permission_id_permissions FOREIGN KEY(permission_id) REFERENCES permissions (id) ON DELETE CASCADE
);

CREATE TABLE user_sessions (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	jti UUID NOT NULL, 
	user_agent VARCHAR(400), 
	ip_address VARCHAR(64), 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_user_sessions PRIMARY KEY (id), 
	CONSTRAINT fk_user_sessions_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT fk_user_sessions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_user_sessions_user_id ON user_sessions (user_id);

CREATE INDEX ix_user_sessions_tenant_id ON user_sessions (tenant_id);

CREATE UNIQUE INDEX ix_user_sessions_jti ON user_sessions (jti);

CREATE TABLE courses (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	slug VARCHAR(220) NOT NULL, 
	summary VARCHAR(500), 
	description TEXT, 
	category_id UUID, 
	status course_status NOT NULL, 
	level course_level NOT NULL, 
	is_free BOOLEAN NOT NULL, 
	price NUMERIC(10, 2) NOT NULL, 
	thumbnail_url VARCHAR(500), 
	enrollment_count INTEGER NOT NULL, 
	published_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_courses PRIMARY KEY (id), 
	CONSTRAINT uq_courses_tenant_slug UNIQUE (tenant_id, slug), 
	CONSTRAINT fk_courses_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT fk_courses_category_id_categories FOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE SET NULL
);

CREATE INDEX ix_courses_deleted_at ON courses (deleted_at);

CREATE INDEX ix_courses_title ON courses (title);

CREATE INDEX ix_courses_status ON courses (status);

CREATE INDEX ix_courses_category_id ON courses (category_id);

CREATE INDEX ix_courses_slug ON courses (slug);

CREATE INDEX ix_courses_tenant_id ON courses (tenant_id);

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

CREATE INDEX ix_assignments_course_id ON assignments (course_id);

CREATE INDEX ix_assignments_deleted_at ON assignments (deleted_at);

CREATE INDEX ix_assignments_tenant_id ON assignments (tenant_id);

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

CREATE INDEX ix_course_instructors_course_id ON course_instructors (course_id);

CREATE INDEX ix_course_instructors_tenant_id ON course_instructors (tenant_id);

CREATE INDEX ix_course_instructors_user_id ON course_instructors (user_id);

CREATE TABLE course_enrollments (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	course_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	status enrollment_status NOT NULL, 
	progress_pct INTEGER NOT NULL, 
	enrolled_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_course_enrollments PRIMARY KEY (id), 
	CONSTRAINT uq_enrollments_course_user UNIQUE (course_id, user_id), 
	CONSTRAINT fk_course_enrollments_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT fk_course_enrollments_course_id_courses FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE, 
	CONSTRAINT fk_course_enrollments_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_course_enrollments_course_id ON course_enrollments (course_id);

CREATE INDEX ix_course_enrollments_tenant_id ON course_enrollments (tenant_id);

CREATE INDEX ix_course_enrollments_user_id ON course_enrollments (user_id);

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

CREATE INDEX ix_course_modules_tenant_id ON course_modules (tenant_id);

CREATE INDEX ix_course_modules_deleted_at ON course_modules (deleted_at);

CREATE INDEX ix_course_modules_course_id ON course_modules (course_id);

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

CREATE INDEX ix_quizzes_tenant_id ON quizzes (tenant_id);

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

CREATE INDEX ix_submissions_user_id ON submissions (user_id);

CREATE INDEX ix_submissions_tenant_id ON submissions (tenant_id);

CREATE INDEX ix_submissions_assignment_id ON submissions (assignment_id);

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

CREATE INDEX ix_lessons_course_id ON lessons (course_id);

CREATE INDEX ix_lessons_tenant_id ON lessons (tenant_id);

CREATE INDEX ix_lessons_deleted_at ON lessons (deleted_at);

CREATE INDEX ix_lessons_module_id ON lessons (module_id);

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

CREATE INDEX ix_quiz_questions_quiz_id ON quiz_questions (quiz_id);

CREATE INDEX ix_quiz_questions_tenant_id ON quiz_questions (tenant_id);

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

CREATE INDEX ix_grades_tenant_id ON grades (tenant_id);

CREATE INDEX ix_grades_user_id ON grades (user_id);

CREATE INDEX ix_grades_assignment_id ON grades (assignment_id);

CREATE TABLE video_assets (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	lesson_id UUID NOT NULL, 
	provider VARCHAR(40) NOT NULL, 
	url VARCHAR(1000) NOT NULL, 
	hls_url VARCHAR(1000), 
	duration_seconds INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_video_assets PRIMARY KEY (id), 
	CONSTRAINT fk_video_assets_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT uq_video_assets_lesson_id UNIQUE (lesson_id), 
	CONSTRAINT fk_video_assets_lesson_id_lessons FOREIGN KEY(lesson_id) REFERENCES lessons (id) ON DELETE CASCADE
);

CREATE INDEX ix_video_assets_tenant_id ON video_assets (tenant_id);

CREATE TABLE document_assets (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	lesson_id UUID NOT NULL, 
	file_url VARCHAR(1000) NOT NULL, 
	file_type VARCHAR(40) NOT NULL, 
	size_bytes INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_document_assets PRIMARY KEY (id), 
	CONSTRAINT fk_document_assets_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
	CONSTRAINT uq_document_assets_lesson_id UNIQUE (lesson_id), 
	CONSTRAINT fk_document_assets_lesson_id_lessons FOREIGN KEY(lesson_id) REFERENCES lessons (id) ON DELETE CASCADE
);

CREATE INDEX ix_document_assets_tenant_id ON document_assets (tenant_id);

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

CREATE INDEX ix_lesson_progress_user_id ON lesson_progress (user_id);

CREATE INDEX ix_lesson_progress_lesson_id ON lesson_progress (lesson_id);

CREATE INDEX ix_lesson_progress_course_id ON lesson_progress (course_id);

CREATE INDEX ix_lesson_progress_tenant_id ON lesson_progress (tenant_id);

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

CREATE INDEX ix_quiz_answers_tenant_id ON quiz_answers (tenant_id);

CREATE INDEX ix_quiz_answers_question_id ON quiz_answers (question_id);
