-- Script to add random icon URLs to existing workflows
-- Icon URLs will be in the format: https://dtijyicuvv7hy.cloudfront.net/{id}.png
-- Where id is a random number from 1 to 11

-- Update all existing workflows with random icon URLs
UPDATE workflows
SET icon_url = 'https://dtijyicuvv7hy.cloudfront.net/' || (floor(random() * 11) + 1)::text || '.png'
WHERE icon_url IS NULL;

-- Verify the update
SELECT
    id,
    name,
    icon_url,
    created_at
FROM workflows
ORDER BY created_at DESC
LIMIT 20;
