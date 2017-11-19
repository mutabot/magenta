# Scenario: Common settings available

> see https://aka.ms/autorest

``` yaml 
input-file: http://localhost:4999/swagger/v1/swagger.json
namespace: MagentaClient

python:
  - output-folder: core/model
    sync-methods: none
    payload-flattening-threshold: 3 
    client-side-validation: false 
    max-comment-columns: 80
	override-client-name: MagentaClient
```
