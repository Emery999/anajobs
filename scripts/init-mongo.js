// MongoDB initialization script
// Creates the nonprofit_jobs database and a user

db = db.getSiblingDB('nonprofit_jobs');

// Create a user for the application
db.createUser({
  user: 'anajobs_user',
  pwd: 'anajobs_password',
  roles: [
    {
      role: 'readWrite',
      db: 'nonprofit_jobs'
    }
  ]
});

// Create the organizations collection with validation schema
db.createCollection('organizations', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['name', 'root', 'jobs'],
      properties: {
        name: {
          bsonType: 'string',
          description: 'Organization name - required'
        },
        root: {
          bsonType: 'string',
          pattern: '^https?://',
          description: 'Root website URL - required and must be valid URL'
        },
        jobs: {
          bsonType: 'string',
          pattern: '^https?://',
          description: 'Jobs page URL - required and must be valid URL'
        },
        status: {
          bsonType: 'string',
          enum: ['active', 'inactive', 'pending'],
          description: 'Organization status'
        },
        scraped: {
          bsonType: 'bool',
          description: 'Whether jobs have been scraped'
        },
        last_scraped: {
          bsonType: 'date',
          description: 'Last scrape date'
        }
      }
    }
  }
});

// Create indexes
db.organizations.createIndex({ 'name': 1 }, { unique: true });
db.organizations.createIndex({ 'root': 1 });
db.organizations.createIndex({ 'jobs': 1 });
db.organizations.createIndex({ 'status': 1 });
db.organizations.createIndex({ 'scraped': 1 });
db.organizations.createIndex({ 'last_scraped': 1 });

print('Database initialization completed successfully!');