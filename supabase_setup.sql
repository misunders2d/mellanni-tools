-- Mellanni Tools: Supabase user management setup
-- Run this in the Supabase SQL Editor (Dashboard → SQL Editor → New query)

-- 1. Create the app_users table
CREATE TABLE IF NOT EXISTS public.app_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    picture_url TEXT,
    roles TEXT[] NOT NULL DEFAULT '{viewer}',  -- e.g. '{admin}', '{sales,viewer}'
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Enable Row Level Security
ALTER TABLE public.app_users ENABLE ROW LEVEL SECURITY;

-- 3. Allow read access via anon key (the app reads user records to check authorization)
CREATE POLICY "Allow anon read access" ON public.app_users
    FOR SELECT USING (true);

-- 4. Seed users
INSERT INTO public.app_users (email, roles) VALUES
    ('2djohar@gmail.com', '{admin,sales,viewer}'),
    ('sergey@mellanni.com', '{admin,sales,viewer}'),
    ('sergey@poluco.co', '{admin,sales,viewer}'),
    ('vitalii@mellanni.com', '{sales,viewer}'),
    ('ruslan@mellanni.com', '{sales,viewer}'),
    ('bohdan@mellanni.com', '{sales,viewer}'),
    ('igor@mellanni.com', '{sales,viewer}'),
    ('margarita@mellanni.com', '{sales,viewer}'),
    ('masao@mellanni.com', '{sales,viewer}'),
    ('valerii@mellanni.com', '{sales,viewer}'),
    ('allysa@mellanni.com', '{viewer}'),
    ('ahmad@mellanni.com', '{viewer}'),
    ('ana@mellanni.com', '{viewer}'),
    ('ann@mellanni.com', '{viewer}'),
    ('andreia@mellanni.com', '{viewer}'),
    ('bernard@mellanni.com', '{viewer}'),
    ('caleb@mellanni.com', '{viewer}'),
    ('dariyka@mellanni.com', '{viewer}'),
    ('david@mellanni.com', '{viewer}'),
    ('ethan@mellanni.com', '{viewer}'),
    ('evelyn@mellanni.com', '{viewer}'),
    ('fabiana@mellanni.com', '{viewer}'),
    ('gor@mellanni.com', '{viewer}'),
    ('hanna@mellanni.com', '{viewer}'),
    ('hans@mellanni.com', '{viewer}'),
    ('info@imvital.net', '{viewer}'),
    ('jennifer@mellanni.com', '{viewer}'),
    ('juan@mellanni.com', '{viewer}'),
    ('karl@mellanni.com', '{viewer}'),
    ('katarina@mellanni.com', '{viewer}'),
    ('ksenia@mellanni.com', '{viewer}'),
    ('lina@mellanni.com', '{viewer}'),
    ('mai@mellanni.com', '{viewer}'),
    ('matt@mellanni.com', '{viewer}'),
    ('mohammad@mellanni.com', '{viewer}'),
    ('nair@mellanni.com', '{viewer}'),
    ('natalie@mellanni.com', '{viewer}'),
    ('nomier@mellanni.com', '{viewer}'),
    ('olha@mellanni.com', '{viewer}'),
    ('oleksii@mellanni.com', '{viewer}'),
    ('shelby@mellanni.com', '{viewer}'),
    ('vicky@mellanni.com', '{viewer}')
ON CONFLICT (email) DO NOTHING;
