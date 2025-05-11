import os
from app import app, db  # noqa: F401

# Make sure the DATABASE_URL is set
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    print("WARNING: DATABASE_URL not set, using sqlite:///:memory: instead")
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
else:
    # Show just the first part of the URL to avoid exposing credentials
    masked_url = database_url.split('@')[0][:10] + '...' if '@' in database_url else database_url[:10] + '...'
    print(f"DATABASE_URL is set: {masked_url}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
