
# ChildAccountResponse


## Properties

Name | Type
------------ | -------------
`id` | number
`platform` | [ChatPlatform](ChatPlatform.md)
`platformUserId` | string
`displayName` | string
`createdAt` | Date
`updatedAt` | Date

## Example

```typescript
import type { ChildAccountResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "platform": null,
  "platformUserId": null,
  "displayName": null,
  "createdAt": null,
  "updatedAt": null,
} satisfies ChildAccountResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ChildAccountResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


