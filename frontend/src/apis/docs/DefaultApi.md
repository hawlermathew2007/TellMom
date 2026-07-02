# DefaultApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**ingestApiIngestPost**](DefaultApi.md#ingestapiingestpost) | **POST** /api/ingest | Ingest |



## ingestApiIngestPost

> ingestApiIngestPost(ingestRequest)

Ingest

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { IngestApiIngestPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // IngestRequest
    ingestRequest: ...,
  } satisfies IngestApiIngestPostRequest;

  try {
    const data = await api.ingestApiIngestPost(body);
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
| **ingestRequest** | [IngestRequest](IngestRequest.md) |  | |

### Return type

`void` (Empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **204** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

