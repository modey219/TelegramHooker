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

-- 4. Function: validate a license code (returns days_remaining)
CREATE OR REPLACE FUNCTION validate_license(p_code TEXT, p_device_id TEXT)
RETURNS JSON AS $$
DECLARE
    v_license licenses%ROWTYPE;
    v_device_count INTEGER;
    v_days_left INTEGER;
BEGIN
    SELECT * INTO v_license FROM licenses WHERE code = p_code AND is_active = TRUE;

    IF NOT FOUND THEN
        RETURN json_build_object('valid', false, 'error', 'Invalid code');
    END IF;

    IF v_license.expires_at IS NOT NULL AND v_license.expires_at < NOW() THEN
        RETURN json_build_object('valid', false, 'error', 'Code expired');
    END IF;

    IF v_license.expires_at IS NOT NULL THEN
        v_days_left := EXTRACT(DAY FROM (v_license.expires_at - NOW()))::INTEGER;
    ELSE
        v_days_left := -1;
    END IF;

    IF EXISTS (SELECT 1 FROM activations WHERE license_id = v_license.id AND device_id = p_device_id) THEN
        UPDATE activations SET last_check = NOW() WHERE license_id = v_license.id AND device_id = p_device_id;
        RETURN json_build_object('valid', true, 'message', 'Welcome back!', 'days_left', v_days_left, 'expires_at', v_license.expires_at);
    END IF;

    SELECT COUNT(*) INTO v_device_count FROM activations WHERE license_id = v_license.id;
    IF v_device_count >= v_license.max_devices THEN
        RETURN json_build_object('valid', false, 'error', 'Device limit reached (1 device only)');
    END IF;

    INSERT INTO activations (license_id, device_id) VALUES (v_license.id, p_device_id);
    UPDATE licenses SET active_devices = active_devices + 1 WHERE id = v_license.id;

    RETURN json_build_object('valid', true, 'message', 'Activated!', 'days_left', v_days_left, 'expires_at', v_license.expires_at);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 5. Function: generate a new license code
CREATE OR REPLACE FUNCTION generate_license(p_max_devices INTEGER DEFAULT 1, p_days INTEGER DEFAULT 30, p_note TEXT DEFAULT '')
RETURNS JSON AS $$
DECLARE
    v_code TEXT;
    v_expires TIMESTAMPTZ;
BEGIN
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

-- 7. Enable RLS
ALTER TABLE licenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE activations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow function calls" ON licenses FOR SELECT USING (FALSE);
CREATE POLICY "Allow function calls" ON activations FOR SELECT USING (FALSE);
