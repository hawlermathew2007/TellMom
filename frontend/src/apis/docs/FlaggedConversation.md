
# FlaggedConversation


## Properties

Name | Type
------------ | -------------
`platform` | string
`serverId` | string
`flaggedChats` | Array&lt;string&gt;
`resolved` | boolean
`explanation` | [GroomingAnalysis](GroomingAnalysis.md)

## Example

```typescript
import type { FlaggedConversation } from ''

// TODO: Update the object below with actual values
const example = {
  "platform": null,
  "serverId": null,
  "flaggedChats": null,
  "resolved": null,
  "explanation": null,
} satisfies FlaggedConversation

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as FlaggedConversation
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


