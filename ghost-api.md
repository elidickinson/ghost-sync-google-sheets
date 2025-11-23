# Ghost Admin API Reference

Ghost Admin API provides comprehensive content and site management through RESTful endpoints with JWT authentication and NQL filtering support.

**Official Documentation**: [https://docs.ghost.org/admin-api/](https://docs.ghost.org/admin-api/)

## Authentication

**Base URL**: `https://{admin_domain}/ghost/api/admin/`

**Required Headers**:
- `Authorization: Ghost {JWT_TOKEN}` - JWT signed with Admin API key
- `Accept-Version: v6.0` - API version
- `Content-Type: application/json` - For POST/PUT requests

**JWT Structure**: Token must include API key ID (`kid`), audience `/admin/`, signed with hex-decoded API secret. Expires after 5 minutes.

## Members

**Official Docs**: [https://docs.ghost.org/admin-api/members/overview](https://docs.ghost.org/admin-api/members/overview)

`GET|POST|PUT|DELETE /ghost/api/admin/members/`

### Browse Members

`GET /ghost/api/admin/members/`
`api.members.browse(options)`

**Query Parameters**: `limit`, `page`, `filter`, `order`, `search`, `fields`, `include`

**Include**: `email_recipients`, `products`, `tiers`

**Defaults**: Returns 15 newest members by default

**Response** (all fields always returned):
```json
{
  "members": [{
    "id": "member_id",
    "uuid": "uuid-string",
    "email": "user@example.com",
    "name": "Member Name",
    "note": "Optional notes",
    "geolocation": "{\"country\":\"US\",\"timezone\":\"America/New_York\"}",
    "subscribed": true,
    "created_at": "2025-01-01T12:00:00.000Z",
    "updated_at": "2025-11-15T12:00:00.000Z",
    "labels": [],
    "subscriptions": [],
    "avatar_image": "https://www.gravatar.com/avatar/...",
    "comped": false,
    "email_count": 15,
    "email_opened_count": 8,
    "email_open_rate": 53,
    "status": "free",
    "last_seen_at": "2025-11-15T12:00:00.000Z",
    "unsubscribe_url": "https://example.com/unsubscribe/...",
    "email_suppression": {
      "suppressed": false,
      "info": null
    },
    "newsletters": []
  }],
  "meta": {"pagination": {"page": 1, "limit": 15, "pages": 10, "total": 150}}
}
```

**Important**: The relationships `labels`, `newsletters`, and `subscriptions` are ALWAYS included. Computed fields `avatar_image`, `comped`, `subscribed`, `unsubscribe_url`, and `email_suppression` are also always returned. **Note**: `attribution` is NOT included in browse responses - it is only returned when reading a single member. Use `include=tiers` (or `include=products`) to get tier data. Use `include=email_recipients` to get email recipient records.

**Example with populated relationships**:
```json
{
  "id": "member_id",
  "uuid": "uuid-string",
  "email": "user@example.com",
  "name": "Member Name",
  "note": "Optional notes",
  "geolocation": "{\"country\":\"US\",\"timezone\":\"America/New_York\"}",
  "subscribed": true,
  "created_at": "2025-01-01T12:00:00.000Z",
  "updated_at": "2025-11-15T12:00:00.000Z",
  "labels": [
    {
      "id": "label_id",
      "name": "VIP",
      "slug": "vip",
      "created_at": "2025-01-01T12:00:00.000Z",
      "updated_at": "2025-01-10T12:00:00.000Z"
    }
  ],
  "subscriptions": [
    {
      "id": "sub_stripe_id",
      "customer": {
        "id": "cus_stripe_id",
        "name": "Member Name",
        "email": "user@example.com"
      },
      "plan": {
        "id": "plan_id",
        "nickname": "Monthly",
        "amount": 500,
        "interval": "month",
        "currency": "USD"
      },
      "status": "active",
      "start_date": "2025-01-01T12:00:00.000Z",
      "default_payment_card_last4": "4242",
      "cancel_at_period_end": false,
      "cancellation_reason": null,
      "current_period_end": "2026-01-01T12:00:00.000Z",
      "trial_start_at": null,
      "trial_end_at": null,
      "price": {
        "id": "price_stripe_id",
        "price_id": "price_id",
        "nickname": "Premium Monthly",
        "amount": 1000,
        "interval": "month",
        "type": "recurring",
        "currency": "USD",
        "tier": {
          "id": "stripe_product_id",
          "name": "Premium",
          "tier_id": "tier_id"
        }
      },
      "tier": {
        "id": "tier_id",
        "name": "Premium",
        "slug": "premium",
        "active": true,
        "welcome_page_url": null,
        "visibility": "public",
        "trial_days": 0,
        "description": "Premium tier",
        "type": "paid",
        "currency": "usd",
        "monthly_price": 1000,
        "yearly_price": 10000,
        "monthly_price_id": "price_monthly_id",
        "yearly_price_id": "price_yearly_id",
        "created_at": "2025-01-01T12:00:00.000Z",
        "updated_at": "2025-01-10T12:00:00.000Z",
        "expiry_at": "2026-01-01T00:00:00.000Z"
      },
      "offer": {
        "id": "offer_id",
        "name": "Black Friday Sale",
        "code": "BLACKFRIDAY",
        "display_title": "Black Friday 50% Off",
        "display_description": "Get 50% off for 3 months",
        "type": "percent",
        "cadence": "month",
        "amount": 50,
        "duration": "repeating",
        "duration_in_months": 3,
        "currency_restriction": false,
        "currency": null,
        "status": "active",
        "redemption_count": 42,
        "tier": {
          "id": "tier_id",
          "name": "Premium"
        },
        "created_at": "2025-01-01T12:00:00.000Z",
        "last_redeemed": "2025-11-15T10:30:00.000Z"
      }
    }
  ],
  "avatar_image": "https://www.gravatar.com/avatar/...",
  "comped": false,
  "email_count": 50,
  "email_opened_count": 35,
  "email_open_rate": 70,
  "status": "paid",
  "last_seen_at": "2025-11-15T12:00:00.000Z",
  "unsubscribe_url": "https://example.com/unsubscribe/...",
  "email_suppression": {
    "suppressed": false,
    "info": null
  },
  "newsletters": [
    {
      "id": "newsletter_id",
      "name": "Weekly Digest",
      "description": "Weekly newsletter",
      "status": "active"
    }
  ],
  "tiers": [
    {
      "id": "tier_id",
      "name": "Premium",
      "slug": "premium",
      "active": true,
      "welcome_page_url": null,
      "visibility": "public",
      "trial_days": 0,
      "description": "Premium tier",
      "type": "paid",
      "currency": "usd",
      "monthly_price": 1000,
      "yearly_price": 10000,
      "monthly_price_id": "price_monthly_id",
      "yearly_price_id": "price_yearly_id",
      "created_at": "2025-01-01T12:00:00.000Z",
      "updated_at": "2025-01-10T12:00:00.000Z",
      "expiry_at": "2026-01-01T00:00:00.000Z"
    }
  ]
}
```

**Relationship field details**:
- `labels`: Always included. Fields: id, name, slug, created_at, updated_at
- `subscriptions`: Always included. Custom serialization with nested objects:
  - Root fields: id, status, start_date, default_payment_card_last4, cancel_at_period_end, cancellation_reason, current_period_end, trial_start_at, trial_end_at, customer, plan, price, tier, offer
  - `customer`: id, name, email
  - `plan`: id, nickname, amount, interval, currency
  - `price`: id, price_id, nickname, amount, interval, type, currency, tier
    - `price.tier`: id, name, tier_id
  - `tier`: Full tier/product object (id, name, slug, active, welcome_page_url, visibility, trial_days, description, type, currency, monthly_price, yearly_price, monthly_price_id, yearly_price_id, created_at, updated_at, expiry_at) - **Source**: `MemberBREADService.js:124-127` sets `subscription.tier` to product from `member.products`
  - `offer`: Offer object or null (id, name, code, display_title, display_description, type, cadence, amount, duration, duration_in_months, currency_restriction, currency, status, redemption_count, tier, created_at, last_redeemed) - **Source**: `MemberBREADService.js:167-177` `attachOffersToSubscriptions()` called in both read() and browse()
- `newsletters`: Always included. Fields: id, name, description, status (only active newsletters)
- `tiers`: Included via `include=tiers` or `include=products`. Fields: id, name, slug, active, welcome_page_url, visibility, trial_days, description, type, currency, monthly_price, yearly_price, monthly_price_id, yearly_price_id, created_at, updated_at, expiry_at
- `email_recipients`: Only included via `include=email_recipients`. Array of objects with fields: id, member_id, batch_id, processed_at, delivered_at, opened_at, failed_at, member_uuid, member_email, member_name, plus nested `email` object containing: id, post_id, uuid, status, recipient_filter, error, error_data, email_count, csd_email_count, delivered_count, opened_count, failed_count, subject, from, reply_to, html, plaintext, source, source_type, track_opens, track_clicks, feedback_enabled, submitted_at, newsletter_id, created_at, updated_at

### Read Single Member

`GET /ghost/api/admin/members/{id}/`
`api.members.read({id}|{email})`

**Query By**: `id` or `email`

**Include**: `email_recipients`, `products`, `tiers`

```javascript
await api.members.read({id: 'member_id'});
await api.members.read({email: 'user@example.com'});
await api.members.read({id: 'member_id', include: 'tiers,email_recipients'});
```

**Differences from Browse**:
- **Includes attribution data**: Member-level `attribution` field is populated, and each subscription includes an `attribution` field
  - Member attribution shows signup source (e.g., post/page that converted them)
  - Subscription attribution shows source for each subscription signup
  - Attribution fields: `id`, `type`, `url`, `title`, `referrer_source`, `referrer_medium`, `referrer_url`
  - **Source**: `MemberBREADService.js:244` calls `attachAttributionsToMember()` ONLY in `read()` method, NOT in `browse()` (lines 378-442). Attribution lookups require expensive database queries unsuitable for bulk operations.
- No pagination `meta` object in response
- No `filter`, `limit`, `page`, `order`, `search`, or `fields` parameters
- Must query by exact `id` or `email`
- Still wrapped in `members` array

**Example response showing attribution**:
```json
{
  "members": [{
    "id": "member_id",
    "email": "user@example.com",
    "attribution": {
      "id": "post_id",
      "type": "post",
      "url": "/welcome-post/",
      "title": "Welcome Post",
      "referrer_source": "Google",
      "referrer_medium": "organic",
      "referrer_url": "https://google.com/search?q=example"
    },
    "subscriptions": [{
      "id": "sub_id",
      "status": "active",
      "attribution": {
        "id": "post_id",
        "type": "post",
        "url": "/premium-offer/",
        "title": "Premium Offer",
        "referrer_source": "Twitter",
        "referrer_medium": "social",
        "referrer_url": "https://twitter.com/example"
      }
    }]
  }]
}
```

### Create Member

`POST /ghost/api/admin/members/` (201)
`api.members.add(data, options)`

**Required**: `email`

**Optional**: `name`, `note`, `labels`, `newsletters`, `tiers`, `stripe_customer_id`, `comped`

**Query Parameters**: `send_email` (boolean), `email_type` (signin|signup|subscribe)

```json
{
  "members": [{
    "email": "new@example.com",
    "name": "New Member",
    "labels": [{"name": "VIP"}, "Early Adopter"],
    "newsletters": [{"id": "newsletter_id"}],
    "tiers": [{"id": "tier_id", "expiry_at": "2026-01-01T00:00:00.000Z"}]
  }]
}
```

**Special Behaviors**:
- **Stripe Integration**: Links member to Stripe customer, imports subscriptions
- **Magic Link**: `send_email=true` sends passwordless login
- **Status**: Auto-set to `paid` if active subscriptions, `comped` if complimentary, else `free`
- **Labels**: Auto-created if names don't exist

### Update Member

`PUT /ghost/api/admin/members/{id}/` (200)
`api.members.edit(data)`

**Required**: `id`

**Updatable**: `email`, `name`, `note`, `labels` (full replacement), `newsletters`, `comped`

**Cannot Update**: `stripe_customer_id`, `subscriptions`, `tiers` (except via `comped`), `created_at`, `status`

```json
{
  "members": [{
    "id": "member_id",
    "name": "Updated Name",
    "labels": [{"name": "Premium"}, "Active"]
  }]
}
```

### Logout Member

`PUT /ghost/api/admin/members/{id}/logout/` (204)

**Required**: `id`

Clears member session.

### Edit Subscription

`PUT /ghost/api/admin/members/{id}/subscriptions/{subscription_id}/`

**Required**: `id`, `subscription_id`, `cancel_at_period_end`

**Optional**: `status` (values: `canceled`)

```json
{
  "cancel_at_period_end": true
}
```

```javascript
// Cancel subscription
await api.members.editSubscription({
  id: 'member_id',
  subscription_id: 'sub_id',
  status: 'canceled'
});

// Update cancel_at_period_end
await api.members.editSubscription({
  id: 'member_id',
  subscription_id: 'sub_id',
  cancel_at_period_end: false
});
```

### Create Subscription

`POST /ghost/api/admin/members/{id}/subscriptions/` (200)

**Required**: `id`, `stripe_price_id`

```json
{
  "stripe_price_id": "price_1234567890"
}
```

Creates new Stripe subscription for member.

### Delete Member

`DELETE /ghost/api/admin/members/{id}/` (204)
`api.members.delete({id, cancel})`

**Parameters**: `id`, `cancel` (boolean - cancel Stripe subscriptions first)

**Hard deletion** - permanently removes database row (no soft-delete). Event tables preserved for analytics.

**Without `cancel`**: Leaves Stripe subscriptions active (orphaned)
**With `cancel=true`**: Cancels Stripe subscriptions then deletes

### Bulk Destroy Members

`DELETE /ghost/api/admin/members/bulk/` (200)

**Required**: `filter` or `search` or `all`

```javascript
await api.members.bulkDestroy({
  filter: 'status:free+created_at:<\'2024-01-01\''
});
```

**Response**:
```json
{
  "meta": {
    "stats": {
      "successful": 100,
      "unsuccessful": 5
    },
    "unsuccessfulIds": ["id1", "id2"],
    "errors": [...]
  }
}
```

**Note**: Never cancels Stripe subscriptions (must be done individually).

### Bulk Edit Members

`PUT /ghost/api/admin/members/bulk/` (200)

**Required**: `filter` or `search` or `all`, `action`

**Actions**: `unsubscribe`, `addLabel`, `removeLabel`

```javascript
await api.members.bulkEdit({
  action: 'addLabel',
  meta: {label: {id: 'label_id'}},
  filter: 'status:paid'
});
```

### Export Members CSV

`GET /ghost/api/admin/members/export/`

**Query Parameters**: `limit`, `filter`, `search`

Returns CSV file with filename `members.{date}.csv`.

### Import Members CSV

`POST /ghost/api/admin/members/upload/` (201/202)

**Content-Type**: `multipart/form-data`

**Form Fields**: `membersfile`, `mapping`, `labels`

**CSV Columns**: `email` (required), `name`, `note`, `subscribed_to_emails`, `complimentary_plan`, `stripe_customer_id`, `labels`, `created_at`

**Response**:
```json
{
  "meta": {
    "stats": {"imported": 150, "invalid": 5, "duplicates": 3},
    "import_label": {"name": "Import 2025-11-16"},
    "errors": [...]
  }
}
```

**Important**: CSV imports do NOT trigger `member.added` webhooks.

### Member Stats

`GET /ghost/api/admin/members/stats/`

**Response**:
```json
{
  "resource": "members",
  "total": 1500,
  "data": [{
    "date": "2025-01-01",
    "paid": 100,
    "free": 400,
    "comped": 10
  }]
}
```

Returns member counts by status over time.

### MRR Stats

`GET /ghost/api/admin/members/stats/mrr/`

**Response**:
```json
{
  "resource": "mrr",
  "data": [{
    "currency": "usd",
    "data": [{
      "date": "2025-01-01",
      "value": 5000
    }]
  }]
}
```

Returns monthly recurring revenue by currency.

### Activity Feed

`GET /ghost/api/admin/members/events/`

**Query Parameters**: `limit`, `filter`

Returns member event timeline (logins, subscriptions, email events, etc.).

### Duplicate Email Handling

- **Unique constraint**: Enforced at database (191 char max)
- **Duplicate creation**: Returns 500 error with `ER_DUP_ENTRY`
- **Import behavior**: Skips duplicates, doesn't update existing
- **After deletion**: Email immediately reusable (hard deletion)

**Best Practice**:
```javascript
const existing = await api.members.read({email: 'user@example.com'}).catch(() => null);
if (existing) {
  await api.members.edit({id: existing.id, name: 'Updated'});
} else {
  await api.members.add({email: 'user@example.com', name: 'New'});
}
```

## Posts

**Official Docs**: [https://docs.ghost.org/admin-api/posts/overview](https://docs.ghost.org/admin-api/posts/overview)

`GET|POST|PUT|DELETE /ghost/api/admin/posts/`

### Browse Posts

`GET /ghost/api/admin/posts/`
`api.posts.browse(options)`

**Query Parameters**: `limit`, `page`, `filter`, `order`, `fields`, `formats`, `collection`, `absolute_urls`, `include`

**Include**: `tags`, `authors`, `authors.roles`, `email`, `tiers`, `newsletter`, `count.conversions`, `count.signups`, `count.paid_conversions`, `count.clicks`, `sentiment`, `count.positive_feedback`, `count.negative_feedback`, `post_revisions`, `post_revisions.author`

**Formats**: `html`, `mobiledoc`, `lexical`, `plaintext` (default: `html`)

**Note**: Official docs state default format is Lexical, but source code shows `html` is the default. Tags, authors, and author roles are automatically included.

**Response** (with all fields):
```json
{
  "posts": [{
    "id": "post_id",
    "uuid": "uuid-string",
    "title": "Post Title",
    "slug": "post-slug",
    "html": "<p>HTML content</p>",
    "comment_id": "comment-id",
    "feature_image": "https://example.com/image.jpg",
    "feature_image_alt": "Alt text",
    "feature_image_caption": "Caption text",
    "featured": false,
    "status": "published",
    "locale": null,
    "visibility": "public",
    "email_segment": "all",
    "created_at": "2025-01-01T12:00:00.000Z",
    "updated_at": "2025-01-15T12:00:00.000Z",
    "published_at": "2025-01-15T12:00:00.000Z",
    "published_by": "user_id",
    "custom_excerpt": "Custom excerpt text",
    "codeinjection_head": null,
    "codeinjection_foot": null,
    "custom_template": null,
    "canonical_url": null,
    "newsletter_id": "newsletter_id",
    "show_title_and_feature_image": true,
    "url": "https://example.com/post-slug/",
    "excerpt": "Excerpt text",
    "reading_time": 5,
    "access": true,
    "og_image": null,
    "og_title": null,
    "og_description": null,
    "twitter_image": null,
    "twitter_title": null,
    "twitter_description": null,
    "meta_title": null,
    "meta_description": null,
    "email_subject": null,
    "frontmatter": null,
    "email_only": false,
    "tags": [],
    "authors": [],
    "primary_tag": null,
    "primary_author": null,
    "tiers": []
  }],
  "meta": {"pagination": {"page": 1, "limit": 15, "pages": 10, "total": 150}}
}
```

**Notes**:
- Format fields (`html`, `lexical`, `mobiledoc`, `plaintext`) controlled by `formats` param (default: `html` only)
- `email_recipient_filter` renamed to `email_segment` in API response
- `primary_tag` and `primary_author` are computed from first tag/author
- posts_meta fields (`og_*`, `twitter_*`, `meta_*`, `email_subject`, `feature_image_alt`, `feature_image_caption`, `email_only`, `frontmatter`) flattened to root level
- `excerpt` and `reading_time` are computed fields
- `access` indicates whether current user/member can access full content

**With relationships included** (`include=tags,authors,email,newsletter,tiers`):
```json
{
  "tags": [{
    "id": "tag_id",
    "name": "News",
    "slug": "news",
    "description": "News articles",
    "feature_image": null,
    "visibility": "public",
    "og_image": null,
    "og_title": null,
    "og_description": null,
    "twitter_image": null,
    "twitter_title": null,
    "twitter_description": null,
    "meta_title": null,
    "meta_description": null,
    "codeinjection_head": null,
    "codeinjection_foot": null,
    "canonical_url": null,
    "accent_color": null,
    "created_at": "2025-01-01T12:00:00.000Z",
    "updated_at": "2025-01-10T12:00:00.000Z",
    "url": "https://example.com/tag/news/"
  }],
  "authors": [{
    "id": "user_id",
    "name": "Author Name",
    "slug": "author-name",
    "email": "author@example.com",
    "profile_image": "https://example.com/profile.jpg",
    "cover_image": null,
    "bio": "Author bio",
    "website": "https://example.com",
    "location": "San Francisco",
    "facebook": null,
    "twitter": "@author",
    "accessibility": null,
    "status": "active",
    "locale": null,
    "created_at": "2025-01-01T12:00:00.000Z",
    "updated_at": "2025-01-10T12:00:00.000Z",
    "url": "https://example.com/author/author-name/"
  }],
  "email": {
    "id": "email_id",
    "post_id": "post_id",
    "uuid": "email-uuid",
    "status": "submitted",
    "recipient_filter": "all",
    "error": null,
    "error_data": null,
    "email_count": 1000,
    "delivered_count": 995,
    "opened_count": 450,
    "failed_count": 5,
    "subject": "Post Title",
    "from": "\"Author Name\" <noreply@example.com>",
    "reply_to": "author@example.com",
    "html": "<html>...</html>",
    "plaintext": "Plain text version",
    "track_opens": true,
    "track_clicks": true,
    "feedback_enabled": false,
    "submitted_at": "2025-01-15T12:00:00.000Z",
    "newsletter_id": "newsletter_id",
    "created_at": "2025-01-15T12:00:00.000Z",
    "updated_at": "2025-01-15T12:05:00.000Z"
  },
  "newsletter": {
    "id": "newsletter_id",
    "uuid": "newsletter-uuid",
    "name": "Weekly Digest",
    "slug": "weekly-digest",
    "status": "active"
  },
  "tiers": [{
    "id": "tier_id",
    "name": "Premium",
    "slug": "premium",
    "active": true,
    "welcome_page_url": null,
    "visibility": "public",
    "trial_days": 0,
    "description": "Premium tier",
    "type": "paid",
    "currency": "usd",
    "monthly_price": 1000,
    "yearly_price": 10000,
    "created_at": "2025-01-01T12:00:00.000Z",
    "updated_at": "2025-01-10T12:00:00.000Z"
  }]
}
```

### Read Single Post

`GET /ghost/api/admin/posts/{id}/`
`api.posts.read({id}|{slug}|{uuid})`

### Create Post

`POST /ghost/api/admin/posts/` (201)
`api.posts.add(data, options)`

**Required**: `title`

**Optional**: `slug`, `html`, `lexical`, `mobiledoc`, `feature_image`, `featured`, `status`, `visibility`, `published_at`, `tags`, `authors`, `tiers`, `excerpt`, `meta_title`, `meta_description`, `og_*`, `twitter_*`, `newsletter_id`

**Query Parameters**: `source` (values: `html`), `formats`, `include`

**Status Values**: `draft` (default), `published`, `scheduled`, `sent`

**Visibility Values**: `public` (default), `members`, `paid`, `tiers`

```json
{
  "posts": [{
    "title": "New Post",
    "lexical": "{\"root\":{\"children\":[{\"type\":\"paragraph\",\"children\":[{\"type\":\"text\",\"text\":\"Content\"}]}]}}",
    "status": "published",
    "visibility": "public",
    "tags": ["News", "Updates"],
    "authors": [{email: "author@example.com"}]
  }]
}
```

**Special Behaviors**:
- **Tag creation**: Non-existent tags auto-created
- **Author fallback**: If no match, defaults to owner
- **HTML conversion**: `?source=html` converts HTML to Lexical (lossy)
- **Scheduling**: Must be >= 2 minutes in future for `scheduled` status
- **Email sending**: Triggered on `status: published` with newsletter

### Update Post

`PUT /ghost/api/admin/posts/{id}/` (200)
`api.posts.edit(data)`

**Required**: `id`

**Query Parameters**: `email_segment`, `newsletter`, `force_rerender`, `save_revision`, `convert_to_lexical`, `source`, `formats`, `include`

### Delete Post

`DELETE /ghost/api/admin/posts/{id}/` (204)

### Bulk Edit Posts

`PUT /ghost/api/admin/posts/bulk/` (200)

**Required**: `filter`, `action`

```javascript
await api.posts.bulkEdit({
  action: 'unpublish',
  filter: 'status:published+tag:outdated'
});
```

### Bulk Destroy Posts

`DELETE /ghost/api/admin/posts/bulk/` (200)

**Required**: `filter`

```javascript
await api.posts.bulkDestroy({
  filter: 'status:draft+created_at:<\'2024-01-01\''
});
```

### Copy Post

`POST /ghost/api/admin/posts/{id}/copy/` (201)

Duplicates post, creates new draft with "(Copy)" appended to title.

### Export Post Analytics

`GET /ghost/api/admin/posts/export/`

**Query Parameters**: `limit`, `filter`, `order`

Returns CSV file with post analytics, filename `post-analytics.{date}.csv`.

## Pages

**Official Docs**: [https://docs.ghost.org/admin-api/pages/overview](https://docs.ghost.org/admin-api/pages/overview)

`GET|POST|PUT|DELETE /ghost/api/admin/pages/`

Pages use identical operations as Posts but with `type: page` and different allowed includes.

**Include**: `tags`, `authors`, `authors.roles`, `tiers`, `count.signups`, `count.paid_conversions`, `post_revisions`, `post_revisions.author`

**Differences from Posts**:
- No `email`, `newsletter`, `count.clicks`, `sentiment`, `count.positive_feedback`, `count.negative_feedback` includes
- No `newsletter_id` field
- No email sending on publish
- No `sent` status
- Operations: browse, read, add, edit, bulkEdit, bulkDestroy, destroy, copy

## Tags

`GET|POST|PUT|DELETE /ghost/api/admin/tags/`

### Browse Tags

`GET /ghost/api/admin/tags/`

**Query Parameters**: `limit`, `page`, `filter`, `order`, `fields`, `include`

**Include**: `count.posts`

**Response**:
```json
{
  "tags": [{
    "id": "tag_id",
    "name": "Technology",
    "slug": "technology",
    "description": "Tech-related posts",
    "feature_image": null,
    "visibility": "public",
    "og_image": null,
    "og_title": null,
    "og_description": null,
    "twitter_image": null,
    "twitter_title": null,
    "twitter_description": null,
    "meta_title": null,
    "meta_description": null,
    "codeinjection_head": null,
    "codeinjection_foot": null,
    "canonical_url": null,
    "accent_color": null,
    "created_at": "2025-01-01T12:00:00.000Z",
    "updated_at": "2025-01-10T12:00:00.000Z",
    "url": "https://example.com/tag/technology/"
  }],
  "meta": {"pagination": {"page": 1, "limit": 15, "pages": 5, "total": 75}}
}
```

**With count.posts**:
```json
{
  "tags": [{
    "id": "tag_id",
    "name": "Technology",
    "slug": "technology",
    ...
    "count": {"posts": 42},
    "url": "https://example.com/tag/technology/"
  }]
}
```

### Read Single Tag

`GET /ghost/api/admin/tags/{id}/`

**Parameters**: `id`, `slug`, or `visibility`

### Create Tag

`POST /ghost/api/admin/tags/` (201)

**Required**: `name`

**Optional**: `slug`, `description`, `feature_image`, `visibility` (public|internal), `meta_title`, `meta_description`, `og_image`, `twitter_image`, `accent_color`

### Update Tag

`PUT /ghost/api/admin/tags/{id}/` (200)

**Required**: `id`

### Delete Tag

`DELETE /ghost/api/admin/tags/{id}/` (204)

Removes tag from all associated posts.

## Labels

`GET|POST|PUT|DELETE /ghost/api/admin/labels/`

### Browse Labels

`GET /ghost/api/admin/labels/`

**Query Parameters**: `limit`, `page`, `filter`, `order`, `fields`, `include`

**Include**: `count.members`

**Response**:
```json
{
  "labels": [{
    "id": "label_id",
    "name": "VIP",
    "slug": "vip",
    "created_at": "2025-01-01T12:00:00.000Z",
    "updated_at": "2025-01-10T12:00:00.000Z"
  }],
  "meta": {"pagination": {"page": 1, "limit": 15, "pages": 2, "total": 30}}
}
```

**With count.members**:
```json
{
  "labels": [{
    "id": "label_id",
    "name": "VIP",
    "slug": "vip",
    "count": {"members": 150},
    "created_at": "2025-01-01T12:00:00.000Z",
    "updated_at": "2025-01-10T12:00:00.000Z"
  }]
}
```

### Read Single Label

`GET /ghost/api/admin/labels/{id}/`

**Parameters**: `id`, `slug`

### Create Label

`POST /ghost/api/admin/labels/` (201)

**Required**: `name`

**Optional**: `slug`, `description`

```json
{
  "labels": [{
    "name": "VIP",
    "slug": "vip"
  }]
}
```

### Update Label

`PUT /ghost/api/admin/labels/{id}/` (200)

### Delete Label

`DELETE /ghost/api/admin/labels/{id}/` (204)

## Tiers

**Official Docs**: [https://docs.ghost.org/admin-api/tiers/overview](https://docs.ghost.org/admin-api/tiers/overview)

`GET|POST|PUT /ghost/api/admin/tiers/`

### Browse Tiers

`GET /ghost/api/admin/tiers/`

**Query Parameters**: `limit`, `page`, `filter`, `order`, `fields`, `include`

**Include**: `monthly_price`, `yearly_price`, `benefits`

**Filter**: `type:free|paid`, `visibility:public|none`, `active:true|false`

**Response**:
```json
{
  "tiers": [{
    "id": "tier_id",
    "name": "Premium",
    "description": "Premium membership",
    "slug": "premium",
    "active": true,
    "type": "paid",
    "welcome_page_url": null,
    "created_at": "2025-01-01T12:00:00.000Z",
    "updated_at": "2025-01-10T12:00:00.000Z",
    "visibility": "public",
    "benefits": [
      {
        "id": "benefit_id",
        "name": "Ad-free experience",
        "slug": "ad-free-experience",
        "created_at": "2025-01-01T12:00:00.000Z",
        "updated_at": "2025-01-01T12:00:00.000Z"
      }
    ],
    "currency": "usd",
    "monthly_price": 500,
    "yearly_price": 5000,
    "trial_days": 0
  }],
  "meta": {"pagination": {"page": 1, "limit": 15, "pages": 1, "total": 3}}
}
```

**Free tier response**:
```json
{
  "id": "tier_id",
  "name": "Free",
  "description": "Free membership",
  "slug": "free",
  "active": true,
  "type": "free",
  "welcome_page_url": null,
  "created_at": "2025-01-01T12:00:00.000Z",
  "updated_at": "2025-01-10T12:00:00.000Z",
  "visibility": "public",
  "benefits": null,
  "trial_days": 0
}
```

**Notes**:
- `active` is transformed from `status === 'active'`
- Free tiers exclude `currency`, `monthly_price`, `yearly_price` fields
- `benefits` is an array of benefit objects or null
- Official docs state `benefits`, `monthly_price`, `yearly_price` require `include` parameter, but source code shows they're always returned
- Tiers are ordered by ascending monthly price by default

### Read Single Tier

`GET /ghost/api/admin/tiers/{id}/`

### Create Tier

`POST /ghost/api/admin/tiers/` (201)

**Required**: `name`

**Optional**: `slug`, `type` (paid|free), `monthly_price`, `yearly_price`, `currency`, `trial_days`, `benefits`

```json
{
  "tiers": [{
    "name": "Gold",
    "type": "paid",
    "monthly_price": 999,
    "yearly_price": 9990,
    "currency": "usd",
    "benefits": ["Ad-free", "Premium content"]
  }]
}
```

### Update Tier

`PUT /ghost/api/admin/tiers/{id}/` (200)

**Required**: `id`

**Note**: Cannot change `type` after creation.

## Newsletters

**Official Docs**: [https://docs.ghost.org/admin-api/newsletters/overview](https://docs.ghost.org/admin-api/newsletters/overview)

`GET|POST|PUT /ghost/api/admin/newsletters/`

### Browse Newsletters

`GET /ghost/api/admin/newsletters/`

**Query Parameters**: `limit`, `page`, `filter`, `order`, `fields`, `include`

**Include**: `count.posts`, `count.members`, `count.active_members`

**Note**: Each site has one newsletter by default. `sender_reply_to` accepts `newsletter` or `support`.

**Response**:
```json
{
  "newsletters": [{
    "id": "newsletter_id",
    "uuid": "uuid-string",
    "name": "Weekly Digest",
    "slug": "weekly-digest",
    "description": "Our weekly newsletter",
    "sender_name": "Ghost Team",
    "sender_email": "hello@example.com",
    "sender_reply_to": "newsletter",
    "status": "active",
    "visibility": "members",
    "subscribe_on_signup": true,
    "sort_order": 0,
    "header_image": null,
    "show_header_icon": true,
    "show_header_title": true,
    "show_header_name": true,
    "show_excerpt": false,
    "title_font_category": "sans_serif",
    "title_alignment": "center",
    "title_font_weight": "bold",
    "show_feature_image": true,
    "body_font_category": "sans_serif",
    "footer_content": null,
    "show_badge": true,
    "show_post_title_section": true,
    "show_comment_cta": true,
    "show_subscription_details": false,
    "show_latest_posts": false,
    "background_color": "light",
    "button_corners": "rounded",
    "button_style": "fill",
    "button_color": "accent",
    "link_style": "underline",
    "link_color": "accent",
    "image_corners": "square",
    "header_background_color": "transparent",
    "feedback_enabled": false,
    "created_at": "2025-01-01T12:00:00.000Z",
    "updated_at": "2025-01-10T12:00:00.000Z"
  }],
  "meta": {"pagination": {"page": 1, "limit": 15, "pages": 1, "total": 2}}
}
```

### Read Single Newsletter

`GET /ghost/api/admin/newsletters/{id}/`

**Parameters**: `id`, `slug`, or `uuid`

### Create Newsletter

`POST /ghost/api/admin/newsletters/` (201)

**Required**: `name`

**Optional**: `slug`, `sender_name`, `sender_email`, `description`, `status` (active|archived), `subscribe_on_signup`, `title_font_category`, `body_font_category`, `show_badge`, `footer_content`

**Query Parameters**: `opt_in_existing` (boolean - subscribe existing members)

### Update Newsletter

`PUT /ghost/api/admin/newsletters/{id}/` (200)

**Required**: `id`

### Verify Property Update

`PUT /ghost/api/admin/newsletters/verifications/`

**Required**: `token`

Used to verify sender email changes.

## Webhooks

`POST|PUT|DELETE /ghost/api/admin/webhooks/`

**Note**: No browse or read operations available.

### Create Webhook

`POST /ghost/api/admin/webhooks/` (201)

**Required**: `event`, `target_url`

**Optional**: `name`, `secret`, `api_version`

**Available Events** (31 total):
- `site.changed`
- `post.added`, `post.deleted`, `post.edited`, `post.published`, `post.published.edited`, `post.unpublished`, `post.scheduled`, `post.unscheduled`, `post.rescheduled`
- `page.added`, `page.deleted`, `page.edited`, `page.published`, `page.published.edited`, `page.unpublished`, `page.scheduled`, `page.unscheduled`, `page.rescheduled`
- `tag.added`, `tag.edited`, `tag.deleted`, `post.tag.attached`, `post.tag.detached`, `page.tag.attached`, `page.tag.detached`
- `member.added`, `member.edited`, `member.deleted`

```json
{
  "webhooks": [{
    "event": "post.published",
    "target_url": "https://example.com/webhook",
    "name": "Post Publish Notifier",
    "secret": "webhook_secret",
    "api_version": "v6.0"
  }]
}
```

**Response after creation**:
```json
{
  "webhooks": [{
    "id": "webhook_id",
    "event": "post.published",
    "target_url": "https://example.com/webhook",
    "name": "Post Publish Notifier",
    "secret": "webhook_secret",
    "api_version": "v6.0",
    "integration_id": "integration_id",
    "status": "available",
    "last_triggered_at": null,
    "last_triggered_status": null,
    "last_triggered_error": null,
    "created_at": "2025-01-01T12:00:00.000Z",
    "updated_at": "2025-01-01T12:00:00.000Z"
  }]
}
```

### Update Webhook

`PUT /ghost/api/admin/webhooks/{id}/` (200)

**Required**: `id`

**Editable**: `name`, `event`, `target_url`, `secret`, `api_version`

**Permission**: Can only edit webhooks owned by authenticated integration.

### Delete Webhook

`DELETE /ghost/api/admin/webhooks/{id}/` (204)

**Permission**: Can only delete webhooks owned by authenticated integration.

## Images & Media

### Upload Image

`POST /ghost/api/admin/images/upload/` (201)

**Content-Type**: `multipart/form-data`
**Form Fields**: `file`

**Response**:
```json
{
  "images": [{
    "url": "https://example.com/content/images/2025/01/image.jpg",
    "ref": "image_reference"
  }]
}
```

Auto-optimization, resizing, original stored with `_o` suffix. Supports JPG, PNG, WebP, GIF.

### Upload Media

`POST /ghost/api/admin/media/upload/` (201)

For video/audio files.

### Upload Files

`POST /ghost/api/admin/files/upload/` (201)

For non-image/media files (PDFs, documents, etc.).

## Site & Settings

### Get Site Info

`GET /ghost/api/admin/site/`

**Response** (not wrapped in array):
```json
{
  "site": {
    "title": "My Ghost Site",
    "description": "Thoughts, stories and ideas",
    "logo": "https://example.com/logo.png",
    "accent_color": "#FF1A75",
    "url": "https://example.com",
    "version": "5.75.0"
  }
}
```

### Get Settings

`GET /ghost/api/admin/settings/`

**Response** (not wrapped in array):
```json
{
  "settings": [
    {"key": "title", "value": "My Ghost Site"},
    {"key": "description", "value": "Thoughts, stories and ideas"},
    {"key": "timezone", "value": "Etc/UTC"},
    {"key": "default_content_visibility", "value": "public"}
  ]
}
```

### Update Settings

`PUT /ghost/api/admin/settings/`

```json
{
  "settings": [
    {"key": "title", "value": "New Site Title"},
    {"key": "description", "value": "New description"}
  ]
}
```

## Users

`GET /ghost/api/admin/users/`

### Browse Users

`GET /ghost/api/admin/users/`

**Query Parameters**: `limit`, `page`, `filter`, `order`, `fields`, `include`

**Include**: `count.posts`, `roles`

**Response**:
```json
{
  "users": [{
    "id": "user_id",
    "name": "User Name",
    "slug": "user-name",
    "email": "user@example.com",
    "profile_image": "https://example.com/image.jpg",
    "bio": "Bio text",
    "status": "active",
    "roles": [{"id": "role_id", "name": "Author"}]
  }]
}
```

### Read Single User

`GET /ghost/api/admin/users/{id}/`

**Parameters**: `id`, `slug`, or `email`

**Note**: User creation, updates, deletion typically done through Ghost Admin UI for security.

## NQL Filter Reference

Ghost uses NQL (Ghost Query Language) for filtering across all browse endpoints.

### Syntax
```
property:operator-value
```

### Operators

| Operator | Symbol | Example |
|----------|--------|---------|
| Equals | `:` | `status:published` |
| Not equals | `-` | `status:-draft` |
| Greater than | `>` | `created_at:>'2024-01-01'` |
| Less than | `<` | `published_at:<'2025-01-01'` |
| Contains | `~` | `title:~'tutorial'` |
| In list | `[...]` | `status:[published,scheduled]` |

### Combinators

- **AND**: `+`
- **OR**: `,`
- **Grouping**: `()`

### Examples

```javascript
// Posts by tag
filter: 'tag:news'

// Published posts from 2024
filter: 'status:published+published_at:>\'2024-01-01\'+published_at:<\'2025-01-01\''

// Featured or paid content
filter: 'featured:true,visibility:paid'

// Complex filtering
filter: '(status:published,status:scheduled)+tag:[news,updates]+featured:true'

// Members: paid with high engagement
filter: 'status:paid+email_open_rate:>50+label:vip'
```

## Database Schema

### members table

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | varchar(24) | PK | Member identifier |
| `uuid` | varchar(36) | UNIQUE | Universal ID |
| `email` | varchar(191) | UNIQUE, NOT NULL | Email address |
| `name` | varchar(191) | NULL | Full name |
| `note` | varchar(2000) | NULL | Admin notes |
| `status` | varchar(50) | DEFAULT 'free' | free/paid/comped |
| `email_count` | int unsigned | DEFAULT 0 | Emails sent |
| `email_opened_count` | int unsigned | DEFAULT 0 | Emails opened |
| `email_open_rate` | int unsigned | NULL | Open rate % |
| `email_disabled` | tinyint(1) | DEFAULT 0 | Delivery disabled |
| `last_seen_at` | datetime | NULL | Last activity |
| `created_at` | datetime | NOT NULL | Creation timestamp |
| `updated_at` | datetime | NULL | Update timestamp |

### posts table

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | varchar(24) | PK | Post identifier |
| `uuid` | varchar(36) | UNIQUE | Universal ID |
| `title` | varchar(2000) | NOT NULL | Post title |
| `slug` | varchar(191) | UNIQUE (with type) | URL slug |
| `html` | longtext | NULL | HTML content |
| `lexical` | longtext | NULL | Lexical JSON |
| `mobiledoc` | longtext | NULL | MobileDoc JSON (deprecated) |
| `feature_image` | varchar(2000) | NULL | Featured image URL |
| `featured` | tinyint(1) | DEFAULT 0 | Featured flag |
| `status` | varchar(50) | DEFAULT 'draft' | draft/published/scheduled/sent |
| `visibility` | varchar(50) | DEFAULT 'public' | public/members/paid/tiers |
| `type` | varchar(50) | DEFAULT 'post' | post/page |
| `newsletter_id` | varchar(24) | FK | Newsletter reference |
| `published_at` | datetime | NULL | Publication date |
| `created_at` | datetime | NOT NULL | Creation timestamp |
| `updated_at` | datetime | NULL | Update timestamp |

### tags table

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | varchar(24) | PK | Tag identifier |
| `name` | varchar(191) | NOT NULL | Tag name |
| `slug` | varchar(191) | UNIQUE | URL slug |
| `description` | varchar(500) | NULL | Tag description |
| `visibility` | varchar(50) | DEFAULT 'public' | public/internal |

### labels table

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | varchar(24) | PK | Label identifier |
| `name` | varchar(191) | UNIQUE | Label name |
| `slug` | varchar(191) | UNIQUE | URL slug |
| `description` | varchar(500) | NULL | Label description |

### products (tiers) table

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | varchar(24) | PK | Tier identifier |
| `name` | varchar(191) | NOT NULL | Tier name |
| `slug` | varchar(191) | UNIQUE | URL slug |
| `type` | varchar(50) | DEFAULT 'paid' | paid/free |
| `monthly_price` | int | NULL | Monthly price (cents) |
| `yearly_price` | int | NULL | Yearly price (cents) |
| `currency` | varchar(50) | NULL | Currency code |
| `trial_days` | int unsigned | DEFAULT 0 | Trial period |

### newsletters table

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | varchar(24) | PK | Newsletter identifier |
| `uuid` | varchar(36) | UNIQUE | Universal ID |
| `name` | varchar(191) | UNIQUE | Newsletter name |
| `slug` | varchar(191) | UNIQUE | URL slug |
| `sender_name` | varchar(191) | NULL | Sender name |
| `sender_email` | varchar(191) | NULL | Sender email |
| `status` | varchar(50) | DEFAULT 'active' | active/archived |
| `subscribe_on_signup` | tinyint(1) | DEFAULT 1 | Auto-subscribe new members |

### webhooks table

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | varchar(24) | PK | Webhook identifier |
| `event` | varchar(50) | NOT NULL | Event name |
| `target_url` | varchar(2000) | NOT NULL | Webhook URL |
| `name` | varchar(191) | NULL | Webhook name |
| `secret` | varchar(191) | NULL | Webhook secret |
| `api_version` | varchar(50) | DEFAULT 'v2' | API version |
| `integration_id` | varchar(24) | FK | Integration reference |
| `last_triggered_at` | datetime | NULL | Last trigger time |

## API Serialization Architecture

Understanding what the Ghost Admin API actually returns requires examining **two layers of transformation**:

### 1. Model Layer (`/models/*.js`)

The Bookshelf models define `toJSON()` or `serialize()` methods that transform database records into JSON.

**Example - Member Model** (`member.js:393-406`):
- Adds computed `avatar_image` field from Gravatar
- Returns all database fields by default

**Example - StripeCustomerSubscription Model** (`stripe-customer-subscription.js:19-69`):
- Performs major restructuring of flat database structure
- Transforms into nested objects: `customer`, `plan`, `price` with nested `tier`
- Renames fields (e.g., `subscription_id` → `id`)

### 2. Output Serializer Layer (`/api/endpoints/utils/serializers/output/*.js`)

The API serializers perform final transformation before sending the response.

**Example - Member Serializer** (`serializers/output/members.js:154-219`):
- Explicitly picks which fields to include in response
- Adds computed fields: `comped` (from status), `subscribed` (from newsletters array)
- Adds `attribution`, `unsubscribe_url`, `email_suppression`
- Renames `products` → `tiers` in response

**Example - Newsletter Serializer** (`serializers/output/members.js:385-394`):
- Newsletter model returns all ~32 database fields
- Serializer filters to only 4 fields: `id`, `name`, `description`, `status`
- Only includes active newsletters, sorted by `sort_order`

### Data Flow

```
Database Record
    ↓
Bookshelf Model (with relationships loaded)
    ↓
model.toJSON() or model.serialize()
    ↓
Output Serializer (serializeMember, etc.)
    ↓
Final API Response
```

### Key Implications

1. **Database schema ≠ API response**: Not all database fields are returned
2. **Model methods matter**: Check both model files AND serializers
3. **Relationships vary**: Each relationship type may be serialized differently
4. **Computed fields**: Some fields don't exist in database (e.g., `avatar_image`, `comped`, `subscribed`)

### Where to Look

To determine exact API response structure:
1. Check model's `toJSON()` or `serialize()` method in `/models/{resource}.js`
2. Check output serializer in `/api/endpoints/utils/serializers/output/{resource}.js`
3. For relationships, check both the related model AND how the parent serializer handles it

## References

**Official Documentation**:
- [Ghost Admin API](https://docs.ghost.org/admin-api/) - Main documentation
- [Members](https://docs.ghost.org/admin-api/members/overview) | [Posts](https://docs.ghost.org/admin-api/posts/overview) | [Pages](https://docs.ghost.org/admin-api/pages/overview)
- [Tiers](https://docs.ghost.org/admin-api/tiers/overview) | [Newsletters](https://docs.ghost.org/admin-api/newsletters/overview)
- [JavaScript SDK](https://docs.ghost.org/admin-api/javascript/)

**Ghost Source Code** (validated against v6.0):
- **Endpoints**: [members.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/api/endpoints/members.js) | [posts.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/api/endpoints/posts.js) | [pages.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/api/endpoints/pages.js) | [tags.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/api/endpoints/tags.js) | [labels.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/api/endpoints/labels.js) | [tiers.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/api/endpoints/tiers.js) | [newsletters.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/api/endpoints/newsletters.js) | [webhooks.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/api/endpoints/webhooks.js)
- **Models**: [member.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/models/member.js) | [post.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/models/post.js) | [tag.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/models/tag.js) | [label.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/models/label.js) | [newsletter.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/models/newsletter.js) | [product.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/models/product.js) | [stripe-customer-subscription.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/models/stripe-customer-subscription.js) | [webhook.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/models/webhook.js)
- **Serializers**: [members.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/api/endpoints/utils/serializers/output/members.js) | [posts.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/api/endpoints/utils/serializers/output/posts.js) | [tiers.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/api/endpoints/utils/serializers/output/tiers.js)
- **Mappers**: [posts.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/api/endpoints/utils/serializers/output/mappers/posts.js) | [tags.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/api/endpoints/utils/serializers/output/mappers/tags.js) | [users.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/api/endpoints/utils/serializers/output/mappers/users.js) | [emails.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/api/endpoints/utils/serializers/output/mappers/emails.js)
- **Schema**: [schema.js](https://github.com/TryGhost/Ghost/blob/main/ghost/core/core/server/data/schema/schema.js)
