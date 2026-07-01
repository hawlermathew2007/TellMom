# ClassifierApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**classifierCheckinCheckinPost**](ClassifierApi.md#classifiercheckincheckinpost) | **POST** /checkin | Classifier Checkin |



## classifierCheckinCheckinPost

> ClassifierCheckInResponse classifierCheckinCheckinPost(classifierCheckInRequest, xPassword)

Classifier Checkin

### Example

```ts
import {
  Configuration,
  ClassifierApi,
} from '';
import type { ClassifierCheckinCheckinPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new ClassifierApi();

  const body = {
    // ClassifierCheckInRequest
    classifierCheckInRequest: ...,
    // string (optional)
    xPassword: xPassword_example,
  } satisfies ClassifierCheckinCheckinPostRequest;

  try {
    const data = await api.classifierCheckinCheckinPost(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **classifierCheckInRequest** | [ClassifierCheckInRequest](ClassifierCheckInRequest.md) |  | |
| **xPassword** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

[**ClassifierCheckInResponse**](ClassifierCheckInResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

