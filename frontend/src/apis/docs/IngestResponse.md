
# IngestResponse


## Properties

Name | Type
------------ | -------------
`status` | string
`classifiedCount` | number
`newlyFlagged` | Array&lt;string&gt;
`parentsNotified` | number

## Example

```typescript
import type { IngestResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "status": null,
  "classifiedCount": null,
  "newlyFlagged": null,
  "parentsNotified": null,
} satisfies IngestResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as IngestResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


