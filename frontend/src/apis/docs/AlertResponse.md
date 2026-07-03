
# AlertResponse


## Properties

Name | Type
------------ | -------------
`id` | number
`childAccountId` | number
`platform` | [ChatPlatform](ChatPlatform.md)
`serverId` | string
`messagePreview` | string
`probability` | number
`acknowledged` | boolean
`createdAt` | Date
`messages` | [Array&lt;ChatMessageResponse&gt;](ChatMessageResponse.md)

## Example

```typescript
import type { AlertResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "childAccountId": null,
  "platform": null,
  "serverId": null,
  "messagePreview": null,
  "probability": null,
  "acknowledged": null,
  "createdAt": null,
  "messages": null,
} satisfies AlertResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as AlertResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


