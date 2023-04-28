# Built-in Access Control (BIAC) Module

This module configures Trino to enable the built-in access control (BIAC) system
integrated with the SEP web UI.  

This module can be used in conjunction with the `password-file` and `ldap`
security modules to provide usernames.  

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module biac  

### Usage with Delta Lake or Hive modules  

Additional configuration is required for use of BIAC with the `Delta Lake` and
`Hive` object storage catalogs.  

**Delta Lake**: Add the following property to `delta.properties`:

    delta.security=starburst

**Hive**: Add the following property to `hive.properties`:  

    hive.security=starburst

## Accessing Roles and Privileges in the SEP UI  

Standalone BIAC:  
- Open a web browser and go to [http://localhost:8080](http://localhost:8080)
- Sign in using a username for an authorized user (Default: `admin`,
  `starburst_service`)
- Click on your username in the top right corner > switch role > `sysadmin`  

BIAC with `password-file` or `ldap` module:  
- Open a web browser and go to [https://localhost:8443](https://localhost:8443)  
- Have the browser accept the self-signed certificate:  
  - **Chrome**: Click anywhere on the page and type `thisisunsafe`
  - **Firefox**: Click on the Advanced button and then click on **Accept the
    Risk and Continue**.
  - **Safari**: Click on the button **Show Details** and then click the link
    **visit this website**.
- Sign in using a username/password for an authorized user (`admin /
  trinoRocks15`)
- Click on your username in the top right corner > switch role > `sysadmin`

## Using the SEP REST API with BIAC 

You can manage BIAC entities and their actions via the SEP REST API (BIAC
endpoints are of the form `/api/v1/biac/...`). See the list of available
endpoints and methods in our [API
Documentation](https://docs.starburst.io/latest/api/index.html#api-_).  

Note: The SEP REST API can only be used for clusters secured with `PASSWORD`
authentication. To test using the BIAC REST API endpoints, ensure the BIAC
module has been provisioned in conjunction with the `password-file` or `ldap`
module.  

### Example 1: List Roles  

    curl -k --location \
    -X GET 'https://localhost:8443/api/v1/biac/roles' \
    -H 'Accept: application/json' \
    -H 'Content-Type: application/json' \
    -H 'X-Trino-Role: system=ROLE{sysadmin}' \
    -u 'admin:trinoRocks15'  

### Example 2: Adding a user to authorized users  

The following API POST request adds user `Alice` to authorized users. After
performing the following successfully, Alice will be able to access BIAC
features in the SEP UI. 

    curl -k --location \
    -X POST 'https://localhost:8443/api/v1/biac/subjects/users/alice/assignments' \
    -H 'Accept: application/json' \
    -H 'Content-Type: application/json' \
    -H 'X-Trino-Role: system=ROLE{sysadmin}' \
    -u 'admin:trinoRocks15' \
    -d '{ "roleId":"-2", "roleAdmin":"true"}'

### Example 3: Get Role Assignments for a Role

The following API GET request returns users/groups assigned to the `sysadmin`
role which is defined by `roleId=-1`.  

    curl -k --location \
    -X GET 'https://localhost:8443/api/v1/biac/roles/-2/assignments?pageToken=&pageSize=&pageSort=' \
    -H 'Accept: application/json' \
    -H 'Content-Type: application/json' \
    -H 'X-Trino-Role: system=ROLE{sysadmin}' \
    -u 'admin:trinoRocks15'


### Example 4: Create Role

    curl -k --location \
    -X POST 'https://localhost:8443/api/v1/biac/roles' \
    -H 'Accept: application/json' \
    -H 'Content-Type: application/json' \
    -H 'X-Trino-Role: system=ROLE{sysadmin}' \
    -u 'admin:trinoRocks15' \
    -d '{ "name": "testRole", "description":"test creating new BIAC role"}'
