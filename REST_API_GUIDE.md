# Minitrino REST API Guide

The Minitrino REST API provides HTTP endpoints for cluster management operations, offering the same functionality as the CLI commands through web requests.

## Installation

To use the REST API server, install the optional server dependencies:

```bash
pip install minitrino[server]
```

Or install the dependencies manually:

```bash
pip install fastapi>=0.104.0 pydantic>=2.0.0 uvicorn[standard]>=0.24.0
```

## Starting the Server

Start the REST API server using the `minitrino server` command:

```bash
# Start server on default host/port (127.0.0.1:8000)
minitrino server

# Start server on custom host/port
minitrino server --host 0.0.0.0 --port 8080

# Start with auto-reload for development
minitrino server --reload
```

## API Documentation

Once the server is running, you can access:

- **Interactive API Documentation**: http://127.0.0.1:8000/docs
- **Alternative API Documentation**: http://127.0.0.1:8000/redoc
- **OpenAPI Schema**: http://127.0.0.1:8000/openapi.json

## Available Endpoints

### Health Check

```http
GET /health
```

Returns server health status.

**Response:**
```json
{
  "status": "healthy",
  "service": "minitrino-api"
}
```

### Provision Cluster

```http
POST /provision
```

Provision a Minitrino cluster with optional modules.

**Request Body:**
```json
{
  "modules": ["postgres", "mysql"],
  "image": "trino",
  "workers": 2,
  "no_rollback": false,
  "cluster_name": "my-cluster"
}
```

**Request Parameters:**
- `modules` (array, optional): List of modules to provision. Default: `[]`
- `image` (string, optional): Cluster image type (`trino` or `starburst`). Default: `"trino"`
- `workers` (integer, optional): Number of workers to provision. Default: `0`
- `no_rollback` (boolean, optional): Disable rollback on failure. Default: `false`
- `cluster_name` (string, optional): Name for the cluster. Default: `"default"`

**Success Response (200):**
```json
{
  "success": true,
  "message": "Successfully provisioned cluster 'my-cluster'",
  "cluster_name": "my-cluster",
  "modules": ["postgres", "mysql"],
  "image": "trino",
  "workers": 2
}
```

**Error Response (400/500):**
```json
{
  "success": false,
  "error": "Error message",
  "details": "Additional error details (optional)"
}
```

## Usage Examples

### Using curl

```bash
# Basic cluster provision
curl -X POST "http://127.0.0.1:8000/provision" \
  -H "Content-Type: application/json" \
  -d '{}'

# Provision with modules
curl -X POST "http://127.0.0.1:8000/provision" \
  -H "Content-Type: application/json" \
  -d '{
    "modules": ["postgres", "mysql"],
    "image": "trino",
    "workers": 1,
    "cluster_name": "test-cluster"
  }'

# Health check
curl http://127.0.0.1:8000/health
```

### Using Python requests

```python
import requests

# Basic provision
response = requests.post("http://127.0.0.1:8000/provision")
print(response.json())

# Provision with configuration
payload = {
    "modules": ["postgres"],
    "image": "trino",
    "workers": 2,
    "cluster_name": "my-cluster"
}

response = requests.post(
    "http://127.0.0.1:8000/provision",
    json=payload
)

if response.status_code == 200:
    result = response.json()
    print(f"Cluster '{result['cluster_name']}' provisioned successfully!")
else:
    error = response.json()
    print(f"Error: {error['error']}")
```

### Using JavaScript (fetch)

```javascript
// Basic provision
fetch('http://127.0.0.1:8000/provision', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({})
})
.then(response => response.json())
.then(data => console.log(data));

// Provision with configuration
const payload = {
  modules: ['postgres', 'mysql'],
  image: 'trino',
  workers: 1,
  cluster_name: 'webapp-cluster'
};

fetch('http://127.0.0.1:8000/provision', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(payload)
})
.then(response => response.json())
.then(data => {
  if (data.success) {
    console.log(`Cluster '${data.cluster_name}' provisioned successfully!`);
  } else {
    console.error(`Error: ${data.error}`);
  }
});
```

## CLI Equivalent Commands

The REST API endpoints correspond to CLI commands:

| REST API | CLI Command |
|----------|-------------|
| `POST /provision` | `minitrino provision` |

For example:
```bash
# CLI command
minitrino provision --module postgres --module mysql --image trino --workers 2 --cluster my-cluster

# Equivalent REST API call
curl -X POST "http://127.0.0.1:8000/provision" \
  -H "Content-Type: application/json" \
  -d '{
    "modules": ["postgres", "mysql"],
    "image": "trino", 
    "workers": 2,
    "cluster_name": "my-cluster"
  }'
```

## Error Handling

The API returns appropriate HTTP status codes:

- **200**: Success
- **400**: Client error (invalid parameters, user errors)
- **500**: Server error (internal Minitrino errors)

Error responses include:
- `success`: Always `false` for errors
- `error`: Primary error message
- `details`: Additional error information (when available)

## Logging

Server logs are controlled by the same logging options as the CLI:

```bash
# Debug logging
minitrino --verbose server

# Custom log level
minitrino --log-level DEBUG server
```

The API server logs will show request details and any errors that occur during cluster operations.
