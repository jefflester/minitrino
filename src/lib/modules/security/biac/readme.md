# Built-in Access Control (BIAC) Module

This module configures Trino to enable the built-in access control (BIAC) system
integrated with the SEP web UI.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module biac  

## Accessing Roles and Privileges in the SEP UI  

Standalone BIAC:  

- Open a web browser and go to [http://localhost:8080](http://localhost:8080)
  (or [https://localhost:8443](hhttps://localhost:8443) if TLS is configured)
- Log in using an authorized sysadmin user (`admin` or `starburst_service`)
- Click on the username in the top right corner > switch role > `sysadmin`

Once the `sysadmin` role has been assumed, you can begin to create roles and
grant various privileges.

## Using the SEP REST API with BIAC

You can manage BIAC entities and their actions via the SEP REST API (BIAC
endpoints are of the form `/api/v1/biac/...`). See the list of available
endpoints and methods in our [API
Documentation](https://docs.starburst.io/latest/api/index.html#api-_).  

### Example 1: List Roles  

    curl -k --location \
      -X GET 'http://localhost:8080/api/v1/biac/roles' \
      -H 'Accept: application/json' \
      -H 'Content-Type: application/json' \
      -H 'X-Trino-Role: system=ROLE{sysadmin}' \
      -u 'admin:'  

### Example 2: Adding a User to Authorized Users  

The following API POST request adds user `Alice` to authorized users. After
performing the following successfully, Alice will be able to access BIAC
features in the SEP UI.

    curl -k --location \
      -X POST 'http://localhost:8080/api/v1/biac/subjects/users/alice/assignments' \
      -H 'Accept: application/json' \
      -H 'Content-Type: application/json' \
      -H 'X-Trino-Role: system=ROLE{sysadmin}' \
      -u 'admin:' \
      -d '{ "roleId":"-2", "roleAdmin":"true"}'

### Example 3: Get Role Assignments for a Role

The following API GET request returns users/groups assigned to the `sysadmin`
role which is defined by `roleId=-1`.  

    curl -k --location \
      -X GET 'http://localhost:8080/api/v1/biac/roles/-2/assignments?pageToken=&pageSize=&pageSort=' \
      -H 'Accept: application/json' \
      -H 'Content-Type: application/json' \
      -H 'X-Trino-Role: system=ROLE{sysadmin}' \
      -u 'admin:'

### Example 4: Create a Role

    curl -k --location \
      -X POST 'http://localhost:8080/api/v1/biac/roles' \
      -H 'Accept: application/json' \
      -H 'Content-Type: application/json' \
      -H 'X-Trino-Role: system=ROLE{sysadmin}' \
      -u 'admin:' \
      -d '{ "name": "test_role", "description":"test creating new BIAC role"}'
