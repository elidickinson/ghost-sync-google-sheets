# Ghost Admin API Members Endpoints Documentation

Ghost Admin API provides comprehensive member management through RESTful endpoints supporting CRUD operations, filtering, and bulk operations. All endpoints require JWT authentication and support the Ghost Query Language (NQL) for advanced filtering.

## Authentication and Base Configuration

**Base URL**: `https://{admin_domain}/ghost/api/admin/members/`

**Required Headers**:
- `Authorization: Ghost {JWT_TOKEN}` - JWT signed with Admin API key
- `Accept-Version: v6.0` - API version header
- `Content-Type: application/json` - For POST/PUT requests

**JWT Structure**: Token must include API key ID in header (`kid`), audience set to `/admin/`, and be signed with the hexadecimal-decoded API secret. Tokens expire after 5 minutes.

**Implementation**: Endpoints are implemented in [members.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/api/endpoints/members.js), with core logic in the [members-api package](https://github.com/TryGhost/Ghost/tree/main/ghost/core/core/server/services/members/members-api). The [member model](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/models/member.js) defines the database schema and relationships.

## Browse Members

**Retrieves a paginated list of members with optional filtering, sorting, and related data inclusion.**

### Endpoint Details

**HTTP Method**: `GET`  
**Path**: `/ghost/api/admin/members/`  
**JavaScript SDK**: `api.members.browse(options)`

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 15 | Number of records per page |
| `page` | integer | No | 1 | Page number for pagination |
| `filter` | string | No | - | NQL filter expression (URL encoded) |
| `order` | string | No | - | Sort field and direction (e.g., `created_at DESC`) |
| `include` | string | No | - | Comma-separated related resources: `labels`, `newsletters`, `subscriptions`, `tiers` |
| `fields` | string | No | - | Comma-separated list of fields to return |

### Response Structure

```json
{
  "members": [
    {
      "id": "member_id_string",
      "uuid": "uuid-string",
      "email": "user@example.com",
      "name": "Member Name",
      "note": "Optional notes about member",
      "status": "free",
      "geolocation": "location_data",
      "email_count": 15,
      "email_opened_count": 8,
      "email_open_rate": 53,
      "email_disabled": false,
      "enable_comment_notifications": true,
      "last_seen_at": "2025-11-15T12:00:00.000Z",
      "last_commented_at": "2025-11-10T12:00:00.000Z",
      "created_at": "2025-01-01T12:00:00.000Z",
      "updated_at": "2025-11-15T12:00:00.000Z",
      "labels": [],
      "newsletters": [],
      "subscriptions": [],
      "tiers": []
    }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "limit": 15,
      "pages": 10,
      "total": 150,
      "next": 2,
      "prev": null
    }
  }
}
```

### Response Fields

**Core Fields**:
- `id` (string) - Unique member identifier (24 chars)
- `uuid` (string) - Universal unique identifier (36 chars)
- `email` (string) - Member email address (unique, max 191 chars)
- `name` (string, nullable) - Member full name (max 191 chars)
- `note` (string, nullable) - Admin notes (max 2000 chars)
- `status` (string) - Membership status: `free`, `paid`, or `comped`
- `expertise` (string, nullable) - Member expertise/profession (max 191 chars)

**Engagement Fields**:
- `email_count` (integer) - Total emails sent to member
- `email_opened_count` (integer) - Total emails opened by member
- `email_open_rate` (integer, nullable) - Calculated open rate percentage
- `email_disabled` (boolean) - Email delivery disabled due to bounces or spam complaints (only affects newsletter sends)
- `enable_comment_notifications` (boolean) - Comment notification preference
- `last_seen_at` (datetime, nullable) - Last site activity
- `last_commented_at` (datetime, nullable) - Last comment timestamp

**Audit Fields**:
- `created_at` (datetime) - Record creation timestamp
- `created_by` (string, nullable) - User ID who created record
- `updated_at` (datetime, nullable) - Last update timestamp
- `updated_by` (string, nullable) - User ID who last updated

**Related Data** (when included):
- `labels` (array) - Member labels for segmentation
- `newsletters` (array) - Newsletter subscriptions
- `subscriptions` (array) - Stripe subscription details
- `tiers` (array) - Products/tiers member has access to

### Example Requests

```javascript
// Basic browse
const members = await api.members.browse();

// With pagination and filtering
const paidMembers = await api.members.browse({
  filter: 'status:paid',
  limit: 50,
  page: 2,
  include: 'labels,tiers',
  order: 'created_at DESC'
});

// Complex filter
const vipMembers = await api.members.browse({
  filter: 'label:vip+email_open_rate:>0.5+email_disabled:false',
  include: 'labels,newsletters,subscriptions,tiers'
});
```

## Read Single Member

**Retrieves a single member by ID or email.**

### Endpoint Details

**HTTP Method**: `GET`  
**Path**: `/ghost/api/admin/members/{id}/`  
**JavaScript SDK**: `api.members.read(options)`

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Member ID (use in path or as option with email) |

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `include` | string | No | - | Related resources: `labels`, `newsletters`, `subscriptions`, `tiers` |
| `fields` | string | No | - | Specific fields to return |

### Alternative Lookup

Can also read by email:
```javascript
api.members.read({email: 'user@example.com'});
```

### Response Structure

Returns a single member object (not wrapped in array):

```json
{
  "members": [
    {
      "id": "member_id",
      "uuid": "uuid-string",
      "email": "user@example.com",
      "name": "Member Name",
      "status": "paid",
      "labels": [...],
      "subscriptions": [...],
      "tiers": [...]
    }
  ]
}
```

### Response Fields

Same fields as Browse Members endpoint. All member fields are returned unless limited by `fields` parameter.

### Example Requests

```javascript
// Read by ID
const member = await api.members.read({id: 'member_id'});

// Read by ID with includes
const member = await api.members.read({
  id: 'member_id',
  include: 'labels,newsletters,subscriptions,tiers'
});

// Read by email
const member = await api.members.read({email: 'user@example.com'});
```

## Create Member

**Creates a new member with optional newsletter subscriptions, labels, and tier assignments.**

### Endpoint Details

**HTTP Method**: `POST`  
**Path**: `/ghost/api/admin/members/`  
**JavaScript SDK**: `api.members.add(data, options)`  
**Status Code**: `201 Created`

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `send_email` | boolean | No | false | Send signup/signin email to member |
| `email_type` | string | No | - | Email type: `signin`, `signup`, or `subscribe` |

### Request Body

**Required Fields**:
- `email` (string) - Member email address (must be unique)

**Optional Fields**:
- `name` (string) - Member full name
- `note` (string) - Admin notes about member (max 2000 chars)
- ~~`subscribed` (boolean) - Newsletter subscription (deprecated, use `newsletters` array)~~
- `labels` (array) - Array of label objects or label name strings
- `newsletters` (array) - Array of newsletter objects to subscribe to
- `tiers` (array) - Array of tier objects with optional `expiry_at`
- `stripe_customer_id` (string) - Link to existing Stripe customer
- `comped` (boolean) - Grant complimentary paid access

### Request Structure

```json
{
  "members": [
    {
      "email": "newmember@example.com",
      "name": "New Member",
      "note": "Added via API",
      "subscribed": true,
      "labels": [
        {"name": "Early Adopter"},
        "VIP"
      ],
      "newsletters": [
        {"id": "newsletter_id"}
      ],
      "tiers": [
        {
          "id": "tier_id",
          "expiry_at": "2026-01-01T00:00:00.000Z"
        }
      ]
    }
  ]
}
```

### Advanced: Creating Paid Members

```json
{
  "members": [
    {
      "email": "paid@example.com",
      "name": "Paid Member",
      "comped": true,
      "tiers": [
        {
          "id": "tier_id",
          "expiry_at": "2026-12-31T00:00:00.000Z"
        }
      ]
    }
  ]
}
```

### Response Structure

Returns the created member object with all fields, including generated `id`, `uuid`, `created_at`:

```json
{
  "members": [
    {
      "id": "new_member_id",
      "uuid": "generated-uuid",
      "email": "newmember@example.com",
      "name": "New Member",
      "status": "free",
      "created_at": "2025-11-16T12:00:00.000Z",
      "labels": [...],
      "newsletters": [...]
    }
  ]
}
```

### Validation Rules

- **email**: Required, must be valid email format, unique, max 191 characters
- **name**: Optional, max 191 characters
- **note**: Optional, max 2000 characters
- **email_type**: Must be one of: `signin`, `signup`, `subscribe`
- **labels**: Can be array of strings (label names) or objects with `name` property
- **stripe_customer_id**: If provided, must exist in Stripe and not already linked

### Example Requests

```javascript
// Simple member creation
const member = await api.members.add({
  email: 'user@example.com',
  name: 'John Doe'
});

// With labels and newsletters
const member = await api.members.add({
  email: 'user@example.com',
  name: 'Jane Doe',
  labels: ['Early Adopter', 'Newsletter'],
  newsletters: [{id: 'newsletter_id'}]
});

// Send signin email
const member = await api.members.add(
  {
    email: 'user@example.com',
    name: 'Member Name'
  },
  {
    send_email: true,
    email_type: 'signin'
  }
);

// Create with complimentary tier
const member = await api.members.add({
  email: 'comped@example.com',
  name: 'Comped Member',
  comped: true,
  tiers: [{ id: 'tier_id' }]
});
```

### Special Behaviors

1. **Stripe Integration**: When `stripe_customer_id` provided, Ghost links the member to the Stripe customer and imports subscription data
2. **Magic Link**: With `send_email=true`, member receives a passwordless login link
3. **Status Calculation**: Status set to `paid` if member has active subscriptions, `comped` if complimentary access granted, otherwise `free`
4. **Label Creation**: If label names don't exist, they are automatically created

## Update Member

**Updates an existing member's information, labels, and newsletter subscriptions.**

### Endpoint Details

**HTTP Method**: `PUT`  
**Path**: `/ghost/api/admin/members/{id}/`  
**JavaScript SDK**: `api.members.edit(data)`  
**Status Code**: `200 OK`

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Member ID (must also be in request body) |

### Request Body

**Required Fields**:
- `id` (string) - Member ID (must match path parameter)
- `updated_at` (datetime) - Current timestamp from original member object (for conflict detection)

**Updatable Fields**:
- `email` (string) - Change member email address
- `name` (string) - Update member name
- `note` (string) - Update admin notes
- ~~`subscribed` (boolean) - Update newsletter subscription (deprecated)~~
- `labels` (array) - Replace member labels (full replacement, not merge)
- `newsletters` (array) - Update newsletter subscriptions
- `comped` (boolean) - Grant or revoke complimentary access

### Request Structure

```json
{
  "members": [
    {
      "id": "member_id",
      "name": "Updated Name",
      "email": "newemail@example.com",
      "note": "Updated notes",
      "labels": [
        {"name": "Premium"},
        "Active"
      ],
      "updated_at": "2025-11-15T12:00:00.000Z"
    }
  ]
}
```

### Important Notes

**Cannot Update Through This Endpoint**:
- `stripe_customer_id` - Use service methods or Stripe API
- `subscriptions` - Managed through Stripe API
- Direct tier assignments - Use `comped` flag or Stripe subscriptions
- `created_at` - Immutable
- `status` - Calculated field based on subscriptions

**Complimentary Subscription Management**:
```json
{
  "members": [
    {
      "id": "member_id",
      "comped": true,
      "updated_at": "2025-11-15T12:00:00.000Z"
    }
  ]
}
```

Setting `comped: true` creates a complimentary subscription; `comped: false` cancels it.

### Response Structure

Returns updated member with all current data:

```json
{
  "members": [
    {
      "id": "member_id",
      "email": "newemail@example.com",
      "name": "Updated Name",
      "updated_at": "2025-11-16T12:00:00.000Z",
      "labels": [...],
      "subscriptions": [...]
    }
  ]
}
```

### Conflict Prevention

The `updated_at` field prevents concurrent update conflicts. If the timestamp doesn't match the current record, the update fails with a conflict error.

### Example Requests

```javascript
// Update name and email
const member = await api.members.edit({
  id: 'member_id',
  name: 'Updated Name',
  email: 'newemail@example.com',
  updated_at: member.updated_at
});

// Replace labels
const member = await api.members.edit({
  id: 'member_id',
  labels: ['VIP', 'Active Subscriber'],
  updated_at: member.updated_at
});

// Grant complimentary access
const member = await api.members.edit({
  id: 'member_id',
  comped: true,
  updated_at: member.updated_at
});

// Update newsletter subscriptions
const member = await api.members.edit({
  id: 'member_id',
  newsletters: [
    {id: 'newsletter_1'},
    {id: 'newsletter_2'}
  ],
  updated_at: member.updated_at
});
```

## Delete Member

**Hard deletes a member permanently from the database and optionally cancels their Stripe subscriptions.**

Ghost performs true hard deletion without any soft-delete mechanism. When a member is deleted, the database row is completely removed using standard SQL DELETE operations. The members table schema contains no deleted_at timestamp or status field for tracking deleted records.

### Endpoint Details

**HTTP Method**: `DELETE`  
**Path**: `/ghost/api/admin/members/{id}/`  
**JavaScript SDK**: `api.members.delete(options)`  
**Status Code**: `204 No Content`

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Member ID to delete |

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `cancel` | boolean | No | false | Cancel Stripe subscriptions before deletion |

### Deletion Behavior

**Standard Delete** (without `cancel`):
- Member record is permanently deleted
- Labels and subscriptions are removed
- Stripe subscriptions remain active (creating orphaned subscriptions)
- Event records remain for analytics

**Delete with Cancel** (`?cancel=true`):
- Cancels active Stripe subscriptions
- Then permanently deletes the member record
- Member loses access immediately

**Bulk Deletion**:
- Requires explicit filters to prevent accidental mass deletion
- Never cancels Stripe subscriptions
- Uses optimized bulk deletion queries


### Response

No content returned on successful deletion (204 status).

### Example Requests

```javascript
// Basic deletion
await api.members.delete({id: 'member_id'});

// Delete and cancel subscriptions
await api.members.delete({
  id: 'member_id',
  cancel: true
});
```

### Cascade Behavior

Deleting a member cascades to:
- **members_labels** - Label associations removed
- **members_newsletters** - Newsletter subscriptions removed
- **members_products** - Tier associations removed
- **members_stripe_customers** - Stripe customer link removed (configured via bookshelf-relations)

Event tables (login events, status events, payment events) typically preserved for analytics. Cascade deletion is configured in the [member model](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/models/member.js).

## Duplicate Email Handling

Ghost enforces strict email uniqueness with important considerations for imports and member management.

### Database Email Constraints

The [members table](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/models/member.js) enforces a unique constraint on the email column at the database level:
- Attempting to create a member with an existing email triggers an `ER_DUP_ENTRY` MySQL error
- Ghost surfaces this as a 500 Internal Server Error rather than a more helpful validation message
- The email field has a maxlength of 191 characters (reduced from 254) to ensure compatibility with utf8mb4 encoding

```javascript
members: {
    email: {
        type: 'string', 
        maxlength: 191, 
        nullable: false, 
        unique: true,
        validations: {isEmail: true}
    }
}
```

### Import Behavior

During CSV imports:
- Ghost **does not deduplicate** automatically when importing
- Duplicate email attempts result in database constraint errors
- Ghost logs the error but continues processing remaining members
- Existing members are never updated by import - if a CSV contains an email that already exists, that row is skipped

After deletion:
- Since Ghost uses hard deletion, the unique constraint is removed immediately
- The same email address can be reused immediately to create a new member
- If the original member had a Stripe customer ID and was deleted without canceling subscriptions, the new member can be linked to a different Stripe customer

### SQLite Case Sensitivity Edge Case

In SQLite environments (typically used in development):
- Emails like `Name@Google.com` and `name@google.com` can both be created
- This is because SQLite doesn't enforce case-insensitive uniqueness by default
- Production databases (MySQL/PostgreSQL) correctly treat these as duplicates

### Error Handling for Duplicates

When encountering email duplicates through the Admin API:
- The response will be a 500 Internal Server Error
- Error message typically indicates a database constraint violation
- No specific "duplicate email" error is returned to indicate the specific issue

```javascript
// Example error response for duplicate email
{
  "errors": [{
    "message": "ER_DUP_ENTRY: Duplicate entry 'user@example.com' for key 'members_email_unique'",
    "errorType": "ValidationError"
  }]
}
```

### Best Practices

To prevent duplicate email issues:
1. Always check if an email exists before creating a new member
2. Use the email lookup option in the Read Single Member endpoint
3. For imports, clean your CSV data to remove duplicates before uploading
4. When migrating from other systems, consider handling existing emails explicitly

```javascript
// Check if member exists before creating
const existingMember = await api.members.read({
  email: 'user@example.com'
});

if (existingMember) {
  // Update existing member instead of creating duplicate
  await api.members.edit({
    id: existingMember.id,
    name: 'Updated Name'
  });
} else {
  // Create new member
  await api.members.add({
    email: 'user@example.com',
    name: 'New User'
  });
}
```

## Email Bounce Handling

Ghost immediately suppresses email delivery for hard bounces and spam complaints. The `email_disabled` flag only blocks email sending - it doesn't affect content access, subscriptions, or authentication. All suppressed emails can be re-enabled.

### Bounce Detection

When a hard bounce occurs:
- `email_disabled` is set to `true`
- An entry is added to the `suppressions` table with `reason='bounce'`
- The event is logged in `email_recipients` for analytics

## Newsletter Subscription vs Member Status

Ghost separates newsletter subscriptions from membership status, allowing independent management of communication preferences and content access.

### Architecture

- Newsletter subscriptions are managed through the `members_newsletters` junction table
- Each subscription links a `member_id` to a `newsletter_id`
- A member can subscribe to multiple newsletters independently

### Key Behaviors

- Unsubscribing from newsletters doesn't change membership status or content access
- Paid members who unsubscribe continue being charged and maintain full site access
- Email delivery and content access are independent systems
- Newsletter preferences persist when payment status changes

### unsubscribe URLs
```
/unsubscribe/?uuid={member_uuid}&newsletter={newsletter_uuid}
```

These UUID-based links work without authentication and allow granular unsubscription from specific newsletters. See [issue #12492](https://github.com/TryGhost/Ghost/issues/12492) for more on unsubscribe behavior.

## Re-subscription Workflows

All email-disabled states are reversible through:

1. **Member Portal** - Self-service re-subscription through `/#/portal/account`
2. **Admin Panel** - Direct management of member subscriptions
3. **API Updates** - Programmatic re-enabling

```javascript
PUT /ghost/api/admin/members/:id
Body: {
  "members": [{
    "id": "member-id",
    "newsletters": [{"id": "newsletter-id"}],
    "email_disabled": false
  }]
}
```

The magic link endpoint can re-enable emails during authentication:

```javascript
POST /members/api/send-magic-link/
Body: {
  "email": "user@example.com",
  "emailType": "subscribe"  // Combines login with newsletter opt-in
}
```

Email suppression is managed by the [email-suppression-list package](https://github.com/TryGhost/Ghost/tree/main/ghost/packages/email-suppression-list).

## Payment and Newsletter Subscription Separation

Ghost maintains separate systems for payment subscriptions and newsletter preferences, allowing independent management.

### Independence

- Newsletter subscriptions don't affect Stripe billing or membership status
- Canceling a paid subscription doesn't change newsletter preferences
- Members retain content access based on their tier regardless of email preferences

### Edge Cases

**Member deletion with active Stripe subscriptions:**
- Without `?cancel=true`, Ghost deletes the member but leaves Stripe subscriptions active
- This creates orphaned subscriptions that continue billing customers who no longer exist in Ghost
- Use `cancel=true` to properly clean up Stripe subscriptions before deletion

**Bulk deletion limitations:**
- Bulk operations never cancel Stripe subscriptions
- Subscription cancellation must be done individually

**Multiple subscriptions:**
- Members with multiple active subscriptions may receive duplicate newsletters

### Database Separation

The separation is reflected in the database schema:
- `members_newsletters` table tracks email preferences
- `members_stripe_customers_subscriptions` table tracks payment subscriptions
- No foreign key relationships exist between these tables
- This architectural separation allows independent management of both systems

### API Behavior

When working with the API:

```javascript
// Cancel a Stripe subscription without affecting newsletter preferences
await ghostAdminApi.subscriptions.edit({
  subscription_id: 'sub_123456',
  status: 'canceled'
});

// Unsubscribe from all newsletters without affecting payment status
await ghostAdminApi.members.edit({
  member_id: 'member_123',
  newsletters: []  // Empty array unsubscribes from all
});

// Delete a member and cancel their subscription
await ghostAdminApi.members.delete({
  id: 'member_123',
  cancel: true  // Critical for avoiding orphaned Stripe subscriptions
});
```

### Best Practices

- Always check for active Stripe subscriptions before deletion
- Use `cancel=true` when deleting members who might have active billing
- Remember that newsletter unsubscribe pages should not offer to cancel paid subscriptions
- Consider building a member recovery process that handles both email and subscription states separately

See [issue #12150](https://github.com/TryGhost/Ghost/issues/12150) for details on `cancelStripeSubscriptions` handling.

## Check Active Stripe Subscriptions

**Determines if any members have active Stripe subscriptions.**

### Endpoint Details

**HTTP Method**: `GET`  
**Path**: `/ghost/api/admin/members/hasActiveStripeSubscriptions/`  
**Purpose**: Used by Ghost Admin to determine if Stripe integration is actively used

### Response Structure

```json
{
  "hasActiveStripeSubscriptions": true
}
```

### Response Fields

- `hasActiveStripeSubscriptions` (boolean) - True if any member has active Stripe subscription

### Example Request

```javascript
const result = await membersService.api.hasActiveStripeSubscriptions();
// Returns: { hasActiveStripeSubscriptions: boolean }
```

### Use Cases

- Checking before disconnecting Stripe integration
- Determining if paid membership features are in use
- Migration planning

## Bulk Import Members

**Imports multiple members via CSV file upload.**

### Endpoint Details

**HTTP Method**: `POST`  
**Path**: `/ghost/api/admin/members/upload/`  
**Content-Type**: `multipart/form-data`  
**Status Code**: `201 Created`

### Form Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `membersfile` | file | Yes | CSV file containing member data |
| `mapping[email]` | string | Yes | "email" - CSV column mapping |
| `mapping[name]` | string | No | "name" - CSV column mapping |
| `mapping[note]` | string | No | "note" - CSV column mapping |
| `mapping[subscribed_to_emails]` | string | No | "subscribed_to_emails" - CSV column mapping |
| `mapping[complimentary_plan]` | string | No | "complimentary_plan" - CSV column mapping |
| `mapping[stripe_customer_id]` | string | No | "stripe_customer_id" - CSV column mapping |
| `mapping[created_at]` | string | No | "created_at" - CSV column mapping |
| `mapping[labels]` | string | No | "labels" - CSV column mapping |

### CSV Format

**Required Column**:
- `email` - Member email address

**Optional Columns**:
- `name` - Member name
- `note` - Admin notes
- `subscribed_to_emails` - Boolean or true/false string
- `complimentary_plan` - Boolean for complimentary access
- `stripe_customer_id` - Stripe customer ID to link
- `labels` - Comma-separated label names
- `created_at` - ISO 8601 date for backdated records

### CSV Example

```csv
email,name,note,subscribed_to_emails,labels,created_at
user1@example.com,John Doe,Early adopter,true,VIP,2025-01-01T00:00:00.000Z
user2@example.com,Jane Smith,Beta tester,true,"Premium,Newsletter",2025-01-15T00:00:00.000Z
user3@example.com,Bob Wilson,,false,Trial,2025-02-01T00:00:00.000Z
```

### Response Structure

```json
{
  "meta": {
    "stats": {
      "imported": 150,
      "invalid": 5,
      "duplicates": 3
    },
    "import_label": {
      "name": "Import 2025-11-16"
    },
    "errors": [
      {
        "message": "Validation failed",
        "context": "Invalid email format",
        "help": "Row 23: user@invalid"
      }
    ]
  }
}
```

### Import Behavior

1. **Validation**: Each row validated for email format and required fields
2. **Duplicate Handling**: Existing emails skipped or updated based on configuration
3. **Label Creation**: New labels automatically created if they don't exist
4. **Auto-Labeling**: All imported members tagged with import timestamp label
5. **Stripe Linking**: If `stripe_customer_id` provided, member linked to Stripe customer
6. **Backdating**: `created_at` allows importing historical member data

### Processing

Import happens asynchronously:
- File uploaded and validated immediately
- Members processed in batches in background
- Response includes immediate validation errors
- Full results available after processing completes

### Limitations

- Maximum file size varies by hosting (typically 5-10 MB)
- Large imports (>10,000 members) may take several minutes
- Email validation performed server-side
- Invalid rows logged but don't stop the import

CSV import is handled by the [members-importer](https://github.com/TryGhost/Ghost/tree/main/ghost/packages/members-importer) and [members-csv](https://github.com/TryGhost/Ghost/tree/main/ghost/packages/members-csv) packages.

## Query Language (NQL) Reference

Ghost uses NQL (Ghost Query Language) for filtering members across browse endpoints.

### Basic Syntax

```
property:operator-value
```

### Operators

| Operator | Symbol | Example | Description |
|----------|--------|---------|-------------|
| Equals | `:` or `=` | `status:free` | Exact match |
| Not equals | `-` | `status:-paid` | Negation |
| Greater than | `>` | `email_open_rate:>50` | Numeric comparison |
| Greater or equal | `>=` | `email_count:>=10` | Numeric comparison |
| Less than | `<` | `created_at:<'2025-01-01'` | Numeric/date comparison |
| Less or equal | `<=` | `email_opened_count:<=5` | Numeric comparison |
| Contains | `~` | `name:~'John'` | Substring match |
| Starts with | `~^` | `email:~^'admin'` | Prefix match |
| In list | `[...]` | `status:[free,paid]` | Match any value |

### Combinators

- **AND**: `+` - All conditions must be true
- **OR**: `,` - At least one condition must be true  
- **Grouping**: `()` - Override operator precedence

### Filterable Properties

**Core Properties**:
- `id`, `uuid`, `email`, `name`, `note`, `status`, `expertise`

**Engagement Metrics**:
- `email_count`, `email_opened_count`, `email_open_rate`
- `email_disabled`, `enable_comment_notifications`
- `last_seen_at`, `last_commented_at`

**Relationships**:
- `label`, `labels.slug`, `labels.name`
- `newsletters`, `newsletters.slug`, `newsletters.name`
- `tier`, `tier.slug`, `products.slug`
- `subscriptions.status`, `subscriptions.start_date`

**Dates**:
- `created_at`, `updated_at`

### Filter Examples

```javascript
// Single property
filter: 'status:paid'

// Negation
filter: 'status:-free'

// Multiple values (OR)
filter: 'status:[paid,comped]'

// Numeric comparison
filter: 'email_open_rate:>50'

// Date comparison
filter: "created_at:>'2025-01-01'"

// AND combination
filter: 'status:paid+label:vip'

// OR combination
filter: 'status:free,status:comped'

// Complex with grouping
filter: '(status:paid,status:comped)+email_disabled:false+label:newsletter'

// Contains search
filter: "name:~'John'"

// Multiple conditions
filter: "status:paid+email_open_rate:>0.5+label:vip+created_at:>'2024-01-01'"

// Newsletter subscription
filter: 'newsletters.slug:weekly-digest'

// Label filter
filter: 'label:[vip,premium,early-adopter]'

// Email with special characters (requires quotes)
filter: "email:'user+test@example.com'"
```

### Important Notes

1. **URL Encoding**: All filters must be URL encoded in direct HTTP requests
2. **Special Characters**: Wrap values containing `+`, `@`, spaces in single quotes
3. **Date Format**: Use ISO 8601 format: `YYYY-MM-DDTHH:mm:ss.sssZ`
4. **Case Sensitivity**: Property names are case-insensitive; values are case-sensitive
5. **JavaScript SDK**: Automatically handles encoding

Query parsing is handled by the [NQL package](https://github.com/TryGhost/Ghost/tree/main/ghost/packages/nql).

## Member Model Complete Schema

Comprehensive field reference from the [member model](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/models/member.js) and [database schema](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/data/schema/schema.js). See [issue #12493](https://github.com/TryGhost/Ghost/issues/12493) for event table preservation and [issue #11557](https://github.com/TryGhost/Ghost/issues/11557) for Stripe customer deletion handling.

### Primary Table: members

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| **id** | varchar(24) | PRIMARY KEY, NOT NULL | Unique member identifier |
| **uuid** | varchar(36) | UNIQUE, NULL | Universal unique identifier |
| **email** | varchar(191) | UNIQUE, NOT NULL | Member email address |
| **name** | varchar(191) | NULL | Member full name |
| **note** | varchar(2000) | NULL | Admin notes about member |
| **expertise** | varchar(191) | NULL | Member expertise/profession |
| **geolocation** | varchar(2000) | NULL | Geographic location JSON |
| **status** | varchar(50) | NOT NULL, DEFAULT 'free' | Membership status |
| **transient_id** | varchar(191) | NULL | Temporary identifier |
| **email_count** | int unsigned | NOT NULL, DEFAULT 0 | Total emails sent |
| **email_opened_count** | int unsigned | NOT NULL, DEFAULT 0 | Total emails opened |
| **email_open_rate** | int unsigned | NULL | Open rate percentage |
| **email_disabled** | tinyint(1) | NOT NULL, DEFAULT 0 | Email delivery disabled flag |
| **enable_comment_notifications** | tinyint(1) | NOT NULL, DEFAULT 1 | Comment notification preference |
| **last_seen_at** | datetime | NULL | Last activity timestamp |
| **last_commented_at** | datetime | NULL | Last comment timestamp |
| **created_at** | datetime | NOT NULL | Creation timestamp |
| **created_by** | varchar(24) | NULL | Creator user ID |
| **updated_at** | datetime | NULL | Last update timestamp |
| **updated_by** | varchar(24) | NULL | Last updater user ID |

#### Important Notes

**Hard Deletion**
Ghost performs true hard deletion - database rows are completely removed with no soft-delete mechanism. After deletion, the same email can be immediately reused.

**Email Disabled Field**
The `email_disabled` flag prevents email delivery only. It doesn't affect content access or subscriptions and can be reversed when the email issue is resolved.

### Related Tables

**members_labels** (many-to-many):
- `id` (PK), `member_id` (FK), `label_id` (FK), `sort_order`

**members_newsletters** (many-to-many, introduced in Ghost 4.44+):
- `id` (PK), `member_id` (FK), `newsletter_id` (FK)
- Manages newsletter subscriptions independently from member status
- Unsubscribing removes rows from this table but doesn't change member record
- Allows granular control over newsletter preferences without affecting content access

**members_products** (many-to-many):
- `id` (PK), `member_id` (FK), `product_id` (FK), `sort_order`, `expiry_at`

**members_stripe_customers**:
- `id` (PK), `member_id` (FK, UNIQUE), `customer_id` (Stripe ID, UNIQUE), `email`, `name`

**members_stripe_customers_subscriptions**:
- `id` (PK), `customer_id` (FK), `subscription_id`, `stripe_price_id`
- `status`, `plan_id`, `plan_nickname`, `plan_interval`, `plan_amount`, `plan_currency`
- `start_date`, `current_period_end`, `cancel_at_period_end`, `cancellation_reason`

**suppressions** (from @tryghost/email-suppression-list package):
- `email_address` - The suppressed email
- `email_id` - ID of email that caused suppression
- `reason` - 'bounce' or 'spam'
- `created_at` - Timestamp of suppression event

**Event Tables**:
- `members_login_events`, `members_email_change_events`, `members_status_events`
- `members_paid_subscription_events`, `members_payment_events`
- `members_subscribe_events`, `members_unsubscribe_events`, `members_click_events`

### Status Values

- `free` - Free member with no paid access
- `paid` - Member with active paid subscription
- `comped` - Member with complimentary paid access

See [issue #12259](https://github.com/TryGhost/Ghost/issues/12259) for details on multiple subscription email duplication.
