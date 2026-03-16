# Password Space Blog - Entity Relationship Diagram

This diagram shows the database schema for the Password Space Blog application, including authentication, blog posts, and JWT token management.

```mermaid
erDiagram
    USER ||--o{ POST : "authors"
    USER ||--o{ OUTSTANDING_TOKEN : "owns"
    OUTSTANDING_TOKEN ||--o| BLACKLISTED_TOKEN : "references"
    USER ||--o{ LOG_ENTRY : "performs"

    USER {
        int id
        string username
        string email
        string password
        string first_name
        string last_name
        boolean is_staff
        boolean is_active
        boolean is_superuser
        datetime date_joined
        datetime last_login
    }

    POST {
        int id
        int author_id
        string title
        string slug
        text content
        text excerpt
        int status
        datetime created_on
        datetime updated_on
    }

    OUTSTANDING_TOKEN {
        int id
        int user_id
        string jti
        text token
        datetime created_at
        datetime expires_at
    }

    BLACKLISTED_TOKEN {
        int id
        int token_id
        datetime blacklisted_at
    }

    LOG_ENTRY {
        int id
        int user_id
        int content_type_id
        string object_id
        string object_repr
        int action_flag
        text change_message
        datetime action_time
    }
```

## Tables Overview

| Table | Purpose |
|-------|---------|
| **User** | Authentication & user profiles (Argon2 hashed, 12+ chars min) |
| **Post** | Blog posts with author, slug, draft/published status |
| **OutstandingToken** | Active JWT refresh tokens |
| **BlacklistedToken** | Revoked/logged-out tokens |
| **LogEntry** | Django admin audit trail |

## Key Relationships

- User → Post (1:M, cascade delete)
- User → OutstandingToken (1:M, cascade delete)
- OutstandingToken → BlacklistedToken (1:1)

## Indexes and Constraints

- **Unique Constraints**:
  - `User.username`
  - `Post.title`
  - `Post.slug`
  - `OutstandingToken.jti`
  - `BlacklistedToken.token_id`

- **Ordering**:
  - `Post`: Ordered by `-created_on` (newest first)

## Security Features

- **Password Storage**: Argon2 hashing (memory-hard algorithm)
- **Password Policy**: Minimum 12 characters enforced
- **JWT Tokens**: Stored in HTTP-only cookies (no localStorage exposure)
- **Token Rotation**: New refresh token issued on each refresh
- **Token Blacklist**: Logout immediately invalidates tokens
- **Cookie Security**: Secure, HttpOnly, SameSite=Lax flags
