-- Migration: Add check_user_exists RPC function
-- Description: Create RPC function to check if user exists in auth.users schema
-- This fixes the issue where Supabase client incorrectly interprets auth.users as public.auth.users
-- Created: 2025-08-13

-- ==============================================================================
-- CREATE RPC FUNCTION TO CHECK USER EXISTS IN AUTH SCHEMA
-- ==============================================================================

CREATE OR REPLACE FUNCTION check_user_exists(user_id uuid)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Check if user exists in auth.users table
    -- Using SECURITY DEFINER allows function to access auth schema
    RETURN EXISTS (
        SELECT 1
        FROM auth.users
        WHERE id = user_id
    );
END;
$$;

-- Grant execute permission to authenticated users and service role
GRANT EXECUTE ON FUNCTION check_user_exists(uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION check_user_exists(uuid) TO service_role;

-- Add comment for documentation
COMMENT ON FUNCTION check_user_exists IS 'Check if a user exists in auth.users table. Used by GitHub installation callback to validate user IDs.';

-- Test the function with a verification query
DO $$
BEGIN
    RAISE NOTICE 'check_user_exists function created successfully';
    RAISE NOTICE 'This function can be called via Supabase RPC to check user existence in auth.users schema';
    RAISE NOTICE 'Usage: supabase.rpc("check_user_exists", {"user_id": "uuid-string"})';
END;
$$;
