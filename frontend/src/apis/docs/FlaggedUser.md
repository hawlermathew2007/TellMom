
# FlaggedUser


## Properties

Name | Type
------------ | -------------
`userId` | string
`serverId` | string
`platform` | string
`flaggedChats` | Array&lt;string&gt;
`resolved` | boolean

## Example

```typescript
import type { FlaggedUser } from ''

// TODO: Update the object below with actual values
const example = {
  "userId": null,
  "serverId": null,
  "platform": null,
  "flaggedChats": null,
  "resolved": null,
} satisfies FlaggedUser

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as FlaggedUser
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


