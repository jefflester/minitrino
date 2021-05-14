#!/usr/bin/env bash

set -ex 

# all - catalog, session-property
curl -i -v -X PUT -u admin:trinoRocks15 --header 'Content-Type: application/json' --header 'Accept: application/json' -d '
{
   "id":1,
   "isEnabled":true,
   "createdBy":"Admin",
   "updatedBy":"Admin",
   "version":1,
   "service":"starburst",
   "name":"all - catalog, session-property",
   "policyType":0,
   "policyPriority":0,
   "description":"Policy for all - catalog, session-property",
   "isAuditEnabled":true,
   "resources":{
      "catalog":{
         "values":[
            "*"
         ],
         "isRecursive":false,
         "isExcludes":false
      },
      "session-property":{
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
            "starburst_service",
            "{USER}"
         ],
         "delegateAdmin":true,
         "accesses":[
            {
               "type":"update",
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
   "sameLevel30schema":null,
   "column":null
}' \
"http://ranger-admin:6080/service/plugins/policies/1";

# all - query
curl -i -v -X PUT -u admin:trinoRocks15 --header 'Content-Type: application/json' --header 'Accept: application/json' -d '
{
   "id":2,
   "guid":"25e258a8-82f6-48d5-9db0-1bfd9641a454",
   "isEnabled":true,
   "createdBy":"Admin",
   "updatedBy":"Admin",
   "version":1,
   "service":"starburst",
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
            "starburst_service",
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
}' \
"http://ranger-admin:6080/service/plugins/policies/2";

# all - system-session-property
curl -i -v -X PUT -u admin:trinoRocks15 --header 'Content-Type: application/json' --header 'Accept: application/json' -d '
{
   "id":3,
   "isEnabled":true,
   "createdBy":"Admin",
   "updatedBy":"Admin",
   "version":1,
   "service":"starburst",
   "name":"all - system-session-property",
   "policyType":0,
   "policyPriority":0,
   "description":"Policy for all - system-session-property",
   "isAuditEnabled":true,
   "resources":{
      "system-session-property":{
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
            "starburst_service",
            "{USER}"
         ],
         "delegateAdmin":true,
         "accesses":[
            {
               "type":"update",
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
}' \
"http://ranger-admin:6080/service/plugins/policies/3";

# all - function
curl -i -v -X PUT -u admin:trinoRocks15 --header 'Content-Type: application/json' --header 'Accept: application/json' -d '
{
   "id":4,
   "isEnabled":true,
   "createdBy":"Admin",
   "updatedBy":"Admin",
   "version":1,
   "service":"starburst",
   "name":"all - function",
   "policyType":0,
   "policyPriority":0,
   "description":"Policy for all - function",
   "isAuditEnabled":true,
   "resources":{
      "function":{
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
            "starburst_service",
            "{USER}"
         ],
         "delegateAdmin":true,
         "accesses":[
            {
               "type":"execute",
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
}' \
"http://ranger-admin:6080/service/plugins/policies/4";

# all - user
curl -i -v -X PUT -u admin:trinoRocks15 --header 'Content-Type: application/json' --header 'Accept: application/json' -d '
{
   "id":5,
   "isEnabled":true,
   "createdBy":"Admin",
   "updatedBy":"Admin",
   "version":1,
   "service":"starburst",
   "name":"all - user",
   "policyType":0,
   "policyPriority":0,
   "description":"Policy for all - user",
   "isAuditEnabled":true,
   "resources":{
      "user":{
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
            "starburst_service",
            "{USER}"
         ],
         "delegateAdmin":true,
         "accesses":[
            {
               "type":"impersonate",
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
}' \
"http://ranger-admin:6080/service/plugins/policies/5";

# all - catalog, schema, procedure
curl -i -v -X PUT -u admin:trinoRocks15 --header 'Content-Type: application/json' --header 'Accept: application/json' -d '
{
   "id":6,
   "isEnabled":true,
   "createdBy":"Admin",
   "updatedBy":"Admin",
   "version":1,
   "service":"starburst",
   "name":"all - catalog, schema, procedure",
   "policyType":0,
   "policyPriority":0,
   "description":"Policy for all - catalog, schema, procedure",
   "isAuditEnabled":true,
   "resources":{
      "catalog":{
         "values":[
            "*"
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
      "procedure":{
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
            "starburst_service",
            "{USER}"
         ],
         "delegateAdmin":true,
         "accesses":[
            {
               "type":"execute",
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
   "column":null
}' \
"http://ranger-admin:6080/service/plugins/policies/6";

# Bob policy
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
            "bob",
            "starburst_service"
         ],
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
            },
            {
               "type":"create",
               "isAllowed":true
            },
            {
               "type":"drop",
               "isAllowed":true
            },
            {
               "type":"alter",
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
   "service":"starburst"
}' \
"http://ranger-admin:6080/service/plugins/policies";

# Alice policy
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
            "sf10"
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
            "alice",
            "starburst_service"
         ],
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
            },
            {
               "type":"create",
               "isAllowed":true
            },
            {
               "type":"drop",
               "isAllowed":true
            },
            {
               "type":"alter",
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
   "service":"starburst"
}' \
"http://ranger-admin:6080/service/plugins/policies";
