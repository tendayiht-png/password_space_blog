# Password Space Blog - Entity Relationship Diagram

This diagram shows the database schema for the Password Space Blog application, including authentication, blog posts, comments, and JWT token management.

```mermaid
erDiagram
    USER ||--o{ POST : "authors"
    USER ||--o{ COMMENT : "writes"
    POST ||--o{ COMMENT : "has"
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

    COMMENT {
        int id
        int post_id
        int author_id
        text body
        boolean approved
        datetime created_on
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

## Table Descriptions

### Core Blog Tables

#### User (Django Auth)
- **Purpose**: Stores user authentication and profile information
- **Key Fields**:
  - `username`: Unique identifier for login
  - `password`: Argon2 hashed password (12+ character minimum enforced)
  - `is_staff`: Admin panel access flag
  - `is_superuser`: Full administrative privileges

#### Post
- **Purpose**: Blog post content and metadata
- **Key Fields**:
  - `author_id`: Foreign key to User (related_name: "blog_posts")
  - `slug`: URL-friendly identifier (unique)
  - `status`: Draft (0) or Published (1)
  - `created_on`: Auto-set on creation
  - `updated_on`: Auto-updated on save

#### Comment
- **Purpose**: User comments on blog posts
- **Key Fields**:
  - `post_id`: Foreign key to Post (related_name: "comments")
  - `author_id`: Foreign key to User (related_name: "commenter")
  - `approved`: Moderation flag (default: false)

### JWT Authentication Tables

#### OutstandingToken
- **Purpose**: Tracks all issued JWT refresh tokens
- **Key Fields**:
  - `user_id`: Foreign key to User
  - `jti`: Unique JSON Web Token ID
  - `token`: Full JWT refresh token string
  - `expires_at`: Token expiration timestamp

#### BlacklistedToken
- **Purpose**: Revoked/invalidated refresh tokens
- **Key Fields**:
  - `token_id`: Foreign key to OutstandingToken (unique)
  - `blacklisted_at`: Timestamp of revocation
- **Behavior**: When a user logs out, their refresh token is added here

### System Tables

#### LogEntry (Django Admin)
- **Purpose**: Audit trail for admin actions
- **Key Fields**:
  - `user_id`: Admin user who performed action
  - `content_type_id`: Type of model affected
  - `action_flag`: Add (1), Change (2), Delete (3)

## Relationships

1. **User → Post** (One-to-Many)
   - Each user can author multiple posts
   - Cascade delete: Deleting user deletes their posts

2. **User → Comment** (One-to-Many)
   - Each user can write multiple comments
   - Cascade delete: Deleting user deletes their comments

3. **Post → Comment** (One-to-Many)
   - Each post can have multiple comments
   - Cascade delete: Deleting post deletes its comments

4. **User → OutstandingToken** (One-to-Many)
   - Each user can have multiple active JWT tokens
   - Cascade delete: Deleting user deletes their tokens

5. **OutstandingToken → BlacklistedToken** (One-to-One)
   - Each token can be blacklisted only once
   - Cascade delete: Deleting token deletes blacklist entry

## Indexes and Constraints

- **Unique Constraints**:
  - `User.username`
  - `Post.title`
  - `Post.slug`
  - `OutstandingToken.jti`
  - `BlacklistedToken.token_id`

- **Ordering**:
  - `Post`: Ordered by `-created_on` (newest first)
  - `Comment`: Ordered by `created_on` (oldest first)

## Security Features

- **Password Storage**: Argon2 hashing (memory-hard algorithm)
- **Password Policy**: Minimum 12 characters enforced
- **JWT Tokens**: Stored in HTTP-only cookies (no localStorage exposure)
- **Token Rotation**: New refresh token issued on each refresh
- **Token Blacklist**: Logout immediately invalidates tokens
- **Cookie Security**: Secure, HttpOnly, SameSite=Lax flags
