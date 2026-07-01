
# GroomingAnalysis


## Properties

Name | Type
------------ | -------------
`victimSelection` | [StageAssessment](StageAssessment.md)
`accessRelationshipBuilding` | [StageAssessment](StageAssessment.md)
`trustDevelopment` | [StageAssessment](StageAssessment.md)
`isolation` | [StageAssessment](StageAssessment.md)
`boundaryTesting` | [StageAssessment](StageAssessment.md)
`desensitization` | [StageAssessment](StageAssessment.md)
`maintainingControl` | [StageAssessment](StageAssessment.md)
`overallAssessment` | [OverallAssessment](OverallAssessment.md)

## Example

```typescript
import type { GroomingAnalysis } from ''

// TODO: Update the object below with actual values
const example = {
  "victimSelection": null,
  "accessRelationshipBuilding": null,
  "trustDevelopment": null,
  "isolation": null,
  "boundaryTesting": null,
  "desensitization": null,
  "maintainingControl": null,
  "overallAssessment": null,
} satisfies GroomingAnalysis

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as GroomingAnalysis
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


