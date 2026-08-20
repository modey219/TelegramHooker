-- ============================================
-- Telegram Hooker - Activation Code System
-- Run this in Supabase SQL Editor
-- ============================================

-- 1. Activation codes table
CREATE TABLE IF NOT EXISTS licenses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    max_devices INTEGER DEFAULT 1,
    active_devices INTEGER DEFAULT 0,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    note TEXT
);

-- 2. Device activations table
CREATE TABLE IF NOT EXISTS activations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    license_id UUID REFERENCES licenses(id) ON DELETE CASCADE,
    device_id TEXT NOT NULL,
    activated_at TIMESTAMPTZ DEFAULT NOW(),
    last_check TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(license_id, device_id)
);

-- 3. Indexes
CREATE INDEX IF NOT EXISTS idx_licenses_code ON licenses(code);
CREATE INDEX IF NOT EXISTS idx_activations_device ON activations(device_id);

-- 4. Function: validate a license code
CREATE OR REPLACE FUNCTION validate_license(p_code TEXT, p_device_id TEXT)
RETURNS JSON AS $$
DECLARE
    v_license licenses%ROWTYPE;
    v_device_count INTEGER;
BEGIN
    -- Find the license
    SELECT * INTO v_license FROM licenses WHERE code = p_code AND is_active = TRUE;

    IF NOT FOUND THEN
        RETURN json_build_object('valid', false, 'error', 'Invalid code');
    END IF;

    -- Check expiry
    IF v_license.expires_at IS NOT NULL AND v_license.expires_at < NOW() THEN
        RETURN json_build_object('valid', false, 'error', 'Code expired');
    END IF;

    -- Check if this device is already activated
    IF EXISTS (SELECT 1 FROM activations WHERE license_id = v_license.id AND device_id = p_device_id) THEN
        -- Already activated, update last_check
        UPDATE activations SET last_check = NOW() WHERE license_id = v_license.id AND device_id = p_device_id;
        RETURN json_build_object('valid', true, 'message', 'Welcome back!');
    END IF;

    -- Check device limit
    SELECT COUNT(*) INTO v_device_count FROM activations WHERE license_id = v_license.id;
    IF v_device_count >= v_license.max_devices THEN
        RETURN json_build_object('valid', false, 'error', 'Device limit reached (' || v_license.max_devices || ' max)');
    END IF;

    -- Activate this device
    INSERT INTO activations (license_id, device_id) VALUES (v_license.id, p_device_id);
    UPDATE licenses SET active_devices = active_devices + 1 WHERE id = v_license.id;

    RETURN json_build_object('valid', true, 'message', 'Activated successfully!');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 5. Function: generate a new license code
CREATE OR REPLACE FUNCTION generate_license(p_max_devices INTEGER DEFAULT 1, p_days INTEGER DEFAULT 30, p_note TEXT DEFAULT '')
RETURNS JSON AS $$
DECLARE
    v_code TEXT;
    v_expires TIMESTAMPTZ;
BEGIN
    -- Generate random code: TH-XXXX-XXXX-XXXX
    v_code := 'TH-' ||
              upper(substring(md5(random()::text) from 1 for 4)) || '-' ||
              upper(substring(md5(random()::text) from 1 for 4)) || '-' ||
              upper(substring(md5(random()::text) from 1 for 4));

    IF p_days > 0 THEN
        v_expires := NOW() + (p_days || ' days')::INTERVAL;
    ELSE
        v_expires := NULL;
    END IF;

    INSERT INTO licenses (code, max_devices, expires_at, note)
    VALUES (v_code, p_max_devices, v_expires, p_note);

    RETURN json_build_object('code', v_code, 'max_devices', p_max_devices, 'expires_at', v_expires);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 6. Function: revoke a license
CREATE OR REPLACE FUNCTION revoke_license(p_code TEXT)
RETURNS JSON AS $$
BEGIN
    UPDATE licenses SET is_active = FALSE WHERE code = p_code;
    DELETE FROM activations WHERE license_id = (SELECT id FROM licenses WHERE code = p_code);
    RETURN json_build_object('success', true, 'message', 'License revoked');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 7. Enable RLS (Row Level Security)
ALTER TABLE licenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE activations ENABLE ROW LEVEL SECURITY;

-- 8. Public can only call the functions (not read tables directly)
CREATE POLICY "Allow function calls" ON licenses FOR SELECT USING (FALSE);
CREATE POLICY "Allow function calls" ON activations FOR SELECT USING (FALSE);

-- ============================================
-- RUN THESE AFTER TABLES ARE CREATED:
-- Go to Supabase > Settings > API
-- Copy the "anon" key and "URL"
-- Then update server/config.json
-- ============================================
