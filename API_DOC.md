Here's the API documentation in a single markdown format:

# Jarvoice API Documentation

## Base URL
`http://your-api-domain.com`

## Endpoints

### Users

#### `POST /users`
Create a new user.

**Request Body**
```json
{
  "email": "user@example.com",
  "name": "John Doe",
  "phone_number": "+12345678900"
}
```

**Response** (200 OK)
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "name": "John Doe",
  "phone_number": "+12345678900",
  "created_at": "2024-03-20T10:00:00Z",
  "updated_at": "2024-03-20T10:00:00Z"
}
```

#### `GET /users/{user_id}`
Get user details.

**Response** (200 OK)
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "name": "John Doe",
  "phone_number": "+12345678900",
  "created_at": "2024-03-20T10:00:00Z",
  "updated_at": "2024-03-20T10:00:00Z"
}
```

### Tasks

#### `POST /tasks`
Create a new task.

**Request Body**
```json
{
  "title": "Complete project presentation",
  "description": "Prepare slides for quarterly review",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "PENDING",
  "priority": "HIGH",
  "due_date": "2024-03-25T15:00:00Z",
  "reminder_time": "2024-03-25T14:00:00Z"
}
```

**Response** (200 OK)
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174001",
  "title": "Complete project presentation",
  "description": "Prepare slides for quarterly review",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "PENDING",
  "priority": "HIGH",
  "due_date": "2024-03-25T15:00:00Z",
  "reminder_time": "2024-03-25T14:00:00Z",
  "reminder_sent": false,
  "created_at": "2024-03-20T10:00:00Z",
  "updated_at": "2024-03-20T10:00:00Z"
}
```

#### `GET /tasks`
Get tasks for a user.

**Query Parameters**
- `user_id` (required): UUID
- `status` (optional): "PENDING" | "IN_PROGRESS" | "COMPLETED" | "CANCELED"
- `due_after` (optional): ISO datetime
- `due_before` (optional): ISO datetime

**Response** (200 OK)
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174001",
    "title": "Complete project presentation",
    "description": "Prepare slides for quarterly review",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "status": "PENDING",
    "priority": "HIGH",
    "due_date": "2024-03-25T15:00:00Z",
    "reminder_time": "2024-03-25T14:00:00Z",
    "reminder_sent": false,
    "created_at": "2024-03-20T10:00:00Z",
    "updated_at": "2024-03-20T10:00:00Z"
  }
]
```

#### `PATCH /tasks/{task_id}`
Update a task.

**Request Body**
```json
{
  "title": "Updated title",
  "status": "IN_PROGRESS",
  "reminder_time": "2024-03-25T13:00:00Z"
}
```

**Response** (200 OK)
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174001",
  "title": "Updated title",
  "description": "Prepare slides for quarterly review",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "IN_PROGRESS",
  "priority": "HIGH",
  "due_date": "2024-03-25T15:00:00Z",
  "reminder_time": "2024-03-25T13:00:00Z",
  "reminder_sent": false,
  "created_at": "2024-03-20T10:00:00Z",
  "updated_at": "2024-03-20T11:00:00Z"
}
```

### Contacts

#### `POST /contacts`
Create a new contact.

**Request Body**
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Jane Smith",
  "phone_number": "+12345678901",
  "email": "jane@example.com",
  "relationship": "Colleague"
}
```

**Response** (200 OK)
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174002",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Jane Smith",
  "phone_number": "+12345678901",
  "email": "jane@example.com",
  "relationship": "Colleague",
  "created_at": "2024-03-20T10:00:00Z",
  "updated_at": "2024-03-20T10:00:00Z"
}
```

#### `GET /contacts`
Get contacts for a user.

**Query Parameters**
- `user_id` (required): UUID

**Response** (200 OK)
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174002",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Jane Smith",
    "phone_number": "+12345678901",
    "email": "jane@example.com",
    "relationship": "Colleague",
    "created_at": "2024-03-20T10:00:00Z",
    "updated_at": "2024-03-20T10:00:00Z"
  }
]
```

#### `GET /contacts/{contact_id}`
Get a single contact.

#### `PATCH /contacts/{contact_id}`
Update a contact.

**Request Body**
```json
{
  "name": "Jane Smith-Jones",
  "relationship": "Friend"
}
```

#### `DELETE /contacts/{contact_id}`
Delete a contact.

**Response** (200 OK)
```json
{
  "message": "Contact deleted successfully"
}
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "An internal server error occurred"
}
```

## Data Types

### Task Status
- `PENDING`
- `IN_PROGRESS`
- `COMPLETED`
- `CANCELED`

### Task Priority
- `LOW`
- `MEDIUM`
- `HIGH`

## Important Notes

1. All dates are in ISO 8601 format and UTC timezone
2. All IDs are UUID v4 format
3. Phone numbers must be in E.164 format (e.g., "+12345678900")
4. All string enums (status, priority) are case-sensitive
5. No pagination implemented yet
6. All endpoints require proper authentication headers