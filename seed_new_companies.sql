-- Run this once in Supabase SQL editor to add all new companies with careers URLs.
-- Safe to re-run — ON CONFLICT (name) DO UPDATE only fills in blank careers_url.

INSERT INTO companies (name, careers_url) VALUES
  ('Snowflake',          'https://careers.snowflake.com'),
  ('Uber',               'https://www.uber.com/us/en/careers/list/'),
  ('Cardinal Health',    'https://jobs.cardinalhealth.com/en/careers'),
  ('Qualcomm',           'https://careers.qualcomm.com/careers'),
  ('Stripe',             'https://stripe.com/jobs'),
  ('Databricks',         'https://www.databricks.com/company/careers'),
  ('Airbnb',             'https://careers.airbnb.com'),
  ('Lyft',               'https://www.lyft.com/careers'),
  ('Pinterest',          'https://www.pinterestcareers.com'),
  ('Robinhood',          'https://careers.robinhood.com'),
  ('Datadog',            'https://careers.datadoghq.com'),
  ('MongoDB',            'https://www.mongodb.com/careers'),
  ('Instacart',          'https://instacart.careers'),
  ('Palo Alto Networks', 'https://jobs.paloaltonetworks.com'),
  ('Dropbox',            'https://jobs.dropbox.com'),
  ('Eli Lilly',          'https://lilly.wd5.myworkdayjobs.com/en-US/LLY'),
  ('AMD',                'https://careers.amd.com/careers-home/jobs'),
  ('Cincinnati Children''s', 'https://jobs.cincinnatichildrens.org/search-jobs'),
  ('Wayfair',               'https://www.wayfair.com/careers/jobs/?teamIds=1&countryIds=1'),
  ('Elevance Health',       'https://elevancehealth.wd1.myworkdayjobs.com/ANT/jobs')
ON CONFLICT (name) DO UPDATE
  SET careers_url = EXCLUDED.careers_url
  WHERE companies.careers_url IS NULL;
