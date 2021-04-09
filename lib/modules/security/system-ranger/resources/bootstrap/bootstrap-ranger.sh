#!/usr/bin/env bash

set -euxo pipefail

echo "Waiting for Ranger Admin to come up..."
/opt/minitrino/wait-for-it.sh ranger-admin:6080 --strict --timeout=150 -- echo "Ranger Admin service is up."

function create_sep_service() {
   curl -i -v -X POST -u admin:trinoRocks15 --header 'Content-Type: application/json' --header 'Accept: application/json' -d '
   {
      "name":"minitrino",
      "description":"Minitrino SEP service",
      "isEnabled":true,
      "tagService":"",
      "configs":{
         "username":"trino_admin",
         "password":"trinoRocks15",
         "jdbc.driverClassName":"io.trinodb.jdbc.TrinoDriver",
         "jdbc.url":"jdbc:trino://localhost:8080",
         "resource-lookup":"true"
      },
      "type":"starburst-enterprise-trino"
   }
   ' \
   'http://localhost:6080/service/plugins/services';
}

COUNTER=0 && set +e
while [[ "${COUNTER}" -le 36 ]]; do 
   if create_sep_service | grep -q "HTTP/1.1 200 OK"; then
      break
   else 
      sleep 5
      ((COUNTER++))
   fi
done
set -e

if [[ "${COUNTER}" == 36 ]]; then
   echo "Timeout waiting for Starburst Enterprise Trino service to become available in Ranger Admin. Exiting."
   exit 1
fi

# Create users
curl -i -v -X POST -u admin:trinoRocks15 --header 'Content-Type: application/json' --header 'Accept: application/json' -d '
{
   "name":"bob",
   "password":"trinoRocks15",
   "firstName":"Bob",
   "lastName":"",
   "emailAddress":"bob@starburstdata.com",
   "userRoleList":[
      "ROLE_USER"
   ],
   "groupIdList":[
      "1"
   ],
   "status":1
}
' \
'http://localhost:6080/service/xusers/secure/users';

curl -i -v -X POST -u admin:trinoRocks15 --header 'Content-Type: application/json' --header 'Accept: application/json' -d '
{
   "name":"alice",
   "password":"trinoRocks15",
   "firstName":"Alice",
   "lastName":"",
   "emailAddress":"alice@starburstdata.com",
   "userRoleList":[
      "ROLE_USER"
   ],
   "groupIdList":[
      "1"
   ],
   "status":1
}
' \
'http://localhost:6080/service/xusers/secure/users';

# Create User Policies
curl -i -v -X POST -u admin:trinoRocks15 --header 'Content-Type: application/json' --header 'Accept: application/json' -d '
{
   "policyType":"0",
   "name":"Bob",
   "isEnabled":true,
   "policyPriority":0,
   "policyLabels":[
      
   ],
   "description":"",
   "isAuditEnabled":true,
   "resources":{
      "catalog":{
         "values":[
            "tpch"
         ],
         "isRecursive":false,
         "isExcludes":false
      },
      "schema":{
         "values":[
            "sf100"
         ],
         "isRecursive":false,
         "isExcludes":false
      },
      "table":{
         "values":[
            "*"
         ],
         "isRecursive":false,
         "isExcludes":false
      },
      "column":{
         "values":[
            "*"
         ],
         "isRecursive":false,
         "isExcludes":false
      }
   },
   "isDenyAllElse":false,
   "policyItems":[
      {
         "users":[
            "bob"
         ],
         "delegateAdmin":true,
         "accesses":[
            {
               "type":"select",
               "isAllowed":true
            },
            {
               "type":"insert",
               "isAllowed":true
            },
            {
               "type":"delete",
               "isAllowed":true
            },
            {
               "type":"update",
               "isAllowed":true
            },
            {
               "type":"ownership",
               "isAllowed":true
            }
         ]
      }
   ],
   "allowExceptions":[
      
   ],
   "denyPolicyItems":[
      
   ],
   "denyExceptions":[
      
   ],
   "service":"minitrino"
}
' \
'http://localhost:6080/service/plugins/policies';

curl -i -v -X POST -u admin:trinoRocks15 --header 'Content-Type: application/json' --header 'Accept: application/json' -d '
{
   "policyType":"0",
   "name":"Alice",
   "isEnabled":true,
   "policyPriority":0,
   "policyLabels":[
      
   ],
   "description":"",
   "isAuditEnabled":true,
   "resources":{
      "catalog":{
         "values":[
            "tpch"
         ],
         "isRecursive":false,
         "isExcludes":false
      },
      "schema":{
         "values":[
            "sf1"
         ],
         "isRecursive":false,
         "isExcludes":false
      },
      "table":{
         "values":[
            "*"
         ],
         "isRecursive":false,
         "isExcludes":false
      },
      "column":{
         "values":[
            "*"
         ],
         "isRecursive":false,
         "isExcludes":false
      }
   },
   "isDenyAllElse":false,
   "policyItems":[
      {
         "users":[
            "alice"
         ],
         "delegateAdmin":true,
         "accesses":[
            {
               "type":"select",
               "isAllowed":true
            },
            {
               "type":"insert",
               "isAllowed":true
            },
            {
               "type":"delete",
               "isAllowed":true
            },
            {
               "type":"update",
               "isAllowed":true
            },
            {
               "type":"ownership",
               "isAllowed":true
            }
         ]
      }
   ],
   "allowExceptions":[
      
   ],
   "denyPolicyItems":[
      
   ],
   "denyExceptions":[
      
   ],
   "service":"minitrino"
}
' \
'http://localhost:6080/service/plugins/policies';

curl -i -v -X POST -u admin:trinoRocks15 --header 'Content-Type: application/json' --header 'Accept: application/json' -d '
{
   "policyType":"0",
   "name":"System",
   "isEnabled":true,
   "policyPriority":0,
   "policyLabels":[
      
   ],
   "description":"",
   "isAuditEnabled":true,
   "resources":{
      "catalog":{
         "values":[
            "system"
         ],
         "isRecursive":false,
         "isExcludes":false
      },
      "schema":{
         "values":[
            "*"
         ],
         "isRecursive":false,
         "isExcludes":false
      },
      "table":{
         "values":[
            "*"
         ],
         "isRecursive":false,
         "isExcludes":false
      },
      "column":{
         "values":[
            "*"
         ],
         "isRecursive":false,
         "isExcludes":false
      }
   },
   "isDenyAllElse":false,
   "policyItems":[
      {
         "users":[
            "{USER}"
         ],
         "accesses":[
            {
               "type":"select",
               "isAllowed":true
            },
            {
               "type":"ownership",
               "isAllowed":true
            }
         ]
      }
   ],
   "allowExceptions":[
      
   ],
   "denyPolicyItems":[
      
   ],
   "denyExceptions":[
      
   ],
   "service":"minitrino"
}
' \
'http://localhost:6080/service/plugins/policies';

# Add users to query policy 
curl -i -v -X PUT -u admin:trinoRocks15 --header 'Content-Type: application/json' --header 'Accept: application/json' -d '
{
   "id":2,
   "isEnabled":true,
   "service":"minitrino",
   "name":"all - query",
   "policyType":0,
   "policyPriority":0,
   "description":"Policy for all - query",
   "isAuditEnabled":true,
   "resources":{
      "query":{
         "values":[
            "*"
         ],
         "isRecursive":false,
         "isExcludes":false
      }
   },
   "policyItems":[
      {
         "users":[
            "trino_admin",
            "{USER}"
         ],
         "delegateAdmin":true,
         "accesses":[
            {
               "type":"select",
               "isAllowed":true
            },
            {
               "type":"execute",
               "isAllowed":true
            },
            {
               "type":"kill",
               "isAllowed":true
            }
         ]
      }
   ],
   "denyPolicyItems":[
      
   ],
   "allowExceptions":[
      
   ],
   "denyExceptions":[
      
   ],
   "dataMaskPolicyItems":[
      
   ],
   "rowFilterPolicyItems":[
      
   ],
   "serviceType":"203",
   "options":{
      
   },
   "validitySchedules":[
      
   ],
   "policyLabels":[
      
   ],
   "zoneName":"",
   "isDenyAllElse":false,
   "sameLevel20catalog":null,
   "sameLevel30schema":null,
   "column":null
}
' \
'http://localhost:6080/service/plugins/policies/2';
