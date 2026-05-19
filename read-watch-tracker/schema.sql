CREATE TABLE IF NOT EXISTS movie_records (
    record_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    rating INTEGER CHECK (rating IS NULL OR rating BETWEEN 1 AND 5),
    genre TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (status IN ('想讀/想看', '進行中', '完成')),
    remark TEXT NOT NULL DEFAULT '',
    tags TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS book_records (
    record_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    isbn TEXT,
    rating INTEGER CHECK (rating IS NULL OR rating BETWEEN 1 AND 5),
    genre TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (status IN ('想讀/想看', '進行中', '完成')),
    remark TEXT NOT NULL DEFAULT '',
    tags TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS course_records (
    record_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    platform TEXT,
    instructor TEXT,
    url TEXT,
    rating INTEGER CHECK (rating IS NULL OR rating BETWEEN 1 AND 5),
    genre TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (status IN ('想讀/想看', '進行中', '完成')),
    remark TEXT NOT NULL DEFAULT '',
    tags TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS paper_records (
    record_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    year INTEGER,
    doi_or_url TEXT,
    key_takeaways TEXT,
    implementation_value TEXT,
    rating INTEGER CHECK (rating IS NULL OR rating BETWEEN 1 AND 5),
    genre TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (status IN ('想讀/想看', '進行中', '完成')),
    remark TEXT NOT NULL DEFAULT '',
    tags TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
