-- Partner Intelligence Migration Script
-- Add new fields to the partners table for website scraping and AI analysis

-- Website content and scraping fields
ALTER TABLE partners ADD COLUMN IF NOT EXISTS website_content TEXT;
ALTER TABLE partners ADD COLUMN IF NOT EXISTS scraped_offerings JSON;
ALTER TABLE partners ADD COLUMN IF NOT EXISTS capabilities_summary TEXT;
ALTER TABLE partners ADD COLUMN IF NOT EXISTS last_scraped TIMESTAMP;
ALTER TABLE partners ADD COLUMN IF NOT EXISTS scrape_status VARCHAR(20) DEFAULT 'PENDING';
ALTER TABLE partners ADD COLUMN IF NOT EXISTS scrape_error TEXT;

-- AI-enhanced fields
ALTER TABLE partners ADD COLUMN IF NOT EXISTS solution_categories JSON;
ALTER TABLE partners ADD COLUMN IF NOT EXISTS technology_stack JSON;
ALTER TABLE partners ADD COLUMN IF NOT EXISTS industry_focus JSON;
ALTER TABLE partners ADD COLUMN IF NOT EXISTS competitive_advantages JSON;

-- Update existing partners to have PENDING scrape status
UPDATE partners SET scrape_status = 'PENDING' WHERE scrape_status IS NULL;

-- Show the updated table structure
\d partners;