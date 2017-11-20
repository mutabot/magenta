# Scenario: Common settings available

> see https://aka.ms/autorest

``` yaml 
input-file: http://localhost:4999/swagger/v1/swagger.json

python:
  - output-folder: .
    sync-methods: none
    payload-flattening-threshold: 2 
    client-side-validation: false 
    max-comment-columns: 180
	override-client-name: DynorisClient
	package-name: dynoris
```
