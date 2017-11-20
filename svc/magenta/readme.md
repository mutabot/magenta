# Scenario: Common settings available

> see https://aka.ms/autorest

``` yaml 
input-file: http://localhost:8092/swagger/v1/swagger.json

python:
  - output-folder: .
    sync-methods: none
    payload-flattening-threshold: 5 
    client-side-validation: false 
    max-comment-columns: 180
	override-client-name: MagentaClient
```
