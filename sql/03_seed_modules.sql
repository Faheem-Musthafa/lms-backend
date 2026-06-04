-- Generated from the SQLAlchemy models — DO NOT hand-edit.
-- Regenerate: python -m scripts.dump_sql
-- Matches Alembic migrations module catalog data.

-- Users/roles/permissions need argon2 hashing → run: python -m scripts.seed

INSERT INTO modules (id, code, name, description, is_active, is_core, created_at, updated_at)
VALUES (gen_random_uuid(), 'AUTH', 'Authentication & identity', 'Authentication & identity', true, true, now(), now())
ON CONFLICT (code) DO NOTHING;
INSERT INTO modules (id, code, name, description, is_active, is_core, created_at, updated_at)
VALUES (gen_random_uuid(), 'COURSES', 'Course catalog & enrollment', 'Course catalog & enrollment', true, false, now(), now())
ON CONFLICT (code) DO NOTHING;
INSERT INTO modules (id, code, name, description, is_active, is_core, created_at, updated_at)
VALUES (gen_random_uuid(), 'LEARNING', 'Lessons, content & progress', 'Lessons, content & progress', true, false, now(), now())
ON CONFLICT (code) DO NOTHING;
INSERT INTO modules (id, code, name, description, is_active, is_core, created_at, updated_at)
VALUES (gen_random_uuid(), 'ASSIGNMENTS', 'Assignments, quizzes & grading', 'Assignments, quizzes & grading', true, false, now(), now())
ON CONFLICT (code) DO NOTHING;
INSERT INTO modules (id, code, name, description, is_active, is_core, created_at, updated_at)
VALUES (gen_random_uuid(), 'DASHBOARD', 'Learner & instructor dashboards', 'Learner & instructor dashboards', true, false, now(), now())
ON CONFLICT (code) DO NOTHING;
INSERT INTO modules (id, code, name, description, is_active, is_core, created_at, updated_at)
VALUES (gen_random_uuid(), 'ADMIN', 'Administration, reports & analytics', 'Administration, reports & analytics', true, false, now(), now())
ON CONFLICT (code) DO NOTHING;
