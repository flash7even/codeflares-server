import json

data = {
  "size": 0,
    "query" : {
      "bool": {
        "must": [
          {
            "term": {
              "category_root": "base"
            }
          },
          {
            "term": {
              "user_id": "xSTh3HIB2TcpYv9j_Y_x"
            }
          }
        ]
      }
    },
    "aggs" : {
        "skill_value_by_percentage" : { "sum" : { "field" : "skill_value_by_percentage" } }
    }
}

print(json.dumps(data))